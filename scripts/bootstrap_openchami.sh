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

# Check and create secrets with random passwords if needed

# Postgres Password
postgres_password=$(generate_random_password)
create_secret_if_not_exists "postgres_password" "$postgres_password"

# SMD Postgres Password
smd_postgres_password=$(generate_random_password)
create_secret_if_not_exists "smd_postgres_password" "$smd_postgres_password"


# POSTGRES_MULTIPLE_DATABASES
POSTGRES_MULTIPLE_DATABASES="hmsds:smd-user:$(podman secret inspect smd_postgres_password --showsecret | jq -r '.[0].SecretData')"
create_secret_if_not_exists "postgres_multiple_databases" "$POSTGRES_MULTIPLE_DATABASES"
