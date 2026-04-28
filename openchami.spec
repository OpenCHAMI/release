Name:           openchami
Version:        %{version}
Release:        %{rel}
Summary:        OpenCHAMI RPM package

License:        MIT
URL:            https://openchami.org
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       podman
Requires:       jq
Requires:       curl
Requires:       python >= 3.9
Requires(post): coreutils
Requires(post): openssl
Requires(post): hostname
Requires(post): sed

%description
The quadlets, systemd units, and config files for the Open Composable, Heterogeneous, Adaptable Management Infrastructure

%prep
%setup -q

%build
%install
# 1) Install config, unit, and script files
mkdir -p %{buildroot}/etc/openchami/configs \
         %{buildroot}/etc/openchami/pg-init \
         %{buildroot}/etc/containers/systemd \
         %{buildroot}/etc/systemd/system \
         %{buildroot}/usr/bin \
         %{buildroot}/etc/profile.d \
         %{buildroot}/usr/libexec/openchami

cp -r systemd/configs/*                 %{buildroot}/etc/openchami/configs/
cp -r systemd/containers/*              %{buildroot}/etc/containers/systemd/
cp -r systemd/volumes/*                 %{buildroot}/etc/containers/systemd/
cp -r systemd/networks/*                %{buildroot}/etc/containers/systemd/
cp -r systemd/targets/*                 %{buildroot}/etc/systemd/system/
cp -r systemd/system/*                  %{buildroot}/etc/systemd/system/
cp scripts/bootstrap_openchami.sh       %{buildroot}/usr/libexec/openchami/
cp scripts/openchami-certificate-update %{buildroot}/usr/bin/
cp scripts/openchami_profile.sh         %{buildroot}/etc/profile.d/openchami.sh
cp scripts/multi-psql-db.sh             %{buildroot}/etc/openchami/pg-init/multi-psql-db.sh
cp scripts/ohpc-nodes.sh          %{buildroot}/usr/libexec/openchami/

chmod +x %{buildroot}/usr/libexec/openchami/bootstrap_openchami.sh
chmod +x %{buildroot}/usr/libexec/openchami/ohpc-nodes.sh
chmod +x %{buildroot}/usr/libexec/openchami/bootstrap_openchami.sh
chmod +x %{buildroot}/usr/bin/openchami-certificate-update
chmod +x %{buildroot}/usr/libexec/openchami/ohpc-nodes.sh

chmod 600 %{buildroot}/etc/openchami/configs/openchami.env
chmod 644 %{buildroot}/etc/openchami/configs/*

# 2) Put the 'install-openchami' source on the system so we can
# install it during 'post'. Also create a wrapper script to run
# 'install_openchami' from its shared virtual environment once
# this RPM finishes installing.
mkdir -p \
      "%{buildroot}/opt/install-openchami-%{version}/src" \
      "%{buildroot}/usr/bin"
cp -a install-openchami/* "%{buildroot}/opt/install-openchami-%{version}/src"
cp LICENSE "%{buildroot}/opt/install-openchami-%{version}/src/LICENSE"
cat <<EOF > %{buildroot}/usr/bin/install_openchami
#! /bin/bash
exec /opt/install-openchami-%{version}/venv/bin/python3 -m install_openchami "\$@"
EOF
chmod +x %{buildroot}/usr/bin/install_openchami

%files
%license LICENSE
%config(noreplace) /etc/openchami/configs/*
/etc/containers/systemd/*
/etc/systemd/system/openchami.target
/etc/systemd/system/openchami-cert-renewal.service
/etc/systemd/system/openchami-cert-renewal.timer
/etc/systemd/system/openchami-cert-trust.service
/usr/libexec/openchami/bootstrap_openchami.sh
/usr/libexec/openchami/ohpc-nodes.sh
/etc/profile.d/openchami.sh
/etc/openchami/pg-init/multi-psql-db.sh
/usr/bin/openchami-certificate-update
/usr/bin/install_openchami
/opt/install-openchami-%{version}/

%pre
if [ -f /etc/containers/systemd/coresmd.container ]; then
	echo 'WARNING: /etc/containers/systemd/coresmd.container as been replaced by /etc/containers/systemd/coresmd-coredhcp.container.'
	echo '         Migrate to coresmd-coredhcp to avoid any issues.'
fi

%post
# Create a shared python virtual environmnet in which to install
# 'install-openchami' and then use the pip from that virtual
# environment to install it. By doing it here instead of in the
# 'build' or 'install' stage we keep this RPM from becoming
# architecture dependent (due to inclusion of the python binary) and
# keep the size of the RPM down.
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_INSTALL_OPENCHAMI="%{version}"
export OPT_DIR="/opt/install-openchami-%{version}"
python3 -m venv "$OPT_DIR/venv"
"$OPT_DIR/venv/bin/pip" install --upgrade pip
"$OPT_DIR/venv/bin/pip" install "$OPT_DIR/src"

# reload systemd so new units are seen
systemctl daemon-reload
# bootstrap
systemctl stop firewalld
/usr/libexec/openchami/bootstrap_openchami.sh

%postun
# reload systemd on uninstall
systemctl daemon-reload

# Remove all the install-openchami stuff installed during 'post'
rm -rf /opt/install-openchami-%{version}
