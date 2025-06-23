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



export ip1=`$TF output -json | jq -r '.instance_ip_addresses.value[0]'`
export ip2=`$TF output -json | jq -r '.instance_ip_addresses.value[1]'`
export ip3=`$TF output -json | jq -r '.instance_ip_addresses.value[2]'`

export local_port="${1:-12321}"


echo "$ip1 -> $ip2 -> $ip3"
ssh -J root@$ip1,root@$ip2 -D $local_port root@$ip3

