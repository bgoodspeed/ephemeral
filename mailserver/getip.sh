#!/bin/bash

if command -v terraform >/dev/null 2>&1; then
  export TF=terraform
# If terraform is not found, check for tofu
elif command -v tofu >/dev/null 2>&1; then
  export TF=tofu
else
  echo "Neither terraform nor tofu are installed."
  exit 1
fi

$TF output -json | jq -r '.instance_ip_address.value' | tr -d '\n'
