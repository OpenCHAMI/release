# SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors
# SPDX-License-Identifier: MIT

"""Behavioral contract for the RPM-shipped, read-only endpoint validator."""

import importlib.machinery
import importlib.util
import json
import http.server
import os
from pathlib import Path
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader(
    "endpoint_validator", str(ROOT / "scripts/openchami-validate-endpoints")
)


class EndpointValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_loader(LOADER.name, LOADER)
        cls.tool = importlib.util.module_from_spec(spec)
        LOADER.exec_module(cls.tool)

    def endpoint(self, jwt="required"):
        return {
            "id": "inventory", "target": "ingress", "method": "GET",
            "path": "/inventory", "jwt": jwt, "success_statuses": [200],
            "reason": "test policy",
        }

    def result(self, jwt, statuses, token=True):
        calls = []

        def probe(url, bearer, timeout, cafile):
            calls.append(bearer)
            return {"status": statuses[len(calls) - 1], "error": None}

        row = self.tool.check_endpoint(
            self.endpoint(jwt), {"ingress": "https://example.invalid"},
            {"ingress": "fixture-secret-token"} if token else {}, {},
            2, None, probe,
        )
        return row, calls

    def test_required_needs_anonymous_invalid_and_valid_evidence(self):
        row, calls = self.result("required", [401, 401, 200])
        self.assertEqual(row["verdict"], "pass")
        self.assertEqual(calls[0], None)
        self.assertEqual(calls[-1], "fixture-secret-token")
        self.assertNotIn("fixture-secret-token", json.dumps(row))

    def test_gateway_denial_missing_routes_and_bad_token_are_not_auth_success(self):
        for statuses in ([403, 403, 403], [404, 404, 404], [401, 200, 200],
                         [401, 401, 403], [401, 401, 302], [200, 401, 200]):
            with self.subTest(statuses=statuses):
                row, _ = self.result("required", statuses)
                self.assertEqual(row["verdict"], "fail")

    def test_missing_credential_or_target_is_incomplete(self):
        row, _ = self.result("required", [401, 401], token=False)
        self.assertEqual(row["verdict"], "incomplete")
        row = self.tool.check_endpoint(self.endpoint(), {}, {}, {}, 2, None)
        self.assertEqual(row["verdict"], "incomplete")
        self.assertEqual(row["probes"], {})

    def test_public_and_unresolved_policy_are_distinct(self):
        row, _ = self.result("public", [200, 401, 200])
        self.assertEqual(row["verdict"], "pass")
        row, _ = self.result("observe", [200, 200, 200])
        self.assertEqual(row["verdict"], "incomplete")
        self.assertEqual(row["probes"]["anonymous"]["access"], "accessible")

    def test_network_failure_is_not_a_pass(self):
        row, _ = self.result("public", [None, None, None])
        self.assertEqual(row["verdict"], "fail")

    def test_policy_rejects_mutations_and_ambiguous_input_before_requests(self):
        for patch in ({"method": "DELETE"}, {"path": "//evil.invalid/"},
                      {"path": "/nodes?token=secret"}, {"jwt": "optional"},
                      {"success_statuses": [403]}, {"typo": True}):
            with self.subTest(patch=patch):
                endpoint = dict(self.endpoint(), **patch)
                with self.assertRaises(ValueError):
                    self.tool.validate_policy({"schema_version": 1,
                                               "policy_id": "test-v1",
                                               "endpoints": [endpoint]})

    def test_duplicate_ids_and_unknown_schema_are_rejected(self):
        for version, endpoints in ((2, [self.endpoint()]),
                                   (1, [self.endpoint(), self.endpoint()])):
            with self.assertRaises(ValueError):
                self.tool.validate_policy({"schema_version": version,
                                           "policy_id": "test-v1",
                                           "endpoints": endpoints})

    def test_duplicate_json_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"jwt":"required","jwt":"public"}',
                       object_pairs_hook=self.tool.unique_fields)

    def test_credential_is_sent_only_to_its_logical_target(self):
        policy = json.loads((ROOT / "validation/policies/release-v1.json").read_text())
        calls = []

        def probe(url, token, *_):
            calls.append((url, token))
            return {"status": 401 if token is None or token == self.tool.INVALID_JWT else 200,
                    "error": None}

        for entry in policy["endpoints"]:
            self.tool.check_endpoint(entry,
                                     {name: "https://example.invalid" for name in ("smd", "boot", "metadata")},
                                     {"smd": "fixture-smd-only"}, {}, 2, None, probe)
        self.assertTrue(any(token == "fixture-smd-only" for _, token in calls))
        for url, token in calls:
            if "/boot-service/" in url or "/metadata-service/" in url:
                self.assertNotEqual(token, "fixture-smd-only")

    def test_targets_reject_credentials_queries_and_non_http(self):
        for address in ("https://user:secret@host", "https://host/?token=x",
                        "file:///etc/passwd", "https://host/#secret"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.tool.validate_target(address)

    def test_packaged_policies_are_valid_and_documented(self):
        self.assertEqual({source.name for source in (ROOT / "validation/policies").glob("*.json")},
                         {"release-v1.json", "legacy-bss-v1.json"})
        for source in (ROOT / "validation/policies").glob("*.json"):
            with self.subTest(source=source.name):
                policy = self.tool.validate_policy(json.loads(source.read_text()))
                self.assertEqual(policy["policy_id"], source.stem)
                self.assertIn(source.name, (ROOT / "docs/endpoint-validation.md").read_text())

    def test_optional_non_admin_jwt_requires_403(self):
        for denied_status, verdict in ((403, "pass"), (401, "fail"), (200, "fail")):
            answers = iter((401, 401, 200, denied_status))
            row = self.tool.check_endpoint(
                self.endpoint(), {"ingress": "https://example.invalid"},
                {"ingress": "authorized"}, {"ingress": "non-admin"}, 2, None,
                lambda *args: {"status": next(answers), "error": None},
            )
            self.assertEqual(row["verdict"], verdict)

    def test_absent_means_http_not_found_not_forbidden_or_unreachable(self):
        for status, verdict in ((404, "pass"), (410, "pass"), (403, "fail"),
                                (200, "fail"), (None, "fail")):
            row, calls = self.result("absent", [status])
            self.assertEqual(row["verdict"], verdict)
            self.assertEqual(calls, [None])


class EndpointCLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                auth = self.headers.get("Authorization")
                cls.requests.append((self.path, auth))
                if self.path == "/redirect":
                    status = 302
                elif self.path == "/private":
                    status = 200 if auth == "Bearer fixture-authorized-secret" else 403 if auth == "Bearer fixture-nonadmin-secret" else 401
                elif self.path == "/failure":
                    status = 500
                elif self.path == "/missing":
                    status = 404
                else:
                    status = 200
                self.send_response(status)
                if status == 302:
                    self.send_header("Location", cls.address + "/leaked-token")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.address = "http://127.0.0.1:{}".format(cls.server.server_port)
        cls.addClassCleanup(cls.server.server_close)
        thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(cls.server.shutdown)

    def call(self, path="/private", jwt="required", token=True, extra=()):
        with tempfile.TemporaryDirectory() as directory:
            policy = {
                "schema_version": 1, "policy_id": "cli-test-v1", "endpoints": [{
                    "id": "test", "target": "ingress", "method": "GET", "path": path,
                    "jwt": jwt, "success_statuses": [200], "reason": "fixture",
                }],
            }
            source = Path(directory) / "policy.json"
            source.write_text(json.dumps(policy))
            args = [sys.executable, str(ROOT / "scripts/openchami-validate-endpoints"),
                    "--policy", str(source), "--target", "ingress=" + self.address, "--json"]
            if token:
                args += ["--token-env", "ingress=VALIDATION_TEST_TOKEN"]
            env = dict(os.environ, VALIDATION_TEST_TOKEN="fixture-authorized-secret",
                       VALIDATION_DENIED_TOKEN="fixture-nonadmin-secret",
                       http_proxy="http://127.0.0.1:1", HTTP_PROXY="http://127.0.0.1:1")
            result = subprocess.run(args + list(extra), env=env, capture_output=True,
                                    text=True, timeout=10)
            for secret in ("fixture-authorized-secret", "fixture-nonadmin-secret"):
                self.assertNotIn(secret, result.stdout + result.stderr)
            return result

    def test_real_http_auth_matrix_and_status_only_report(self):
        result = self.call(extra=("--allow-http-token", "--denied-token-env", "ingress=VALIDATION_DENIED_TOKEN"))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(len(report["policy_sha256"]), 64)
        self.assertEqual(report["summary"], {"pass": 1, "fail": 0, "incomplete": 0})
        self.assertEqual(report["endpoints"][0]["probes"]["unauthorized"]["status"], 403)
        self.assertNotIn("headers", result.stdout)
        self.assertNotIn("body", result.stdout)

    def test_no_redirect_following_or_credential_forwarding(self):
        before = len(self.requests)
        result = self.call(path="/redirect", jwt="public", extra=("--allow-http-token",))
        self.assertEqual(result.returncode, 1)
        self.assertTrue(all(path == "/redirect" for path, _ in self.requests[before:]))
        self.assertEqual(json.loads(result.stdout)["endpoints"][0]["probes"]["authorized"]["status"], 302)

    def test_http_credentials_require_explicit_opt_in_before_requests(self):
        before = len(self.requests)
        result = self.call()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.requests), before)

    def test_incomplete_and_fail_exit_codes(self):
        self.assertEqual(self.call(token=False).returncode, 2)
        self.assertEqual(self.call(path="/public", jwt="observe", token=False).returncode, 2)
        self.assertEqual(self.call(path="/failure", jwt="public", token=False).returncode, 1)
        self.assertEqual(self.call(path="/missing", jwt="public", token=False).returncode, 1)

    def test_connection_failure_is_explicit(self):
        from urllib.parse import urlsplit
        spec = importlib.util.spec_from_loader(LOADER.name, LOADER)
        tool = importlib.util.module_from_spec(spec)
        LOADER.exec_module(tool)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        # Reserved but not listening: no other process can claim the test port.
        self.addCleanup(sock.close)
        address = "http://127.0.0.1:{}".format(sock.getsockname()[1])
        self.assertEqual(urlsplit(address).hostname, "127.0.0.1")
        probe = tool.probe_url(address, None, 0.2, None)
        self.assertIsNone(probe["status"])
        self.assertEqual(probe["error"], "connection-error")

    def test_https_rejects_untrusted_certificate_and_accepts_selected_ca(self):
        spec = importlib.util.spec_from_loader(LOADER.name, LOADER)
        tool = importlib.util.module_from_spec(spec)
        LOADER.exec_module(tool)

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_):
                pass

        with tempfile.TemporaryDirectory() as directory:
            cert, key = Path(directory) / "cert.pem", Path(directory) / "key.pem"
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(key), "-out", str(cert), "-days", "1",
                "-subj", "/CN=validator.test", "-addext", "subjectAltName=IP:127.0.0.1",
            ], check=True, capture_output=True)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                address = "https://127.0.0.1:{}".format(server.server_port)
                result = tool.probe_url(address, None, 2, None)
                self.assertEqual(result["error"], "tls-error")
                self.assertIsNone(result["status"])
                result = tool.probe_url(address, "fixture-authorized-secret", 2, str(cert))
                self.assertEqual(result, {"status": 200, "error": None})
            finally:
                server.shutdown()
                server.server_close()


class PackageInstallTest(unittest.TestCase):
    def test_real_install_section_in_disposable_buildroot(self):
        spec = (ROOT / "openchami.spec").read_text()
        self.assertIn("Requires:       python3\n", spec)
        self.assertIn("%doc docs/endpoint-validation.md", spec)
        self.assertNotIn("validate-endpoints", spec.split("%post\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            script = spec.split("%install\n", 1)[1].split("\n%files", 1)[0]
            script = script.replace("%{buildroot}", directory)
            self.assertNotIn("%{", script)
            subprocess.run(["sh", "-eu", "-c", script], cwd=ROOT, check=True,
                           stdout=subprocess.DEVNULL)
            binary = Path(directory) / "usr/bin/openchami-validate-endpoints"
            self.assertEqual(stat.S_IMODE(binary.stat().st_mode), 0o755)
            subprocess.run([sys.executable, str(binary), "--help"], check=True,
                           stdout=subprocess.DEVNULL)
            installed = Path(directory) / "usr/share/openchami/validation/policies"
            self.assertEqual({source.name for source in installed.glob("*.json")},
                             {"release-v1.json", "legacy-bss-v1.json"})
            for source in installed.glob("*.json"):
                self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o644)
                self.assertIn("schema_version", json.loads(source.read_text()))
                self.assertTrue(source.with_name(source.name + ".license").is_file())


if __name__ == "__main__":
    unittest.main()
