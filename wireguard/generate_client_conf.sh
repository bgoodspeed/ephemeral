#!/bin/bash

export client_private_key_file=${2:-client.privatekey}
export server_public_key_file=${3:-server.publickey}
export server_address=`./getip.sh`
export server_port=${4:-51820}
export client_config=${5:-client.conf}


echo "[Interface]" > $client_config
echo "PrivateKey = `cat $client_private_key_file`" >> $client_config

echo "[Peer]" >> $client_config
echo "PublicKey = `cat $server_public_key_file`" >> $client_config
echo "Endpoint = ${server_address}:${server_port}" >> $client_config
echo "AllowedIPs = 0.0.0.0/0, ::/0 " >> $client_config
echo "" >> $client_config



