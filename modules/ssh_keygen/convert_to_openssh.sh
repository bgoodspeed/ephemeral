#!/bin/bash

PEM_FILE="id_rsa.pem"
OPENSSH_FILE="id_rsa"

if [ ! -f "$PEM_FILE" ]; then
  echo "Error: $PEM_FILE not found"
  exit 1
fi

# Convert PEM (PKCS#1) to OpenSSH format
openssl rsa -in "$PEM_FILE" -out "$OPENSSH_FILE" -outform PEM

# Set correct permissions
chmod 600 "$OPENSSH_FILE"

echo "Converted $PEM_FILE to OpenSSH format as $OPENSSH_FILE"
