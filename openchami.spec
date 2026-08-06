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
# Any pre-existing OpenCHAMI quadlets in /etc/containers/systemd could
# unintentionally override the installed quadlets. Exit if any remaining are
# found and link to migration guide.
if [ -f /etc/containers/systemd/acme-deploy.container ] \
     || [ -f /etc/containers/systemd/acme-register.container ] \
     || [ -f /etc/containers/systemd/boot-service.container ] \
     || [ -f /etc/containers/systemd/bss-init.container ] \
     || [ -f /etc/containers/systemd/bss.container ] \
     || [ -f /etc/containers/systemd/cloud-init-server.container ] \
     || [ -f /etc/containers/systemd/coresmd.container ] \
     || [ -f /etc/containers/systemd/coresmd-coredhcp.container ] \
     || [ -f /etc/containers/systemd/coresmd-coredns.container ] \
     || [ -f /etc/containers/systemd/haproxy.container ] \
     || [ -f /etc/containers/systemd/metadata-service.container ] \
     || [ -f /etc/containers/systemd/hydra-gen-jwks.container ] \
     || [ -f /etc/containers/systemd/hydra-migrate.container ] \
     || [ -f /etc/containers/systemd/hydra.container ] \
     || [ -f /etc/containers/systemd/opaal-idp.container ] \
     || [ -f /etc/containers/systemd/opaal.container ] \
     || [ -f /etc/containers/systemd/postgres.container ] \
     || [ -f /etc/containers/systemd/smd-init.container ] \
     || [ -f /etc/containers/systemd/smd.container ] \
     || [ -f /etc/containers/systemd/step-ca.container ] \
     || [ -f /etc/containers/systemd/tokensmith.container ] \
     || [ -f /etc/containers/systemd/openchami-cert-internal.network ] \
     || [ -f /etc/containers/systemd/openchami-external.network ] \
     || [ -f /etc/containers/systemd/openchami-internal.network ] \
     || [ -f /etc/containers/systemd/openchami-jwt-internal.network ] \
     || [ -f /etc/containers/systemd/acme-certs.volume ] \
     || [ -f /etc/containers/systemd/boot-service-data.volume ] \
     || [ -f /etc/containers/systemd/cloud-init-data.volume ] \
     || [ -f /etc/containers/systemd/haproxy-certs.volume ] \
     || [ -f /etc/containers/systemd/metadata-service-data.volume ] \
     || [ -f /etc/containers/systemd/postgres-data.volume ] \
     || [ -f /etc/containers/systemd/step-ca-db.volume ] \
     || [ -f /etc/containers/systemd/step-ca-home.volume ] \
     || [ -f /etc/containers/systemd/step-root-ca.volume ] \
     || [ -f /etc/containers/systemd/tokensmith.volume ] \
; then
	echo 'ERROR: Old OpenCHAMI quadlets still exist in /etc/containers/systemd.'
        echo '       These could unintentionally overwrite the installed quadlets.'
	echo '       Uninstall openchami to get rid of them before upgrading.'
        echo
        echo '       See the following for a guide on migrating to this release:'
        echo
        echo '       https://openchami.org/docs/guides/fabrica-migration'
	exit 1
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
