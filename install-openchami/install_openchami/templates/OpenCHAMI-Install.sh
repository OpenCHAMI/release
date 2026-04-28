#! /usr/bin/bash
# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# Set up the system level pieces needed to start deploying
# OpenCHAMI. This script is intended to be run by a user with
# passwordless 'sudo' permissions. The base node preparation script
# sets up the user 'rocky' with that before chaining here.

# Set up error handling, the environment and some functions for
# running the "prepare" scripts...
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null && pwd )"
source "${SCRIPT_DIR}/prep_setup.sh"

# Get some image building functions into our environment
source "/etc/profile.d/build-image.sh"

# List the image builder configuration files to use for building the
# base OS image, the compute node base image and the compute node
# debug image.
IMAGE_BUILDERS=(
    {%- for file in manifest.files.values() %}
    {%- if "image-builder" in file.annotations %}
    "{{ manifest.deployment_directory }}/{{ file.target }}"
    {%- endif %}
    {%- endfor %}
)

ROCKY_DIRS=(
    "/data/oci"
    "/data/s3"
)

WORK_DIRS=(
    "${DEPLOY_DIR}/boot"
    "${DEPLOY_DIR}/cloud-init"
)

S3_PUBLIC_BUCKETS=(
    "efi"
    "boot-images"
)

function cleanup_service() {
    local service="${1}"; shift || fail "no service specified"
    local dir="${1}"; shift || dir=""
    info "cleaning up service '${service}'"
    if sudo systemctl status --no-pager --full "${service}"; then
        sudo systemctl stop "${service}"
    fi
    if [ -n "${dir}" -a -d "${dir}" ]; then
        info "removing directory '${dir}'"
        sudo rm -rf "${dir}"
        sudo podman system prune -a -f --volumes
    fi
}

function ssh_to_compute_node() {
    local hostname="${1}"; shift || fail "no hostname specified"
    local user="${1}"; shift || fail "no deployment username provided"
    local check="-o StrictHostKeyChecking=no"
    local file="-o UserKnownHostsFile=/dev/null"
    local time="-o ConnectTimeout=10"
    local where="root@${hostname}"
    local retval=0
    info "Attempting to SSH to ${hostname} as ${user}"
    for retry in {0..30}; do
        if sudo su - "${user}" -c \
                "ssh ${check} ${file} ${time} ${where} true"; then
            info "Successful SSH to ${hostname} as ${user}"
            return 0
        fi
        sleep 10
    done
    info "failed to SSH to ${hostname} as ${user}"
    return 1
}


# Create the backing directories for S3 and registry that must be made
# by 'root'. If they are already there and directories, remove them
# because they have stale data in them that leaks disk space. First,
# stop the services.
sudo systemctl daemon-reload
cleanup_service minio.service /data/s3
cleanup_service registry.service /data/oci
for dir in "${ROCKY_DIRS[@]}"; do
    info "Making directory: ${dir}"
    sudo mkdir -p "${dir}"
    sudo chown -R rocky: "${dir}"
done

# Make the directories that are needed for deployment and can be made
# by rocky. If they are already there and directories, remove
# them because they have stale data in them that leaks disk space.
for dir in "${WORK_DIRS[@]}"; do
    info "Making directory: ${dir}"
    if [ -d "${dir}" ]; then
        rm -rf "${dir}"
    fi
    mkdir -p "${dir}"
done

info "turning on IPv4 forwarding"
# Turn on IPv4 forwarding on the management node to allow other nodes
# to reach OpenCHAMI services
sudo sysctl -w net.ipv4.ip_forward=1

{%- if deployment_mode == 'host' %}
# In 'host' mode, all of the compute nodes are VMs on the headnode VM.
# Clean them up so we don't have to worry about conflicts later.
{%- for node in nodes %}
if sudo virsh list --all | grep "{{ node.name }}"; then
    info "cleaning up previously existing '{{ node.name }}' VM"
    sudo virsh destroy "{{ node.name }}"
    sudo virsh undefine "{{ node.name }}" --nvram
fi
{%- endfor %}

info "removing the virtual network for the compute node VM(s) to use"
sudo virsh net-destroy {{ hosting_config.cluster_net_name }} || true
sudo virsh net-undefine {{ hosting_config.cluster_net_name }} || true

info "configuring a virtual network for the compute node VM(s) to use"
sudo virsh net-define /opt/workdir/openchami-net.xml
sudo virsh net-start {{ hosting_config.cluster_net_name }}
sudo virsh net-autostart {{ hosting_config.cluster_net_name }}
{%- endif %}

# Set up an /etc/hosts entry for the OpenCHAMI management head node so
# we can use it for certs and for reaching the services before any other
# DNS is set up.
info "Adding head node (${MANAGEMENT_HEADNODE_IP}) to /etc/hosts"
sudo sed -i /etc/hosts -e "/${MANAGEMENT_HEADNODE_FQDN}/d"
echo "${MANAGEMENT_HEADNODE_IP} ${MANAGEMENT_HEADNODE_FQDN}" | \
    sudo tee -a /etc/hosts > /dev/null

{%- if deployment_mode == 'host' %}
# While we are at it, also add the managed nodes' hostnames and IP
# addresses to /etc/hosts because, since we are in 'host' mode, we are
# not going to be using any other DNS for cluster host naming.
#
# XXX - At the moment we are using the first IP address in the first
#       interface. A better scheme should really be found using the
#       network name, the cluster network name and the interface name,
#       but I think that needs to be done in the python code not in
#       the shell code.
{%- for node in nodes %}
info "Adding managed node {{ node.hostname }} to /etc/hosts"
NODE_FQDN="{{ node.hostname }}.{{ hosting_config.net_head_domain }}"
NODE_IP="{{ node.interfaces[0].ip_addrs[0].ip_addr }}"
sudo sed -i /etc/hosts -e "/${NODE_FQDN}/d"
echo "${NODE_IP} ${NODE_FQDN} {{ node.hostname }}" | \
    sudo tee -a /etc/hosts > /dev/null
{%- endfor %}
{%- endif %}

# Reload systemd to pick up the minio and registry containers and then
# start those services
info "Restarting systemd and starting minio and registry services"
sudo systemctl daemon-reload
sudo systemctl start minio.service
sudo systemctl start registry.service

# Set up Cluster SSL Certs for the
info "Setting up cluster SSL certs for OpenCHAMI"
sudo openchami-certificate-update update "${MANAGEMENT_HEADNODE_FQDN}"

info "set management net IF in 'coredhcp.yaml'"
# Set the interface name in coredhcp.yaml
sudo sed -i \
    -e "s/::MGMT_NET_HEAD_IFNAME::/${MGMT_NET_HEAD_IFNAME}/g" \
    /etc/openchami/configs/coredhcp.yaml

# Shut down and clean up after any pre-existing OpenCHAMI that might
# be running
cleanup_service openchami.target

# Also remove any SMD or BSS data after
# giving the pods a chance to stop
sleep 5
info "clearing SMD and BSS data if present"
for retry in {1..10}; do
    if ! sudo podman volume ls | grep postgres-data >/dev/null 2>&1; then
        # The volume doesn't exist, no reason to try to remove it.
        break
    fi
    sleep 5
    if ! sudo podman volume ls --filter dangling=true |\
            grep postgres-data >/dev/null 2>&1; then
        # The volume is still in use, don't try to remove it yet, the
        # containers are probably still shutting down. Keep retrying.
        continue
    fi
    if ! sudo podman volume rm postgres-data; then
        # Removal failed for some other reason, keep retrying anyway.
        continue
    fi
    break
done
if [ "${retry}" -eq 10 ]; then
    fail "timed out waiting to clear the SMD and BSS data"
fi

# Start OpenCHAMI
info "Starting OpenCHAMI"
sudo systemctl start openchami.target

info "retrieving OpenCHAMI CLI (ochami) RPM"
OCHAMI_CLI_VERSION="latest"
latest_release_url=$(curl -s https://api.github.com/repos/OpenCHAMI/ochami/releases/${OCHAMI_CLI_VERSION} | jq -r ".assets[] | select(.name | endswith(\"$(derive_architecture).rpm\")) | .browser_download_url")
curl -L "${latest_release_url}" -o ochami.rpm
info "Installing OpenCHAMI CLI (ochami) RPM"
sudo dnf install -y ./ochami.rpm

# Configure the OpenCHAMI CLI client
info "Configuring OpenCHAMI CLI (ochami) Client"
sudo rm -f /etc/ochami/config.yaml
echo y | sudo ochami config cluster set --system --default "${CLUSTER_NAME}" \
              cluster.uri "https://${MANAGEMENT_HEADNODE_FQDN}:8443" \
    || fail "failed to configure OpenCHAMI CLI"

# Copy the application data files into their respective places so we are
# ready to build and boot compute nodes.
#
# Set up the 'rocky' user's S3 configuration
cp "${DEPLOY_DIR}/s3cfg" ~/.s3cfg

# All the rendered files have been installed in their respective
# locations, time to set things up and build some images.
#
# The first thing we need is credentials to interact with
# OpenCHAMI. Since OpenCHAMI just came up, this might not work the
# first time, so retry a few times.
for i in {1..10}; do
    get-ochami-token || DEMO_ACCESS_TOKEN=""
    if [[ "${DEMO_ACCESS_TOKEN}" != "" ]]; then
        break
    fi
    sleep 10
done
[[ "${DEMO_ACCESS_TOKEN}" != "" ]] || fail "cannot get openchami access token"

# Wait for SMD to be up and running. This can sometimes take a little
# while. If it takes more than 100 seconds, something is probably
# wrong.
smd_running=false
for i in {0..9}; do
    info "waiting for smd for up to $(( 100 - (${i} * 10) )) more seconds"
    if ochami smd component get > /dev/null 2>&1; then
        smd_running=true
        break
    fi
    sleep 10
done
if ! ${smd_running}; then
    fail "timeout waiting for SMD to start, openChami is not fully available"
fi

# Run the static node discovery
info "performing static discovery"
ochami discover static $(discovery_version) -f yaml -d @"${DEPLOY_DIR}/nodes/nodes.yaml"

# Install and configure 'regctl'
info "setting up 'regctl' to manage the registry"
curl -L https://github.com/regclient/regclient/releases/latest/download/regctl-linux-$(derive_architecture) > regctl \
    && sudo mv regctl /usr/local/bin/regctl \
    && sudo chmod 755 /usr/local/bin/regctl
/usr/local/bin/regctl registry set --tls disabled "${MANAGEMENT_HEADNODE_FQDN}:5000"

# Install and configure S3 client
info "setting up buckets in S3"
for bucket in "${S3_PUBLIC_BUCKETS[@]}"; do
    s3cmd ls | grep s3://"${bucket}" && s3cmd rb -r s3://"${bucket}"
    s3cmd mb s3://"${bucket}"
    s3cmd setacl s3://"${bucket}" --acl-public
    s3cmd setpolicy "${DEPLOY_DIR}/s3-public-read-${bucket}.json" \
          s3://"${bucket}" \
          --host="${MANAGEMENT_HEADNODE_IP}:9000" \
          --host-bucket="${MANAGEMENT_HEADNODE_IP}:9000"
done

# Build the node images...
for builder in "${IMAGE_BUILDERS[@]}"; do 
    info "Building image from image builder '${builder}'"
    build-image "${builder}"
done
{%- if deployment_mode == 'cluster' %}
# On a 'cluster' configuration, cluster hostnames are served by
# coresmd-coredns, which should be running properly at this
# point. Make sure it is and switch over to using it.
systemctl is-active --quiet coresmd-coredns.service || \
    fail "coresmd-coredns is not active, ivestigate why not and try again"

# Switch to coresmd-coredns as the nameserver
info "Switching to the cluster internal DNS nameserver"
switch_dns "${MANAGEMENT_HEADNODE_IP}" "${CLUSTER_DOMAIN}"
{%- endif %}

# Refresh ochami token after the image builds in case it expired
export DEMO_ACCESS_TOKEN="$(sudo bash -lc 'gen_access_token')"

# Create the boot configuration for the Compute node Debug image
cd "${DEPLOY_DIR}/boot"
for builder in "${IMAGE_BUILDERS[@]}"; do
    BOOT_CONFIG_FILE="${DEPLOY_DIR}/boot/$(basename "${builder}")"
    info "Building boot configuration '${BOOT_CONFIG_FILE}'"
    S3_PREFIX="$( \
      yaml_to_json < "${builder}" | jq -r '.options.s3_prefix' |
      sed -e 's:/[[:blank:]]*$::' \
    )"
    generate-boot-config \
        "${S3_PREFIX}" \
        "${MANAGEMENT_HEADNODE_IP}" \
        $(managed_macs) | \
        tee "${BOOT_CONFIG_FILE}"
done

info "Install boot configuration"
# At the moment, there is only one "active" boot image that can be set
# up. It is the iamge used by the 'compute' group in the 'images'
# section of the config. Set up a variable for easy access to the
# build script and boot script for that image.
ACTIVE_BOOT_IMAGE="{{ images.builders[images.deployment_targets['compute']].metadata.boot_param_filename }}"

ochami bss boot params set -f yaml \
       -d @"${DEPLOY_DIR}/boot/${ACTIVE_BOOT_IMAGE}"

# Set up cloud-init for some basics...
#
# First the global cloud-init metadata
# XXX - Need some templating here...
rm -f ~/.ssh/id_rsa*
ssh-keygen -t rsa -q -f ~/.ssh/id_rsa -N ""
mkdir -p "${DEPLOY_DIR}"/cloud-init
cat <<EOF | tee "${DEPLOY_DIR}"/cloud-init/ci-defaults.yaml
---
base-url: "http://${MANAGEMENT_HEADNODE_IP}:8081/cloud-init"
cluster-name: "${CLUSTER_NAME}"
nid-length: 3
public-keys:
  - "$(cat ~/.ssh/id_rsa.pub)"
short-name: "nid"
EOF
ochami cloud-init defaults set -f yaml \
       -d @"${DEPLOY_DIR}"/cloud-init/ci-defaults.yaml

# Next the cloud init metadata for the managed node groups...
for group in $(node_groups); do
    cat <<EOF | tee "${DEPLOY_DIR}/cloud-init/ci-group-${group}.yaml"
- name: ${group}
  description: "${group} group config"
  file:
    encoding: plain
    content: |
      ## template: jinja
      #cloud-config
      merge_how:
      - name: list
        settings: [append]
      - name: dict
        settings: [no_replace, recurse_list]
      users:
        - name: testuser
          ssh_authorized_keys: {{ "{{ ds.meta_data.instance_data.v1.public_keys }}" }}
        - name: root
          ssh_authorized_keys: {{ "{{ ds.meta_data.instance_data.v1.public_keys }}" }}
      disable_root: false
EOF
    ochami cloud-init group set -f yaml \
           -d @"${DEPLOY_DIR}/cloud-init/ci-group-"${group}".yaml"
done
{%- for node in nodes %}
ochami cloud-init node set \
       -d '[{"id":"{{ node.name }}","local-hostname":"{{ node.hostname}} "}]'
{% endfor %}

{%- for node in nodes %}
{%- if deployment_mode == 'cluster' %}
# In 'cluster' mode the nodes are all "physical" hosts already plugged
# into the cluster network. We just need to power them on and they
# should boot from OpenCHAMI
power-on-node "{{ node.name }}" "{{ node.bmc_name }}"
{%- else %}
# In 'host' mode, all of the compute nodes are VMs on the headnode VM,
# so we need to create them here and let them boot from OpenCHAMI.
info "installing '{{ node.name }}' VM as a managed node"
if [ "$(derive_architecture)" == 'amd64' ]; then
    # On x86_64 (amd64) we need to be more detailed about setting up the
    # boot configuration, use this instead...
    UEFI="loader=/usr/share/OVMF/OVMF_CODE.secboot.fd,loader.readonly=yes,loader.type=pflash,nvram.template=/usr/share/OVMF/OVMF_VARS.fd,loader_secure=no"
else
    # On ARM (arm64 or aarch64), the best option for setting up the
    # boot is simply 'uefi', so use that here.
    UEFI="uefi"
fi
sudo virt-install \
     --name {{ node.name }} \
     --memory 4096 \
     --vcpus 1 \
     --disk none \
     --pxe \
     --os-variant centos-stream9 \
{%- for interface in node.interfaces %}
     --network network={{ interface.network_name }},model=virtio,mac={{ interface.mac_addr }} \
{%- endfor %}
     --graphics none \
     --console pty,target_type=serial \
     --boot network,hd \
     --boot "${UEFI}" \
     --virt-type kvm \
     --noautoconsole
{%- endif %}
{%- endfor %}

# Wait for compute node(s) to come up and try to SSH to compute
# node(s) as a sanity check of the installation.
{%- for node in nodes %}
ssh_to_compute_node {{ node.hostname }} "${DEPLOY_USER}"
{%- endfor %}
