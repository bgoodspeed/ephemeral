#!/bin/bash

umask 077
wg genkey | tee server.privatekey | wg pubkey > server.publickey
wg genkey | tee client.privatekey | wg pubkey > client.publickey

echo "Wrote server.privatekey, server.publickey"
echo "Wrote client.privatekey, client.publickey"

