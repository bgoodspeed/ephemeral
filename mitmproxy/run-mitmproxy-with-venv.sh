#!/bin/bash 

source /mitm-venv/bin/activate 
#nohup stdbuf -oL mitmweb --mode regular --listen-host 127.0.0.1 --listen-port 8080 --web-host 127.0.0.1 --web-port 8081 --showhost > /var/log/mitmweb.log 2>&1 &
nohup python -u /mitm-venv/bin/mitmweb --mode regular --listen-port 8080 --web-port 8081 --showhost > /mitm.log 2>&1 &

for i in {1..10}; do
    TOKEN=$(grep -o 'token=[a-zA-Z0-9]*' /mitm.log | head -n1 | cut -d= -f2)
    if [ -n "$TOKEN" ]; then
        echo "$TOKEN" > /mitm.token
        break
    fi
    sleep 1
done

# Optional: fail explicitly if still no token found
if [ ! -s /mitm.token ]; then
    echo "Error: mitmweb token not found after 10 seconds"
    exit 1
fi



