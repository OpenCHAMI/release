#!/bin/bash

source /etc/profile.d/openchami.sh

# Function to generate a random password
generate_random_password() {
  # Generate a random password with 16 characters
  local num_chars=${1:-16}
  openssl rand -base64 "${num_chars}" | openssl dgst | cut -d' ' -f2 | fold -w "${num_chars}" | head -n 1
}

# Function to create a secret if it doesn't exist
create_secret_if_not_exists() {
  local secret_name="$1"
  local secret_value="$2"
  
  # Check if the secret already exists
  if ! podman secret inspect "$secret_name" &>/dev/null; then
    echo "Creating secret: $secret_name"
    create_podman_secret --name "$secret_name" --secret "$secret_value"
  else
    echo "Secret $secret_name already exists, skipping creation."
  fi
}

# Function to define system_name and system_domain in the environment file
generate_environment_file() {
  local short_name=$(hostname -s)
  local dns_name=$(hostname -d)
  local system_fqdn=$(hostname)
  sed -i "s/^SYSTEM_NAME=.*/SYSTEM_NAME=${short_name}/" /etc/openchami/configs/openchami.env
  sed -i "s/^SYSTEM_DOMAIN=.*/SYSTEM_DOMAIN=${dns_name}/" /etc/openchami/configs/openchami.env
  sed -i "s/^SYSTEM_URL=.*/SYSTEM_URL=${system_fqdn}/" /etc/openchami/configs/openchami.env
  sed -i "s|^URLS_SELF_ISSUER=.*|URLS_SELF_ISSUER=https://${system_fqdn}|" /etc/openchami/configs/openchami.env
  sed -i "s|^URLS_SELF_PUBLIC=.*|URLS_SELF_PUBLIC=https://${system_fqdn}|" /etc/openchami/configs/openchami.env
  sed -i "s|^URLS_LOGIN=.*|URLS_LOGIN=https://${system_fqdn}/login|" /etc/openchami/configs/openchami.env
  sed -i "s|^URLS_CONSENT=.*|URLS_CONSENT=https://${system_fqdn}/consent|" /etc/openchami/configs/openchami.env
  sed -i "s|^URLS_LOGOUT=.*|URLS_LOGOUT=https://${system_fqdn}/logout|" /etc/openchami/configs/openchami.env
}

acme_correction() {
  local system_fqdn=$(hostname)
  sed -i "s|-d .* \\\\|-d ${system_fqdn} \\\\|" /etc/containers/systemd/acme-deploy.container
  sed -i "s/^ContainerName=.*/ContainerName=${system_fqdn}/" /etc/containers/systemd/acme-register.container
  sed -i "s/^HostName=.*/HostName=${system_fqdn}/" /etc/containers/systemd/acme-register.container
  sed -i "s|-d .* \\\\|-d ${system_fqdn} \\\\|" /etc/containers/systemd/acme-register.container
}

# Check and create secrets with random passwords if needed

# Postgres Password
postgres_password=$(generate_random_password)
create_secret_if_not_exists "postgres_password" "$postgres_password"

# BSS Postgres Password
bss_postgres_password=$(generate_random_password)
create_secret_if_not_exists "bss_postgres_password" "$bss_postgres_password"

# SMD Postgres Password
smd_postgres_password=$(generate_random_password)
create_secret_if_not_exists "smd_postgres_password" "$smd_postgres_password"

# Hydra Postgres Password
hydra_postgres_password=$(generate_random_password)
create_secret_if_not_exists "hydra_postgres_password" "$hydra_postgres_password"

# Hydra System Secret
hydra_system_secret=$(generate_random_password)
create_secret_if_not_exists "hydra_system_secret" "$hydra_system_secret"

# HYDRA_DSN
HYDRA_DSN="postgres://hydra-user:$(podman secret inspect hydra_postgres_password --showsecret | jq -r '.[0].SecretData')@postgres:5432/hydradb?sslmode=disable&max_conns=20&max_idle_conns=4"
create_secret_if_not_exists "hydra_dsn" "$HYDRA_DSN"

# POSTGRES_MULTIPLE_DATABASES
POSTGRES_MULTIPLE_DATABASES="hmsds:smd-user:$(podman secret inspect smd_postgres_password --showsecret | jq -r '.[0].SecretData'),bssdb:bss-user:$(podman secret inspect bss_postgres_password --showsecret | jq -r '.[0].SecretData'),hydradb:hydra-user:$(podman secret inspect hydra_postgres_password --showsecret | jq -r '.[0].SecretData')"
create_secret_if_not_exists "postgres_multiple_databases" "$POSTGRES_MULTIPLE_DATABASES"

# openchami.env Configuration
generate_environment_file

# Correct the ACME files
acme_correction