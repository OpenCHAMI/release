<!-- SPDX-FileCopyrightText: 2026 OpenCHAMI Contributors -->
<!-- SPDX-License-Identifier: MIT -->

# 0.2.x service update and upgrade notes

These changes prepare the next patch of the RPM line. They do not constitute a
published RPM or completed site deployment qualification.

| Service | Previous | Updated |
| --- | --- | --- |
| [boot-service](https://github.com/OpenCHAMI/boot-service/releases/tag/v0.3.3) | v0.3.1 | v0.3.3 |
| [metadata-service](https://github.com/OpenCHAMI/metadata-service/releases/tag/v0.2.2) | v0.2.1 | v0.2.2 |
| [TokenSmith](https://github.com/OpenCHAMI/tokensmith/releases/tag/v0.4.2) | v0.4.1 | v0.4.2 |
| [CoreSMD](https://github.com/OpenCHAMI/coresmd/releases/tag/v0.7.2), DHCP and DNS | v0.7.0 | v0.7.2 |

SMD and smd-init remain together at v2.20.5. This topology uses metadata-service
and boot-service; legacy cloud-init v1.4.15 and BSS belong to the separate 0.1.x
update.

Boot-service includes HSM membership-cache and Fabrica-generated changes. Its
sync now fetches `/hsm/v2/memberships?type=node` in bulk and fails a synchronization
cycle if a compute node has no membership entry. Before rollout, confirm the
collection is readable with the service token and complete for all compute nodes.
Afterward, verify synced node/group counts and actual group-based boot selection.
Metadata-service updates Fabrica client dependencies. TokenSmith adds identity,
OIDC and token-management behavior: sites using external identity, introspection,
MFA or revocation must qualify those workflows with their own configuration.
The Quadlet now explicitly runs `serve --enable-local-user-mint`, matching the new
image entrypoint. The shipped environment already sets signing-key, bootstrap and
refresh-store paths under `/tokensmith/data`; preserve these paths and the existing
volume when merging site overrides. The local service-token bootstrap remains
configured as before; this RPM update does not enable a new identity provider.

CoreSMD adds defensive SMD HTTP-client behavior and dependency/runtime fixes.
The shipped configuration already uses key/value options and `ipxe_uri`; preserve
site DHCP options, address rules and boot-script URLs.

The [endpoint validation guide](endpoint-validation.md) and `release-v1.json` now
identify the updated packaged versions. Public health and existing SMD JWT
expectations are retained. Boot/metadata collection reads remain observations,
not claims that inbound JWT enforcement is provided by `enable_auth`.

## Qualification before rollout

Use a disposable deployment with representative configuration and no production
credentials:

1. Run `openchami-validate-endpoints` before and after the upgrade with the same
   reviewed policy, direct/proxied targets and authorized test token. Save and
   compare JSON reports using the endpoint guide. Investigate mismatches and
   incomplete observations.
2. Verify metadata/boot health, persisted data after restart, SMD synchronization,
   and service-token mint/exchange. With disposable data, exercise metadata groups
   and boot nodes/configurations, then request actual node metadata and bootscript.
3. Qualify the site's TokenSmith user-token and external-identity flows, including
   refresh/revocation when used. HTTP reachability alone does not establish claim
   or authorization compatibility.
4. Complete DHCP, DNS and a representative node boot. Verify the selected boot
   script, kernel/initrd and configuration data.

## Rollout and rollback

Inventory effective Quadlets, image versions/digests, site overrides, secrets,
configuration and volume backups. Schedule a maintenance window: existing RPM
scriptlets invoke bootstrap and systemd reload behavior. Package build tests do
not execute those scriptlets or qualify a running head node.

Configuration uses `%config(noreplace)`. Review `.rpmnew` files deliberately and
verify generated systemd units: local Quadlets may override packaged images.
Keep the previous RPM, resolved image digests and backups. Test older services
against saved state before relying on a downgrade; an image rollback does not
reverse newer service writes.

This update changes neither the RPM release number nor third-party image pins.
Image tags are version-pinned; record their resolved digests during qualification.
