<!--
SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors

SPDX-License-Identifier: MIT
-->

# Metadata security in Quadlet deployments

Cloud-init responses can contain credentials and other node-specific secrets.
Production deployments must enforce the following trust boundaries before serving
those responses. These requirements apply to metadata-service and to deployments
that still use the legacy cloud-init service.

## Request identity at HAProxy

The packaged HAProxy frontend replaces `X-Forwarded-For` with the source address
of its connection and removes `Forwarded`, `X-Real-IP`, and `True-Client-IP`.
Backends receive one proxy-established client address, regardless of headers
supplied by the caller. Preserve these rules on both HTTP and HTTPS listeners.
TLS encryption alone does not establish the identity claimed inside a header.

This configuration assumes HAProxy receives connections directly from clients.
If another proxy or NAT sits in front of it, establish how the original client
identity will be authenticated and preserved before using that topology. Do not
restore client-supplied forwarding headers to make address lookups work.

Only HAProxy may supply forwarded identity on proxy-to-service connections.
Prevent clients from bypassing it through published backend ports or container
networks. A service receiving traffic directly through WireGuard must instead
identify the node from the original tunnel connection source and its enrolled
peer mapping, ignoring caller-supplied identity headers. Tunnel traffic that
bypasses HAProxy does not receive its header sanitization.

Service admission and identity checks must use the original transport peer.
Middleware that rewrites `RemoteAddr` from forwarding headers must not run before
those trust decisions. A header claiming an address in a WireGuard subnet is not
proof that a request arrived through WireGuard.

## Privileged WireGuard bootstrap

The production model uses a tunnel established by a privileged bootstrap process,
with a limited lifetime:

1. Authorize enrollment and bind the peer key and assigned tunnel address to the
   intended node. Restrict each peer's server-side `AllowedIPs` to its assigned
   address or addresses; membership in a shared subnet alone does not identify it.
2. Allow secret-bearing cloud-init requests only through the authorized bootstrap
   path. Prevent ordinary users from retrieving those responses, including through
   the host's tunnel while bootstrap is running.
3. Tear down the tunnel when bootstrap finishes, before general user workloads
   begin. Ordinary users must not possess the permissions, private keys, or
   enrollment credentials needed to reopen it.
4. Protect downloaded payloads, cloud-init caches, logs, and installed secrets from
   ordinary users after bootstrap. Closing a tunnel does not remove local copies.

These are deployment requirements, not guarantees made by installing this RPM.
The packaged metadata-service configuration does not enable WireGuard-only mode
by default. A service's WireGuard-only setting must also be checked against its
actual listener, proxy, and middleware behavior. Management API token settings
do not establish the cloud-init payload access policy.

The current RPM installation script stops firewalld. Do not rely on pre-existing
firewalld rules surviving installation as the only access control. Establish and
verify the site's intended network controls after installing or updating it.

## Applying an updated configuration

RPM installs `/etc/openchami/configs/*` with `%config(noreplace)`. An upgrade can
leave an existing `haproxy.cfg` active and put the new version in
`haproxy.cfg.rpmnew`. Review and merge the identity rules into the active file;
updating the package alone may not activate them. The HAProxy container mounts
that directory at `/usr/local/etc/haproxy/`.

Validate the active configuration inside the container before an operator applies
a controlled restart:

```bash
sudo podman exec haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg
sudo systemctl restart haproxy.service
```

Keep sensitive metadata access restricted if validation fails. Re-establishing
the previous header trust behavior is not a safe rollback.

## Verification

Use the packaged [endpoint validator and upgrade checklist](endpoint-validation.md)
to record expected versus observed anonymous/JWT access from each relevant network
location before and after updates. Its selected GET probes complement the tests below;
they do not prove bootstrap isolation or sanitize headers on behalf of a service.

With HAProxy, OpenSSL, Python 3, and make installed, run `make test-haproxy`.
The test uses the packaged configuration with temporary loopback listeners,
an ephemeral TLS certificate, and an inert backend. It checks HTTP and HTTPS,
duplicate and comma-separated identity headers, alternate identity headers,
IPv6 source addresses when available, and existing backend path rewrites.

Before production use, also verify the actual deployment with synthetic,
node-specific canary payloads:

- Authorized bootstrap retrieves only the requesting node's data, regardless of
  supplied identity headers, on every permitted proxy and direct tunnel path.
- Requests outside the approved bootstrap path cannot retrieve protected data.
- An ordinary user cannot fetch data during bootstrap, after tunnel teardown,
  or by reopening the tunnel.

The loopback proxy tests do not test WireGuard enrollment, service authorization,
node privileges, or the deployed network policy. Qualify those separately with
the exact service versions and node bootstrap recipe in use.
