#! /usr/bin/bash
# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# Set up the system level pieces needed to start deploying
# OpenCHAMI. This script is intended to be run by a user with
# passwordless 'sudo' permissions. The base node preparation script
# sets up the user 'rocky' with that before chaining here.

# Common setup for the prepare node scripts
set -o errexit -o errtrace
function error_handler() {
    local filename="${1}"; shift
    local lineno="${1}"; shift
    local exitval="${1}"; shift
    echo "exiting on error [${exitval}] from ${filename}:${lineno}" >&2
    exit ${exitval}
}
trap 'error_handler "${BASH_SOURCE[0]}" "${LINENO}" "${?}"' ERR

function fail() {
    local message="${*:-"failing for no specified reason"}"
    echo "${BASH_SOURCE[1]}:${BASH_LINENO[0]}:[${FUNCNAME[1]}]: ${message}" >&2
    return 1
}

function info() {
    local message="${*:-"failing for no specified reason"}"
    echo "INFO: ${message}" >&2
}

function discovery_version() {
    # The version of SMD changed how ochami needs to feed it manually
    # discovered node data at 2.19. We need an extra option to address
    # that if the version is 2.18 or lower.
    local major=""
    local minor=""
    local patch=""
    IFS='.' read major minor patch < \
       <( \
          sudo podman ps | \
              grep '/smd:v' | \
              awk '{sub(/^.*:v/, "", $2); print $2 }'\
       )
    if [ "${major}" -le "2" -a "${minor}" -lt "19" ]; then
       echo "--discovery-version=1"
    fi
}

function node_groups() {
    # Templated mechamism for getting a list of unique node 'group'
    # names from the list of managed nodes.
    sort -u <<EOF
{%- for node in nodes %}
{{ node.node_group }}
{%- endfor %}
EOF
}

function managed_macs() {
    cat <<EOF
{%- for node in nodes %}
{%- for interface in node.interfaces %}
{%- if interface.network_name == node.cluster_net_interface %}
{{ interface.mac_addr }}
{%- endif %}
{%- endfor %}
{%- endfor %}
EOF
}

function find_if_by_addr() {
    addr=${1}; shift || fail "no ip addr supplied when looking up ip interface"
    ip --json a | \
        jq -r "\
          .[] | .ifname as \$ifname | \
          .addr_info | .[] | \
              select( .family == \"inet\") | \
              select( (.local) == \"${addr}\" ) | \
              \"\(\$ifname)\" \
        "
}

function switch_dns() {
    # This function uses nmcli to find and remove all nameservers from
    # the current configuration and then to add back only the local
    # management network IP as a nameserver on the management
    # network. It is complicated because nmcli is complicated...
    #
    # First, get the list of connections (interfaces) with nameservers
    # assigned to them...
    local nameserver="${1}"; shift || fail "no nameserver specified to switch to"
    local domain="${1}"; shift || fail "no search domain specified"
    local connection=""
    local connections="$(
        for connection in $(nmcli --terse --fields NAME connection show); do
            echo -n "${connection} "
            nmcli connection show "${connection}" | grep ipv4.dns:
        done | grep -v '[-]-' | cut -d ' ' -f 1
    )"

    # Now, strip off the nameserver from each of the affected connections...
    for connection in ${connections}; do
        sudo nmcli connection modify "${connection}" ipv4.dns "" && \
            sudo nmcli connection down "${connection}" && \
            sudo nmcli connection up "${connection}"
    done

    # Now find the first interface (nmcli connection) that routes to
    # the desired name server IP address.
    connection="$(ip --json route get "${nameserver}" | jq -r '.[0] | .dev')"
    [[ "${connection}" != "" ]] || fail "no interface found that can reach the DNS server '${nameserver}'"

    # Set the nameserver on the connection and put the cluster domain
    # in the search on the same connection
    sudo nmcli connection modify "${connection}" ipv4.dns "${nameserver}" && \
        sudo nmcli connection modify "${connection}" ipv4.dns-search "${domain}" && \
        sudo nmcli connection down "${connection}" && \
        sudo nmcli connection up "${connection}"
}

function yaml_to_json() {
    python3 -c 'import yaml, json, sys; json.dump(yaml.safe_load(sys.stdin), sys.stdout, indent=2)'
}

function derive_architecture() {
    local uname_arch="$(uname -m)"
    case "${uname_arch}" in
        arm64|aarch64) echo "arm64";;
        amd64|x86_64) echo "amd64";;
        *) fail "unknown platform architecture '${uname_arch}'";;
    esac
}

# Some useful variables that can be templated
CLUSTER_DOMAIN="{{ hosting_config.net_head_domain }}"
CLUSTER_NAME="{{ hosting_config.cluster_name }}"
MANAGEMENT_HEADNODE_IP="{{ hosting_config.net_head_ip }}"
MANAGEMENT_HEADNODE_NAME="{{ hosting_config.nethead_hostname }}"
MANAGEMENT_HEADNODE_FQDN="{{ hosting_config.net_head_hostname }}.{{ hosting_config.net_head_domain }}"
MANAGEMENT_EXT_NAMESERVER="{{ hosting_config.net_head_dns_server }}"
MGMT_NET_HEAD_IFNAME="$(find_if_by_addr "${MANAGEMENT_HEADNODE_IP}")"
DEPLOY_DIR="{{ manifest.deployment_directory }}"
DEPLOY_USER="{{ manifest.deployment_user.username }}"
DEPLOY_GROUP="{{ manifest.deployment_user.primary_group }}"
