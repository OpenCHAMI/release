#!/bin/bash

source /etc/profile.d/openchami.sh

# Function to generate a random password
generate_random_password() {
  # Generate a random password with 16 characters
  openssl rand -base64 16
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

# Pull OpenCHAMI images
pull_openchami_images

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
