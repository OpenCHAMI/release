# OpenCHAMI Quadlet Deployment (Release RPM)

This repository provides an **RPM package** for deploying OpenCHAMI services as **Podman Quadlets**. It is **one of several valid deployment methods** and is the companion to the **[OpenCHAMI Tutorial](https://openchami.org/docs/tutorial/)**.

**Note**: OpenCHAMI is a collection of independently released microservices. This repository packages a tested combination of those microservices into a single RPM for convenience in **quadlet-based deployments**. It is **not** the official "release" of OpenCHAMI, as no single release exists—each microservice is released independently.

For a standardized way to deploy OpenCHAMI, follow the **[OpenCHAMI Tutorial](https://openchami.org/docs/tutorial/)**, which uses this RPM to set up a functional cluster.

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

## OpenCHAMI Deployment Methods

OpenCHAMI is flexible and can be deployed in multiple ways. Here are the recommended options:

| Method | Description | Recommended For |
|--------|-------------|-----------------|
| **[Tutorial](https://openchami.org/docs/tutorial/)** | Step-by-step guide using Podman Quadlets | New users, learning OpenCHAMI |
| **This RPM** | Unified RPM for quadlet-based deployments | Red Hat-based systems, production use |
| **[kube-deploy](https://github.com/OpenCHAMI/kube-deploy)** | Helm charts for Kubernetes | Kubernetes users |
| **[openchami-operator](https://github.com/OpenCHAMI/openchami-operator)** | Kubernetes operator | Advanced Kubernetes orchestration |
| **[integration-sandbox](https://github.com/OpenCHAMI/integration-sandbox)** | Testing environment | Development and testing |
| **[deployment-recipes](https://github.com/OpenCHAMI/deployment-recipes)** | Organization-specific patterns | Legacy or custom deployments *(not recommended for new users)* |

We recommend starting with the **Tutorial** before exploring other methods.

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



