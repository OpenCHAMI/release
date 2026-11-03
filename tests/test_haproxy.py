# SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors
#
# SPDX-License-Identifier: MIT

"""Exercise the shipped HAProxy rules against an inert loopback backend."""

import http.client
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest


IDENTITY_HEADERS = ("X-Forwarded-For", "Forwarded", "X-Real-IP", "True-Client-IP")


class EchoRequest(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(
            {
                "path": self.path,
                "headers": {
                    name: self.headers.get_all(name, []) for name in IDENTITY_HEADERS
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class HAProxyIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        haproxy = shutil.which(os.environ.get("HAPROXY", "haproxy"))
        if not haproxy or not shutil.which("openssl"):
            raise RuntimeError("These tests require haproxy and openssl on PATH")

        temp = tempfile.TemporaryDirectory(prefix="release-haproxy-")
        cls.addClassCleanup(temp.cleanup)
        directory = Path(temp.name)
        backend = http.server.ThreadingHTTPServer(("127.0.0.1", 0), EchoRequest)
        cls.addClassCleanup(backend.server_close)
        thread = threading.Thread(target=backend.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(backend.shutdown)

        # Reserve distinct ports until the complete configuration is ready.
        reservations = []

        def port(host):
            family = socket.AF_INET6 if ":" in host else socket.AF_INET
            sock = socket.socket(family)
            reservations.append(sock)
            cls.addClassCleanup(sock.close)
            sock.bind((host, 0))
            return sock.getsockname()[1]

        cls.frontends = [
            ("127.0.0.1", port("127.0.0.1"), False),
            ("127.0.0.1", port("127.0.0.1"), True),
        ]
        try:
            cls.ipv6_frontends = [
                ("::1", port("::1"), False),
                ("::1", port("::1"), True),
            ]
        except OSError:
            cls.ipv6_frontends = []
        stats_port = port("127.0.0.1")

        cert, key = directory / "cert.pem", directory / "key.pem"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "1",
                "-subj",
                "/CN=metadata.test",
            ],
            check=True,
            capture_output=True,
        )
        cert.write_bytes(cert.read_bytes() + key.read_bytes())

        config = (
            Path(__file__).resolve().parents[1] / "systemd/configs/haproxy.cfg"
        ).read_text()
        # Change only test infrastructure: listeners, socket, cert and backend
        # addresses. Keep the deployed request/header/path rules intact.
        for original, tls in (
            ("  bind :80", False),
            ("  bind :443 ssl crt /etc/haproxy/certs/ strict-sni", True),
        ):
            listeners = []
            for host, number, encrypted in cls.frontends + cls.ipv6_frontends:
                if encrypted == tls:
                    address = f"[{host}]" if ":" in host else host
                    suffix = f" ssl crt {cert} strict-sni" if tls else ""
                    listeners.append(f"  bind {address}:{number}{suffix}")
            if original not in config:
                raise RuntimeError(f"Update the listener fixture for {original!r}")
            config = config.replace(original + "\n", "\n".join(listeners) + "\n", 1)
        config = config.replace("bind *:8404", f"bind 127.0.0.1:{stats_port}")
        config = re.sub(
            r"(?m)^  stats socket .*$",
            f"  stats socket {directory / 'api.sock'} mode 600 level admin",
            config,
        )
        config = re.sub(
            r"(?m)^(  server \S+) \S+(.*)$",
            rf"\1 127.0.0.1:{backend.server_port}\2",
            config,
        )
        config_path = directory / "haproxy.cfg"
        config_path.write_text(config)
        subprocess.run(
            [haproxy, "-c", "-f", str(config_path)], check=True, capture_output=True
        )
        for sock in reservations:
            sock.close()

        log = (directory / "haproxy.log").open("w+")
        cls.addClassCleanup(log.close)
        process = subprocess.Popen(
            [haproxy, "-db", "-f", str(config_path)],
            stdout=log,
            stderr=subprocess.STDOUT,
        )

        def stop():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        cls.addClassCleanup(stop)
        deadline = time.monotonic() + 5
        while True:
            try:
                with socket.create_connection(cls.frontends[0][:2], timeout=0.2):
                    break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    log.seek(0)
                    raise RuntimeError(f"HAProxy failed to start: {log.read()}")
                time.sleep(0.02)

    def request(self, frontend, headers=(), path="/metadata-service/user-data"):
        host, port, tls = frontend
        sock = socket.create_connection((host, port), timeout=3)
        try:
            if tls:
                # The certificate is generated solely for this local test.
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname="metadata.test")
            lines = [f"GET {path} HTTP/1.1", "Host: metadata.test", "Connection: close"]
            lines.extend(f"{name}: {value}" for name, value in headers)
            sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            response = http.client.HTTPResponse(sock)
            response.begin()
            body = response.read()
            self.assertEqual(response.status, 200, body)
            result = json.loads(body)
            self.assertEqual(result["headers"]["X-Forwarded-For"], [host])
            for name in IDENTITY_HEADERS[1:]:
                self.assertEqual(result["headers"][name], [], name)
            return result
        finally:
            sock.close()

    def test_identity_headers(self):
        cases = [
            (),
            (("X-Forwarded-For", "192.0.2.99"),),
            (("X-Forwarded-For", "2001:db8::99"),),
            (("X-Forwarded-For", "192.0.2.99, 198.51.100.7"),),
            (("X-Forwarded-For", "192.0.2.99"), ("x-forwarded-for", "198.51.100.7")),
            (("Forwarded", 'for="192.0.2.99"'),),
            (("X-Real-IP", "192.0.2.99"),),
            (("True-Client-IP", "192.0.2.99"),),
            tuple((name, "192.0.2.99") for name in IDENTITY_HEADERS),
        ]
        cases.extend(
            ((name, "192.0.2.99"), (name.lower(), "198.51.100.7"))
            for name in IDENTITY_HEADERS[1:]
        )
        for frontend in self.frontends:
            for headers in cases:
                with self.subTest(frontend=frontend, headers=headers):
                    self.request(frontend, headers)

    def test_ipv6_source(self):
        if not self.ipv6_frontends:
            self.skipTest("IPv6 loopback is unavailable")
        for frontend in self.ipv6_frontends:
            with self.subTest(frontend=frontend):
                self.request(frontend, (("X-Forwarded-For", "192.0.2.99"),))

    def test_existing_routes(self):
        for frontend in self.frontends:
            for original, rewritten in (
                ("/hsm/v2/State/Components", "/hsm/v2/State/Components"),
                ("/configurator", "/configurator"),
                ("/boot-service/health", "/health"),
                ("/metadata-service/vendor-data?example=1", "/vendor-data?example=1"),
                ("/tokensmith/health", "/health"),
            ):
                with self.subTest(frontend=frontend, path=original):
                    result = self.request(
                        frontend, (("X-Forwarded-For", "192.0.2.99"),), original
                    )
                    self.assertEqual(result["path"], rewritten)


if __name__ == "__main__":
    unittest.main()
