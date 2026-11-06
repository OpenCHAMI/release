<!-- SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors -->
<!-- SPDX-License-Identifier: MIT -->

# Endpoint validation and upgrade comparison

The RPM installs `openchami-validate-endpoints` and versioned JSON policies under
`/usr/share/openchami/validation/policies/`. The tool reports expected JWT behavior,
observed HTTP access and mismatches. It does not change services, firewall rules,
configuration, tokens or data. Run it explicitly; installation and upgrades never
invoke it automatically. Python 3 is the only additional runtime dependency; no pip
packages or new service dependencies are required.

## Choose a policy and vantage point

`release-v1.json` describes a selected read-only set for the packaged topology:
SMD v2.20.5, boot-service v0.3.1 and metadata-service v0.2.1 behind HAProxy. It checks
public health and existing public SMD component-list access, plus SMD's already
protected ComponentEndpoints collection with the shipped JWKS configuration.
Generated boot/metadata collection reads are **observations**, not an assertion that
their `enable_auth` setting enforces inbound JWTs. Assert JWT requirements only in a
reviewed policy qualified against the deployed service configuration.

The route classifications come from the pinned service sources:
[SMD v2.20.5](https://github.com/OpenCHAMI/smd/blob/v2.20.5/cmd/smd/routers.go),
[boot-service v0.3.1](https://github.com/OpenCHAMI/boot-service/blob/v0.3.1/cmd/server/main.go)
and [metadata-service v0.2.1](https://github.com/OpenCHAMI/metadata-service/blob/v0.2.1/cmd/server/main.go).
Requalify these expectations when service versions or configuration change.

The boot collection probe uses `/boot-service/nodes` without a trailing slash.
HAProxy strips the service prefix and boot-service v0.3.1 redirects `/nodes/` to
`/nodes` before the collection handler. Using the canonical path records collection
access rather than a redirect. The validator continues to report redirects without
following them or forwarding credentials.

`legacy-bss-v1.json` is separate for sites running legacy BSS. Dumpstate,
endpoint-history and hosts GET reflect the existing public read behavior. Bootparameters
is observed because its existing authentication depends on the site's JWKS setting.
The current RPM deploys boot-service rather than legacy BSS; do not test one as the other.

These are selected probes, not a complete API inventory. No mutation, enrollment,
phone-home, token issuance or dynamic bootstrap action is tested. Read-only GETs
can still update service access histories, metrics and logs or consume resources.
Use disposable canary data and normal maintenance windows where appropriate.

Run from each relevant access location: the head-node VM, an approved management
client and a representative provisioning network. Label the saved report with its
vantage point. A VM-local success does not establish external availability or isolation.
For direct backend comparisons, use a reviewed copy of the policy with a separate
target and the backend's unprefixed paths. Do not publish backend ports for the test.

## Run against HAProxy

```bash
openchami-validate-endpoints \
  --policy /usr/share/openchami/validation/policies/release-v1.json \
  --target smd=https://head.example:8443 \
  --target boot=https://head.example:8443 \
  --target metadata=https://head.example:8443 \
  --cacert /path/to/site-root-ca.pem \
  --json > endpoints-before.json
```

Obtain an existing short-lived token with permission for the selected SMD read using
the site's normal identity workflow. Do not paste it into command arguments. For an
interactive shell, an example that avoids shell-history token contents is:

```bash
read -r -s -p 'SMD validation token: ' OPENCHAMI_VALIDATION_TOKEN
echo
export OPENCHAMI_VALIDATION_TOKEN
openchami-validate-endpoints \
  --policy /usr/share/openchami/validation/policies/release-v1.json \
  --target smd=https://head.example:8443 \
  --target boot=https://head.example:8443 \
  --target metadata=https://head.example:8443 \
  --token-env smd=OPENCHAMI_VALIDATION_TOKEN \
  --cacert /path/to/site-root-ca.pem --json > endpoints-after.json
validation_status=$?
unset OPENCHAMI_VALIDATION_TOKEN
echo "Validator exit: $validation_status"
```

Credentials must have compatible issuer, audience, expiry and permissions. The tool
does not mint or validate JWTs locally; the service decides. The shipped release
policy uses separate logical `smd`, `boot` and `metadata` targets
even when all three use the same HAProxy address. Map an SMD token only to `smd`;
credentials are never implicitly shared between these service targets. Optionally
provide `--denied-token-env smd=NON_ADMIN_TOKEN` for a valid identity known to lack
the required authority; a `required` row then additionally expects 403 for that token.
Do not use this optional check on deployments that do not enforce authorization.

TLS certificate and hostname verification stay enabled. Use the site's CA bundle;
there is no insecure TLS option. Actual credentials require HTTPS unless the operator
explicitly selects `--allow-http-token` for a trusted internal HTTP path. Environment
HTTP proxies are ignored, and redirects are reported without following them or
forwarding credentials. Each probe has a socket timeout (default 5 seconds), with no
retries; run serially to keep load bounded. DNS resolution may have system-level timeouts.

The report contains status codes, access classes and matching expectations, never
response bodies, request credentials or response headers. It omits target URLs too.
Keep the target-to-URL and vantage-point mapping separately with the change record.
Treat reports as operational inventory. The services can still log incoming requests;
this tool does not alter server-side logging.

## Interpret results

| Policy expectation | Evidence needed to pass |
| --- | --- |
| `public` | Anonymous success from `success_statuses`; authorized success too when an authorized token is supplied. Invalid-token behavior is recorded without imposing a policy. |
| `required` | Anonymous 401, deliberately invalid JWT 401, and supplied authorized JWT success. Missing authorized credentials makes the result incomplete. Optional valid but unauthorized token must return 403. |
| `observe` | Record responses without asserting a settled JWT policy. Always incomplete rather than silently green. |
| `absent` | Anonymous HTTP 404 or 410. An outage, connection refusal, redirect or 403 is not proof the route is absent. |

HTTP 401 is authentication rejection; 403 is forbidden; 404/410 is not found;
3xx is a redirect; connection/TLS errors have no HTTP response. None is interchangeable
with successful authorized access. A gateway returning 403 to every caller fails a
JWT-required row. A login redirect fails rather than following it to an apparent 200.
These checks establish listed status behavior, not which layer enforced it or complete
JWT correctness. A 200 alone does not verify the returned resource identity or contents.

Exit codes: **0** all listed expectations passed; **1** at least one failed;
**2** incomplete coverage/policy, missing credentials/targets or invalid input. Failure
takes precedence over incomplete rows. Machine reports include separate counts and
per-probe evidence. A missing target never silently disappears. The shipped profiles
contain intentional observations, so their fully successful run still exits 2 until
those rows receive reviewed site/version-specific expectations. Do not ignore that
status or describe it as a full security pass.

## Extend policy without changing deployments

Copy the relevant shipped policy into a version-controlled site policy. Give it a new
`policy_id`; retain the original so before/after comparisons use the same expectations.
Policies under `/usr/share` are versioned package data, not site configuration. Future
RPMs should add a new policy filename/version when expectations change. An unsupported
`schema_version`, unknown field, duplicate ID or mutation method is an input error.

Schema version 1 requires exactly `schema_version`, `policy_id` and `endpoints` at the
top level. Each endpoint requires `id`, `target`, `method`, `path`, `jwt`,
`success_statuses` and `reason`. IDs/targets use letters, digits, dots, underscores and
hyphens. Only literal GET paths without query strings, fragments or traversal are
accepted. `success_statuses` is a nonempty array of 2xx status codes.

Example for a future or site-approved JWT requirement, **not current release policy**:

```json
{
  "schema_version": 1,
  "policy_id": "site-admin-reads-v2",
  "endpoints": [
    {
      "id": "metadata-groups",
      "target": "metadata",
      "method": "GET",
      "path": "/groups/",
      "jwt": "required",
      "success_statuses": [200],
      "reason": "Site-approved administrative read policy after auth migration"
    }
  ]
}
```

The matching target could be `metadata=https://head.example:8443/metadata-service`.
Choosing a stricter validation expectation does not implement it on the service.
Keep `observe` rows visible until the site policy specifies the expected access
behavior. Test mutations with service regression tests and disposable integration
fixtures; schema v1 rejects them rather than attempting invalid-body or fake-ID
requests on a live deployment.

## Upgrade checklist

1. Record RPM/service image versions, effective configuration, chosen policy hash,
   target mapping and vantage point. Capture a before report with existing settings.
   Resolve unexpected anonymous access, unavailable public routes and token failures
   rather than changing expectations merely to get a green report.
2. Compare active HAProxy configuration with any `.rpmnew` file: `%config(noreplace)`
   can retain old identity-header rules. Preserve the current routes and forwarding
   sanitization. Use the configuration checks in [metadata-security.md](metadata-security.md)
   before an operator performs a controlled restart. Inspect effective Quadlet
   overrides and published ports; an HTTP probe does not inventory network exposure.
3. After the reviewed update, repeat with the **same policy, targets, vantage point
   and equivalent token privileges**, saving a separate report. Compare `id`, `jwt`,
   `expected`, probe status/access and verdict; timestamps naturally differ. JSON reports
   include the exact policy file's SHA-256 hash. Record
   policy changes separately from behavior changes.
4. Qualify bootstrap and actual CLI workflows independently. A read-only validator
   cannot establish WireGuard ownership, node-specific payload isolation, mutation
   authorization, forwarding-header safety or database upgrade correctness. Keep
   the loopback HAProxy tests and service-specific security tests as release gates.
5. If results regress, keep the previous report, active config and known deployed
   image digests available for a reviewed rollback/forward fix. The validator and
   its policies require no service-data migration. Do not automatically restore an
   unsafe identity-header configuration or weaken auth based on a single failed probe.

Nothing runs automatically during RPM scriptlets. Deployment changes, policy approval,
token provisioning and release publication remain explicit operator actions.
