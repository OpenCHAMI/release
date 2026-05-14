#! /usr/bin/bash
# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# Pick up the common setup for the prepare scripts
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null && pwd )"
source "${SCRIPT_DIR}/prep_setup.sh"

info "preparing platform - install required packages"
PRE_INSTALL_PACKAGES="\
        epel-release \
{%- for package in hosting_config.extra_packages.pre %}
        {{ package }} \
{%- endfor %}
"
PACKAGES="\
{%- if deployment_mode == 'host' %}
        libvirt \
        qemu-kvm \
        virt-install \
        virt-manager \
{%- endif %}
        dnsmasq \
        podman \
        buildah \
        git \
        ansible-core \
        openssl \
        nfs-utils \
        s3cmd \
{%- for package in hosting_config.extra_packages.main %}
        {{ package }} \
{%- endfor %}
"
dnf -y check-update || true
# packages needed before main package list install
dnf install -y ${PRE_INSTALL_PACKAGES}
# packages needed to install and use OpenCHAMI
dnf -y install ${PACKAGES}  # list of packages, should not be quoted

# Don't enable libvirt if we are not running in host mode
{%- if deployment_mode == 'host' %}
systemctl enable --now libvirtd
{%- endif %}

info "preparing platform - create the deployment user '${DEPLOY_USER}'"
if ! getent group "${DEPLOY_GROUP}"; then
    info "creating primary group '{{ group }}' for '${DEPLOY_USER}'"
    groupadd "${DEPLOY_GROUP}"
fi
{%- for group in manifest.deployment_user.supplementary_groups %}
if ! getent group "{{ group }}"; then
    info "creating supplementary group '{{ group }}' for '${DEPLOY_USER}'"
    groupadd "{{ group }}"
fi
{%- endfor %}
if ! getent passwd "${DEPLOY_USER}"; then
    info "creating user '${DEPLOY_USER}'"
    useradd -g "${DEPLOY_GROUP}" "${DEPLOY_USER}"
fi
{%- for group in manifest.deployment_user.supplementary_groups %}
if ! getent group "{{ group }}"; then
    info "adding supplementary group '{{ group }}' to '${DEPLOY_USER}'"
    usermod -aG "{{ group }}" "${DEPLOY_USER}"
fi
{%- endfor %}
# Remove the deployment user from /etc/sudoers and then put it back
# with NOPASSWD access
info "giving user '${DEPLOY_USER}' passwordless sudo access"
sed -i -e "/[[:space:]]*${DEPLOY_USER}/d" /etc/sudoers
echo "${DEPLOY_USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
