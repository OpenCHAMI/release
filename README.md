# OpenCHAMI Releases

OpenCHAMI is a collection of microservices that are assembled and tested to provide HPC cluster provisioning and management.  It is released quarterly.  As far as possible, each release is supported for three years from the release date.  Since some of the components in OpenCHAMI are not developed by the consortium, we cannot promise support beyond that provided by the upstream projects.  See our [Release Policy](/Release_Policy.md) for more details.

## Building Locally

Requirements:

- `rpmdevtools`
- `make`

Generate `openchami-<version>-1.noarch.rpm` in this repo:

```bash
make
```

Increase the release version (`openchami-<version>-2.noarch.rpm`):

```bash
make RELEASE=2
```

Clean built RPMs in repo directory:

```
make clean
```

## Automated RPM Signing

The GitHub release workflow signs built RPMs with the repository signing subkey
stored in the `GPG_SUBKEY_B64` repository secret. The workflow also exports the
matching ASCII-armored public key as a release asset so downstream consumers can
verify the published RPM signature.

## Current Release

OpenCHAMI is in development without an initial release.  We expect a first supported release in Q1 2025.  If you would like to follow the most current, stable configuration, each of the partners maintains a deployment recipe that will become a release candidate in our [Deployment Recipes](https://github.com/OpenCHAMI/deployment-recipes) Repository.

### Feature Map

- [x] Redfish-based automatic node discovery with firmware updates
- [x] Inventory-driven DHCP
- [ ] Inventory-driven DNS
- [x] Ansible Inventory Provider
- [x] Post-Boot configuration through customizable cloud-init
- [x] Customizable API-driven iPXE scripts
- [x] OIDC and JWT-based authentication/authorization with short-lived, narrowly scoped tokens
- [x] Podman Quadlet deployment with SystemD integration
- [x] Docker Compose deployment option
- [x] Kubernetes deployment option
- [x] Optional Image Builder for RHEL-based Operating Systems
- [x] OS Agnostic Boot Chain
- [ ] Persistent State for cloud-init services
- [ ] Backup and Recovery Process
- [ ] Sysadmin documentation and runbooks
- [ ] Standardized Logging
- [x] Secure Machine Identity


## Latest Microservice Releases

| Repository | Release | Container | Attestations |
| :---: | :----: | :----: | :------: | 
| [OpenCHAMI/BSS](https://github.com/openchami/bss) | [![BSS Release](https://badgen.net/github/release/openchami/bss/stable)](https://github.com/openchami/bss/releases) | [ghcr.io/openchami/bss](https://github.com/OpenCHAMI/bss/pkgs/container/bss) | [Attestations](https://github.com/OpenCHAMI/bss/attestations) |
| [OpenCHAMI/SMD](https://github.com/openchami/smd) | [![SMD Release](https://badgen.net/github/release/openchami/smd/stable)](https://github.com/openchami/smd/releases) | [ghcr.io/openchami/smd](https://github.com/OpenCHAMI/smd/pkgs/container/smd) | [Attestations](https://github.com/OpenCHAMI/smd/attestations) |
| [OpenCHAMI/cloud-init](https://github.com/openchami/cloud-init) | [![Cloud-Init Release](https://badgen.net/github/release/openchami/cloud-init/stable)](https://github.com/openchami/cloud-init/releases) | [ghcr.io/openchami/cloud-init](https://github.com/OpenCHAMI/cloud-init/pkgs/container/cloud-init) | [Attestations](https://github.com/OpenCHAMI/cloud-init/attestations) |
| [OpenCHAMI/coresmd](https://github.com/openchami/coresmd) | [![Coresmd Release](https://badgen.net/github/release/openchami/coresmd/stable)](https://github.com/openchami/coresmd/releases) | [ghcr.io/openchami/coresmd](https://github.com/OpenCHAMI/coresmd/pkgs/container/coresmd) | [Attestations](https://github.com/OpenCHAMI/coresmd/attestations) |
| [OpenCHAMI/magellan](https://github.com/openchami/magellan) | [![Magellan Release](https://badgen.net/github/release/openchami/magellan/stable)](https://github.com/openchami/magellan/releases) | [ghcr.io/openchami/magellan](https://github.com/OpenCHAMI/magellan/pkgs/container/magellan) | [Attestations](https://github.com/OpenCHAMI/magellan/attestations) |
| [OpenCHAMI/image-builder](https://github.com/openchami/image-builder) | [![image-builder Release](https://badgen.net/github/release/openchami/image-builder/stable)](https://github.com/openchami/image-builder/releases) | [ghcr.io/openchami/image-builder](https://github.com/OpenCHAMI/image-builder/pkgs/container/image-builder) | [Attestations](https://github.com/OpenCHAMI/image-builder/attestations) |



