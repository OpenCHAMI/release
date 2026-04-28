# OpenCHAMI Installer

The OpenCHAMI Installer consists of a Python wrapper and a base
configuration designed to deploy OpenCHAMI onto a host node using the
quadlet implementation of OpenCHAMI described in the [OpenCHAMI
Tutorial](https://openchami.org/docs/tutorial/) using a "`host` mode"
configuration that creates and boots a single virtual managed
(compute) node co-resident on the OpenCHAMI headnode host. The
installer can be used either to deploy OpenCHAMI and the virtual
managed node on physical hardware or on a virtual machine, as long as
the virtual machine supports nested virtualization and has sufficient
resources to run both the OpenCHAMI headnode software and the virtual
managed node.

The OpenCHAMI Installer can also run in a "`cluster` mode" in which
the OpenCHAMI head node and all managed nodes are connected to a
physical or virtual network cluster where the managed nodes are not
co-resident on the host node. In this case, the assumption is that the
managed nodes can be powered on, powered off, and reset using RedFish
calls to RedFish instances running on Base Board Management
Controllers (BMCs) accesible across a network from the headnode.

  __NOTE: The 'cluster' mode is still under development and not quite
  ready for use.__

## System Requirements

At present, the OpenCHAMI Installer uses the 'dnf' package manager,
which is an RPM based package manager primarily used on RedHat
systems. The installer expects to run on a Rocky Linux or similar
distribution of Linux.

The installer can currently successfully install OpenCHAMI and
bring up virtual compute nodes on x86-64 (amd64) and AMD-64 (aarch64)
hosts. The default configuration assumes x86-64. This README provides
an example configuration overlay to enable AMD-64 operation, as well
as a broader description of configuration overlays.

For `host` mode operation, the OpenCHAMI Installer recommends a
minimum of 4GB of memory, 4 CPU cores and 40GB of free disk space on
the headnode. If the headnode is a VM it must support nested
virtualization for the installer to work in `host` mode. On MacOS,
currently, nested virtualization is only supported by VMs running on
an M3 or better system under Apple Virtualization not those running
under KVM.

The installer requires a minimum version 3.9 of Python installed on
the headnode.

The user running the OpenCHAMI Installer must either be `root` or have
`sudo` access on the headnode.

The host system must have `openchami` (this package) installed on it
either by means of downloading the release RPM and installing it or by
means of obtaining the source code, building the RPM and installing
it. To install from the release RPM, do the following:

```
# Identify the latest release RPM
RELEASE_VERSION="latest"
API_URL="https://api.github.com/repos/openchami/release/releases/${RELEASE_VERSION}"
release_json=$(curl -s "$API_URL")
rpm_url=$(echo "$release_json" | jq -r '.assets[] | select(.name | endswith(".rpm")) | .browser_download_url' | head -n 1)
rpm_name=$(echo "$release_json" | jq -r '.assets[] | select(.name | endswith(".rpm")) | .name' | head -n 1)

# Download the RPM
curl -L -o "$rpm_name" "$rpm_url"

# Install the RPM
sudo dnf install -y ./"$rpm_name"
```

Installation from source is described in the
[OpenCHAMI Release README](https://github.com/OpenCHAMI/release/blob/main/README.md#openchami-releases).


## Installing and Running the Installer

The installer is installed on the OpenCHAMI headnode when the
OpenCHAMI Release RPM is installed. This permits the installer to
track with versions of the OpenCHAMI Release repository. The steps
involved in installing and running the installer are as follows:

1. Use the OpenCHAMI Installer to prepare the headnode for OpenCHAMI
installation:

```shell
sudo install_openchami -p
```

2. Use the OpenCHAMI Installer to install OpenCHAMI and start a
virtual compute node:

```shell
sudo install_openchami
```

__NOTE: If your are running on an arm64 (aarch64) host, you will need
to change the repository URLs in the default image builder
configuration. See the 'Configuration' section below to learn how to
do this with a configuration overlay.__

Assuming this completes successfully, you should be able to become the
deployment user (by default this is `rocky`) and SSH to your virtual
compute node:

```shell
sudo su - rocky
ssh root@compute-001
```

## Configuration

The OpenCHAMI Installer contains a rich configuration that allows for
both future changes to OpenCHAMI and changes to the way OpenCHAMI is
installed on your headnode. This configuration, in turn drives the
creation of configuration files and scripts used internally to install
OpenCHAMI. The base configuration drives an installation quite similar
to the OpenCHAMI tutorial with virtual managed (compute) nodes. This
base configuration can be modified at run time by providing the paths
to one or more YAML format configuration overlays on the command line.

For example, to change the repository URLs in the image builders so you
can deploy this on an `arm64` (`aarch64`) host, all that is required is a
configuration overlay that overrides those URLs. Something like this:

```yaml
images:
  builders:
    rocky-base-9:
      data:
        repos:
        # Note: since 'repos' is a list, all of the elements need to be
        #       specified fully as the new list will completely replace
        #       the list in the default configuration.
        - alias: 'Rocky_9_BaseOS'
          # Change the 'url' field from x86_64 (in the default config) to
          # 'aarch64' in your config to pull packages of the correct
          # machine architecture.
          url: 'https://dl.rockylinux.org/pub/rocky/9/BaseOS/aarch64/os/'
          gpg: 'https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9'
        - alias: 'Rocky_9_AppStream'
          # Change the 'url' field from x86_64 (in the default config) to
          # 'aarch64' in your config to pull packages of the correct
          # machine architecture.
          url: 'https://dl.rockylinux.org/pub/rocky/9/AppStream/aarch64/os/'
          gpg: 'https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9'
    compute-base-rocky9:
      data:
        # Note: since 'repos' is a list, all of the elements need to be
        #       specified fully as the new list will completely replace
        #       the list in the default configuration
        repos:
        - alias: 'Epel9'
          # Change the 'url' field from x86_64 (in the default config) to
          # 'aarch64' in your config to pull packages of the correct
          # machine architecture.
          url: 'https://dl.fedoraproject.org/pub/epel/9/Everything/aarch64/'
          gpg: 'https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-9'
```

When creating a configuration overlay, it helps to know what the
configuration to be overlaid looks like, and what the configuration
looks like after applying the overlay. There are two options to the
installer that allow you to see the contents of the OpenCHAMI
Installer configuration. The first option dumps out the entire contents
of the base configuration file, complete with comments explaining the
pieces. This is a good place to start:

```shell
python3 -m install_openchami -b
```

From there you can cut and paste the necessary pieces to create new
configuration overlays.

The second option dumps out the final configuration after applying
your configuration overlay(s):

```shell
python3 -m install_openchami -c amd64_config_overlay.yaml
```

This configuration may be in a different order from the base
configuration and is not commented, but it allows you to verify that
your configuration changes were applied the way you want them.

To validate your OpenCHAMI Installer final configuration, use:

```shell
python3 -m install_openchami -v amd64_config_overlay.yaml
```

This helps ensure that your configuration is correct and
consistent, and, where possible, required system elements are in place
to support the configuration you have created.

Install your newly configured OpenCHAMI system by first preparing the
host node using:

```shell
sudo install_openchami -p amd64_config_overlay.yaml
```

then installing the new configuration using:

```shell
sudo install_openchami amd64_config_overlay.yaml
```

If all went well, you should have OpenCHAMI running on a 64 bit AMD host
with a co-located VM serving as compute node.

```shell
sudo su - rocky
ssh root@compute-001
```

The OpenCHAMI Installer has been designed to be able to be run
correctly multiple times on the same host with new configurations, so,
if you tried installing on an AMD system before reading this part, you
should be able to simply re-run with the new configuration overlay.

This mechanism also allows you to change many other aspects of how your
OpenCHAMI system is installed. The AMD overlay was simply a convenient
way to demonstrate the mechanism and enable AMD installs.

## Limitations

The OpenCHAMI Installer currently has the following
limitations. Except where otherwise noted, solutions to these are
being investigated and implemented:

- the 'cluster' mode is experimental
- there is no 'remove' operation in the OpenCHAMI Installer
- while the OpenCHAMI Installer tries to be re-usable, it is not
  perfectly idempotent, so situations may arise where re-running the
  installer fails leaving the host in an inconsitent state. There are
  currently no known instances of this, but with arbitrary
  configuration overlays, not every case can be tested.
- along similar lines, the OpenCHAMI installer is not protected against
  being interrupted (for example CTRL-C) in the middle of a sensitive
  operation that may leave the system in an inconsistent state -- it is
  safest not to interrupt a running instance.
- the minimum configuration of the headnode can host up to two virtual
  managed nodes. To host more than that, use a host with more CPU,
  Memory and Disk resources.
- issues have been seen with the `openchami-external` podman network
  disappearing after several runs of the installer. This appears to be
  intractable without a reboot, but a reboot of the host node will clear
  it.
- issues have been seen with the digests of boot images not matcing (some
  kind of corruption of the boot image either in or on the way to the
  registry). We are currently stopping the registry, removing both the
  disk resident registry storage and the podman volume and then restarting
  what should be a fresh registry to alleviate this. It does not always
  work. Rebooting the host node seems to clear this problem.
