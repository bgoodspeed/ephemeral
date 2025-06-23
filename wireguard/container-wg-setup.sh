#!/bin/sh
set -e

WG_INTERFACE="wg0"
WG_CONFIG="/etc/wireguard/client.conf"
WG_LOCAL_IP="192.168.69.2/24"

# Extract the peer endpoint IP from the config (first Peer block)

WG_SERVER_IP=$(grep '^Endpoint' "$WG_CONFIG" | cut -d '=' -f2 | cut -d ':' -f1 | xargs)
echo "[+] WireGuard server IP: $WG_SERVER_IP"

# Bring up loopback
ip link set lo up

# Clean up existing wg0 if any
ip link del "$WG_INTERFACE" 2>/dev/null || true

# Create and configure wg0
ip link add "$WG_INTERFACE" type wireguard
ip addr add "$WG_LOCAL_IP" dev "$WG_INTERFACE"
wg setconf "$WG_INTERFACE" "$WG_CONFIG"
ip link set "$WG_INTERFACE" up

# Determine current default gateway (usually for eth0)
GW=$(ip route | awk '/default/ {print $3}')
DEV=$(ip route | awk '/default/ {print $5}')
echo "[+] Using gateway $GW via $DEV"

# Ensure we can reach the WireGuard server
ip route add "$WG_SERVER_IP" via "$GW" dev "$DEV"

# Now safely change default route to go through wg0
ip route replace default dev "$WG_INTERFACE"

# Set DNS
echo "nameserver 1.1.1.1" > /etc/resolv.conf

# Wait for handshake
echo "[*] Waiting for WireGuard handshake..."
for i in $(seq 1 5); do
    HANDSHAKE=$(wg show "$WG_INTERFACE" latest-handshakes | awk '{print $2}')
    if [ "$HANDSHAKE" != "0" ]; then
        echo "[+] Handshake established."
        break
    fi
    sleep 1
done

# Show IP info
echo "[+] Tunnel IP: $(ip -4 addr show "$WG_INTERFACE" | awk '/inet / {print $2}')"
echo "[+] External IP (via tunnel):"
curl -s https://ipinfo.io

# Drop to shell
exec bash
