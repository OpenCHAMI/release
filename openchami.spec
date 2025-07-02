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
Requires(post): coreutils
Requires(post): openssl
Requires(post): hostname
Requires(post): sed

%description
The quadlets, systemd units, and config files for the Open Composable, Heterogeneous, Adaptable Management Infrastructure

%prep
%setup -q

%build
# nothing to build

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

%post
# reload systemd so new units are seen
systemctl daemon-reload
# bootstrap
systemctl stop firewalld
/usr/libexec/openchami/bootstrap_openchami.sh

%postun
# reload systemd on uninstall
systemctl daemon-reload
