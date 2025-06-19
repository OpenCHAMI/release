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
         %{buildroot}/usr/local/bin \
         %{buildroot}/etc/profile.d

cp -r systemd/configs/*           %{buildroot}/etc/openchami/configs/
cp -r systemd/containers/*        %{buildroot}/etc/containers/systemd/
cp -r systemd/volumes/*           %{buildroot}/etc/containers/systemd/
cp -r systemd/networks/*          %{buildroot}/etc/containers/systemd/
cp -r systemd/targets/*           %{buildroot}/etc/systemd/system/
cp -r systemd/system/*            %{buildroot}/etc/systemd/system/
cp scripts/bootstrap_openchami.sh %{buildroot}/usr/local/bin/
cp scripts/openchami_profile.sh   %{buildroot}/etc/profile.d/openchami.sh
cp scripts/multi-psql-db.sh       %{buildroot}/etc/openchami/pg-init/multi-psql-db.sh

chmod +x %{buildroot}/usr/local/bin/bootstrap_openchami.sh
chmod 600 %{buildroot}/etc/openchami/configs/openchami.env
chmod 644 %{buildroot}/etc/openchami/configs/*




%files
%license LICENSE
/etc/openchami/configs/*
/etc/containers/systemd/*
/etc/systemd/system/openchami.target
/etc/systemd/system/openchami-cert-renewal.service
/etc/systemd/system/openchami-cert-renewal.timer
/usr/local/bin/bootstrap_openchami.sh
/etc/profile.d/openchami.sh
/etc/openchami/pg-init/multi-psql-db.sh

%post
# reload systemd so new units are seen
systemctl daemon-reload
# bootstrap
systemctl stop firewalld
/usr/local/bin/bootstrap_openchami.sh

%postun
# reload systemd on uninstall
systemctl daemon-reload
