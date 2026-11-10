<!-- SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors -->
<!-- SPDX-License-Identifier: MIT -->

# 0.1.x service update and upgrade notes

These changes prepare the next patch of the legacy RPM line. They do not
constitute a published RPM or completed site deployment qualification.

| Service | Previous | Updated |
| --- | --- | --- |
| [cloud-init](https://github.com/OpenCHAMI/cloud-init/releases/tag/v1.4.15) | v1.3.0 | v1.4.15 |
| [BSS](https://github.com/OpenCHAMI/bss/releases/tag/v1.32.4), including bss-init | v1.32.2 | v1.32.4 |
| [SMD](https://github.com/OpenCHAMI/smd/releases/tag/v2.20.5), including smd-init | v2.19.3 | v2.20.5 |

BSS removes credential-bearing log output while preserving its API. Dumpstate,
history and hosts GET retain their existing access policy. SMD retains its default
legacy JWT backend and public/protected route split. This RPM update does not
select TokenSmith authentication or enforced authorization scopes. SMD now exits
after its JWKS initialization retries fail. Confirm OPAAL and its key endpoint are
ready, and check SMD restart/readiness behavior before discovery or boot tests.

CoreSMD stays at v0.4.3: adopting v0.7.x requires a separate migration of the DHCP
configuration format and boot-script URI settings. OPAAL, Hydra and the legacy
topology are retained. Metadata-service, boot-service and TokenSmith are not added.

## Cloud-init administration now requires JWTs

All `/admin` operations, including enabled impersonation routes, require a bearer
JWT. Update site scripts and ochami-cli commands to send a token accepted by
`JWKS_URL`. The shipped environment already points to `http://opaal:3333/keys`;
verify that this endpoint is reachable from cloud-init during startup.

With a working verifier, missing or invalid tokens return 401. Missing or failed
JWKS initialization instead returns 503 for admin requests; correct configuration
and restart the service. Verified tokens must contain `sub`, `iss` and `aud`, but
expected issuer/audience values and roles/scopes are not enforced. Use keys and
issuance trusted for admin access; audience or role isolation is not established
by this check. See the versioned [admin authentication contract](https://github.com/OpenCHAMI/cloud-init/blob/v1.4.15/docs/admin-authentication.md).

Node bootstrap paths retain their existing WireGuard and identity checks and do
not acquire an operator JWT requirement from the new admin middleware.

Back up or export site cloud-init configuration before restarting and prepare
authenticated commands to restore/reseed it. Default storage remains in memory,
so a restart can discard state. This update does not migrate storage or change
volume layout. Preserve any site persistence overrides.

## Qualification before rollout

Use a disposable deployment with representative configuration and no production
credentials. Check both the direct backend and the site's HAProxy ingress:

1. Request `/admin/groups` directly and `/cloud-init/admin/groups` through the
   proxy. Missing and invalid tokens must return 401; an accepted admin token must
   return the expected data. Qualify the installed ochami-cli and actual scripts.
2. Perform a disposable authenticated admin write and read it back. The same
   operation without a token or with an invalid token must fail without modifying
   state. Exercise impersonation when enabled.
3. Confirm metadata, user-data, vendor-data, WireGuard enrollment and phone-home
   through the site's normal node path without an operator JWT.
4. Confirm BSS bootscript delivery and dumpstate/history/hosts reads. Check SMD
   health, inventory reads, discovery and a disposable authenticated mutation with
   the site's existing OPAAL tokens.
5. Complete a node boot, including DHCP/DNS. HTTP reachability alone does not
   establish successful bootstrap.

## Rollout and rollback

Inventory effective Quadlets, image versions/digests, site overrides, secrets,
configuration and volume backups. Schedule a maintenance window: existing RPM
scriptlets invoke bootstrap and systemd reload behavior. Package build tests do
not execute those scriptlets or qualify a running head node.

Configuration uses `%config(noreplace)`. Review `.rpmnew` files deliberately and
verify generated systemd units: local Quadlets may override packaged images.
Keep the previous RPM, resolved image digests and backups. Test older services
against saved state before relying on a downgrade; an image rollback does not
reverse newer service writes. Retain authenticated admin clients for rollback.

This update changes neither the RPM release number nor third-party image pins.
Image tags are version-pinned; record their resolved digests during qualification.
