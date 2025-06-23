#!/bin/bash

export server_private_key_file=${1:-server.privatekey}
export client_public_key_file=${2:-client.publickey}
export server_ip_range=${3:-192.168.69.1/24}
export server_port=${4:-51820}
export server_config=${5:-server.conf}
export server_peer_config=${5:-peer.conf}

echo "[Interface]" > $server_config
echo "PrivateKey = `cat $server_private_key_file`" >> $server_config
echo "Address = $server_ip_range" >> $server_config
echo "ListenPort = $server_port" >> $server_config
echo "PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE" >> $server_config
echo "PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE" >> $server_config

echo "" >> $server_config

echo "[Interface]" > $server_peer_config
echo "PrivateKey = `cat $server_private_key_file`" >> $server_peer_config
echo "ListenPort = $server_port" >> $server_peer_config

echo "[Peer]" >> $server_peer_config
echo "PublicKey = `cat $client_public_key_file`" >> $server_peer_config
echo "AllowedIPs = 0.0.0.0/0" >> $server_peer_config
echo "" >> $server_peer_config


echo "Wrote ${server_config}:"
cat $server_config

echo "Wrote ${server_peer_config}:"
cat $server_peer_config

