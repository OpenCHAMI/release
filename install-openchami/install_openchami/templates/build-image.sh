# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# Report a failure message on stderr
function _bi_fail() {
    local func=${FUNCNAME[1]:-"unknown-function"} # Calling function
    local message="${*:-"failing for no specified reason"}"
    echo "${func}: ${message}" >&2
    return 1
}

function build-image() {
    set -e
    local config="${1}"; shift || _bi_fail "image config file not specified"
    # Build with the specified builder. Default to using the RH9 builder
    local builder="${1:-"ghcr.io/openchami/image-build-el9:latest"}"
    [[ -f "${config}" ]] || _bi_fail "${config} not found"
    podman run \
           --network=host \
           --rm \
           --device /dev/fuse \
           -e S3_ACCESS=admin \
           -e S3_SECRET=admin123 \
           -v "$(realpath "${config}")":/home/builder/config.yaml:Z \
           ${EXTRA_PODMAN_ARGS} \
           "${builder}" \
           image-build \
           --config config.yaml \
           --log-level DEBUG || _bi_fail "cannot build image defined in ${config}"
}

function build-image-rh9() {
    local config="${1}"; shift || _bi_fail "image config file not specified"
    build-image "${config}"
}

function build-image-rh8() {
    local config="${1}"; shift || _bi_fail "image config file not specified"
    local builder="ghcr.io/openchami/image-build:v0.1.0"
    build-image "${config}" "${builder}"
}

function generate-boot-config() {
    local image_subpath="${1}"; shift || _bi_fail "image subpath (example 'compute/debug') not provided as first argument"
    local headnode_ip="${1}"; shift || _bi_fail "management head-node IP address not provided as second argument"
    local macs="$(for mac in "$@"; do echo "${mac}"; done)"
    [[ "${macs}" != "" ]] || _bi_fail "no target node MAC addresses provided"
    cd /opt/workdir/boot
    local uris="$(s3cmd ls -Hr s3://boot-images | grep "${image_subpath}" | \
                        awk '{print $4}' | \
                        sed "s-s3://-http://${headnode_ip}:9000/-" | \
                        xargs)"
    local uri_img="$(echo "${uris}" | cut -d' ' -f1)"
    [[ "${uri_img}" != "" ]] || _bi_fail "no disk image found that matches '${image_subpath}'"
    local uri_initramfs="$(echo "${uris}" | cut -d' ' -f2)"
    [[ "${uri_initramfs}" != "" ]] || _bi_fail "no initrd image found that matches '${image_subpath}'"
    local uri_kernel="$(echo "${uris}" | cut -d' ' -f3)"
    [[ "${uri_kernel}" != "" ]] || _bi_fail "no kernel image found that matches '${image_subpath}'"
    cat <<EOF
---
kernel: '${uri_kernel}'
initrd: '${uri_initramfs}'
params: 'nomodeset ro root=live:${uri_img} ip=dhcp overlayroot=tmpfs overlayroot_cfgdisk=disabled apparmor=0 selinux=0 console=ttyS0,115200 ip6=off cloud-init=enabled ds=nocloud-net;s=http://${headnode_ip}:8081/cloud-init'
macs:
$(for mac in ${macs}; do echo "  - ${mac}"; done)
EOF
}

function __bmc_user() {
    local name="${1}"; shift || _bi_fail "BMC name not provided for __bmc_user"
    sudo cat /etc/vtds/bmc_info.json | \
        jq -r ".[] | select(.name == \"${name}\") | .redfish_username"
}

function __bmc_password() {
    local name="${1}"; shift || _bi_fail "BMC name not provided for __bmc_user"
    sudo cat /etc/vtds/bmc_info.json | \
        jq -r ".[] | select(.name == \"${name}\") | .redfish_password"
}

function __node_reset() {
    local reset_type="${1}"; shift || _bi_fail "no reset type supplied"
    local node_name="${1}"; shift || _bi_fail "no node name provided"
    local bmc_name="${1}"; shift || _bi_fail "no BMC name provided"
    local bmc_url="https://${bmc_name}/redfish/v1/Systems"
    local node_action="${node_name}/Actions/ComputerSystem.Reset"

    curl -k \
         -u "$(__bmc_user "${bmc_name}"):$(__bmc_password "${bmc_name}")" \
         -H "Content-Type: application/json" \
         -X POST -d "{\"ResetType\": \"${reset_type}\" }" \
         "${bmc_url}/${node_action}"
}

function power-on-node() {
    __node_reset "On" "$@"
}

function power-off-node() {
    __node_reset "ForceOff" "$@"
}

function restart-node() {
    __node_reset "ForceRestart" "$@"
}

function get-ochami-token() {
    export DEMO_ACCESS_TOKEN="$(sudo bash -lc 'gen_access_token')"
}
