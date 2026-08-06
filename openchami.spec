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
         %{buildroot}/usr/share/containers/systemd \
         %{buildroot}/usr/lib/systemd/system \
         %{buildroot}/usr/bin \
         %{buildroot}/usr/sbin \
         %{buildroot}/etc/profile.d \
         %{buildroot}/usr/libexec/openchami

cp -r systemd/configs/*                     %{buildroot}/etc/openchami/configs/
cp -r systemd/containers/*                  %{buildroot}/usr/share/containers/systemd/
cp -r systemd/volumes/*                     %{buildroot}/usr/share/containers/systemd/
cp -r systemd/networks/*                    %{buildroot}/usr/share/containers/systemd/
cp -r systemd/targets/*                     %{buildroot}/usr/lib/systemd/system/
cp -r systemd/system/*                      %{buildroot}/usr/lib/systemd/system/
cp scripts/bootstrap_openchami.sh           %{buildroot}/usr/libexec/openchami/
cp scripts/openchami-certificate-update     %{buildroot}/usr/bin/
cp scripts/openchami_profile.sh             %{buildroot}/etc/profile.d/openchami.sh
cp scripts/multi-psql-db.sh                 %{buildroot}/etc/openchami/pg-init/multi-psql-db.sh
cp scripts/ohpc-nodes.sh                    %{buildroot}/usr/libexec/openchami/
cp scripts/tokensmith_bootstrap_token       %{buildroot}/usr/sbin/

chmod +x %{buildroot}/usr/libexec/openchami/bootstrap_openchami.sh
chmod +x %{buildroot}/usr/libexec/openchami/ohpc-nodes.sh
chmod +x %{buildroot}/usr/libexec/openchami/bootstrap_openchami.sh
chmod +x %{buildroot}/usr/bin/openchami-certificate-update
chmod +x %{buildroot}/usr/libexec/openchami/ohpc-nodes.sh
chmod 0700 %{buildroot}/usr/sbin/tokensmith_bootstrap_token

chmod 600 %{buildroot}/etc/openchami/configs/openchami.env
chmod 644 %{buildroot}/etc/openchami/configs/*

%files
%license LICENSE
%config(noreplace) /etc/openchami/configs/*
/usr/share/containers/systemd/*
/usr/lib/systemd/system/openchami.target
/usr/lib/systemd/system/openchami-cert-renewal.service
/usr/lib/systemd/system/openchami-cert-renewal.timer
/usr/lib/systemd/system/openchami-cert-trust.service
/usr/libexec/openchami/bootstrap_openchami.sh
/usr/libexec/openchami/ohpc-nodes.sh
/etc/profile.d/openchami.sh
/etc/openchami/pg-init/multi-psql-db.sh
/usr/bin/openchami-certificate-update
/usr/sbin/tokensmith_bootstrap_token

%pre
# NOTES:
# 1. `coresmd` refers to the legacy implementation before the CoreDNS split.
# 2. Releases now install Quadlets under the standard system-managed path,
#    `/usr/share/containers/systemd`, instead of the admin-managed
#    `/etc/containers/systemd`. This aligns with standard systemd override
#    semantics and keeps local modifications separate from packaged files.
# 3. This warning and these comments will remain until support for the legacy,
#    non-fabrica services is dropped.
if [ -f /etc/containers/systemd/coresmd.container ]; then
	echo 'WARNING: /etc/containers/systemd/coresmd.container as been replaced by /usr/share/containers/systemd/coresmd-coredhcp.container.'
	echo '         Migrate to coresmd-coredhcp to avoid any issues.'
fi

%post
# reload systemd so new units are seen
systemctl daemon-reload
# bootstrap
systemctl stop firewalld
/usr/libexec/openchami/bootstrap_openchami.sh

%postun
# reload systemd on uninstall
systemctl daemon-reload
