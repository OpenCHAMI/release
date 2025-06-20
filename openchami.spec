Name:           openchami
Version:        %{version}
Release:        %{release}%{?dist}
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
This package installs all the necessary files for OpenChami, mostly the quadlet/systemd-unit files.

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


%changelog
* Mon Jun 16 2025 Travis Powell <trpowell@lanl.gov> - 0.0.27-1
- Introduced Dynamic environment file for hostnames in configuration files
* Tue May 20 2025 Your Name <you@example.com> - %{version}-%{release}
- Two-step Skopeo: sync→dir + copy→docker-archive to produce one tag-preserving, deduped tarball  
- Added Requires: skopeo  
- Retained versioned filename, daemon-reload, cleanup  
* Thu Jan 25 2024 Alex Lovell-Troy <alovelltroy@lanl.gov> - 0.9.0-1
- Initial package
