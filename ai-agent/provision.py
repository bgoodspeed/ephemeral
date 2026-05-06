#!/usr/bin/env python3
"""
provision.py — create and destroy DO Gradient AI agent infrastructure.

Usage:
    python provision.py create
    python provision.py destroy
"""

import argparse
import datetime
import json
import os
import secrets
import socket
import subprocess
import sys
import time

import requests

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
AGENTS_FILE = "agents.json"
PRICING_FILE = "pricing.json"
SSH_KEY_FILE  = "proxy_ssh_key"
BASE = "https://api.digitalocean.com/v2"
DROPLET_SIZE  = "s-1vcpu-512mb-10gb"
DROPLET_IMAGE = "ubuntu-24-04-x64"
PROXY_SCRIPT = """\
import os, requests
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
UPSTREAM_URL = os.environ["UPSTREAM_URL"]
UPSTREAM_KEY = os.environ["UPSTREAM_KEY"]
PROXY_KEY    = os.environ["PROXY_KEY"]


@app.route("/api/v1/chat/completions", methods=["POST"])
def proxy():
    if request.headers.get("Authorization") != f"Bearer {PROXY_KEY}":
        return {"error": "unauthorized"}, 401
    r = requests.post(
        f"{UPSTREAM_URL}/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {UPSTREAM_KEY}",
            "Content-Type": "application/json",
        },
        json=request.get_json(),
        stream=True,
        timeout=120,
    )
    return Response(
        stream_with_context(r.iter_content(chunk_size=None)),
        content_type=r.headers.get("Content-Type", "text/event-stream"),
        status=r.status_code,
    )


app.run(host="0.0.0.0", port=443, ssl_context=("/opt/proxy.crt", "/opt/proxy.key"))
"""


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"error: {CONFIG_FILE} not found — copy config.example.json and fill in your values")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    os.chmod(STATE_FILE, 0o600)


class Client:
    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def get(self, path):
        r = self.s.get(f"{BASE}/{path}")
        r.raise_for_status()
        return r.json()

    def post(self, path, body):
        r = self.s.post(f"{BASE}/{path}", json=body)
        if not r.ok:
            print(f"  error {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()

    def delete(self, path):
        r = self.s.delete(f"{BASE}/{path}")
        if r.status_code == 404:
            return None  # already gone, that's fine
        r.raise_for_status()
        return r.json() if r.content else None


def fetch_model_info(do, model_uuid):
    """Return the model dict for the given UUID, or None."""
    try:
        data = do.get("gen-ai/models")
        for m in data.get("models", []):
            if m.get("uuid") == model_uuid:
                return m
    except Exception as e:
        print(f"  warning: could not fetch model info: {e}", file=sys.stderr)
    return None


def update_pricing_file(model_uuid, model_name, input_per_token, output_per_token):
    existing = {}
    if os.path.exists(PRICING_FILE):
        with open(PRICING_FILE) as f:
            existing = json.load(f)
    existing.setdefault("version", 1)
    existing.setdefault("models", {})
    existing["models"][model_uuid] = {
        "name": model_name,
        "input_per_token": input_per_token,
        "output_per_token": output_per_token,
    }
    with open(PRICING_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def create_proxy(do, state, config):
    proxy_key = secrets.token_urlsafe(32)

    # Generate a fresh ed25519 key pair for SSH access to the droplet
    for f in [SSH_KEY_FILE, SSH_KEY_FILE + ".pub"]:
        if os.path.exists(f):
            os.remove(f)
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-f", SSH_KEY_FILE, "-N", "",
         "-C", f"{state['agent_name']}-proxy"],
        check=True, capture_output=True,
    )
    os.chmod(SSH_KEY_FILE, 0o600)
    with open(SSH_KEY_FILE + ".pub") as f:
        public_key = f.read().strip()

    print("uploading SSH key...")
    key_resp = do.post("account/keys", {
        "name": f"{state['agent_name']}-proxy-key",
        "public_key": public_key,
    })
    ssh_key_id = key_resp["ssh_key"]["id"]
    state["proxy_ssh_key_id"] = ssh_key_id
    save_state(state)
    print(f"  id: {ssh_key_id}")

    svc = "\n".join([
        "[Unit]",
        "Description=Agent Proxy",
        "After=network.target",
        "[Service]",
        "ExecStart=/usr/bin/python3 /opt/proxy.py",
        f'Environment="UPSTREAM_URL={state["agent_url"]}"',
        f'Environment="UPSTREAM_KEY={state["agent_api_key"]}"',
        f'Environment="PROXY_KEY={proxy_key}"',
        "Restart=always",
        "[Install]",
        "WantedBy=multi-user.target",
    ])

    user_data = "\n".join([
        "#!/bin/bash",
        "apt-get update -q && apt-get install -y -q python3-flask python3-requests openssl",
        "openssl req -x509 -newkey rsa:4096 -keyout /opt/proxy.key \\",
        "  -out /opt/proxy.crt -days 3650 -nodes -subj '/CN=proxy' 2>/dev/null",
        "cat > /opt/proxy.py << 'PYEOF'",
        PROXY_SCRIPT,
        "PYEOF",
        "cat > /etc/systemd/system/proxy.service << 'SVCEOF'",
        svc,
        "SVCEOF",
        "systemctl daemon-reload && systemctl enable proxy && systemctl start proxy",
    ])

    print("creating proxy droplet...")
    resp = do.post("droplets", {
        "name": f"{state['agent_name']}-proxy",
        "region": config.get("region", "tor1"),
        "size": DROPLET_SIZE,
        "image": DROPLET_IMAGE,
        "user_data": user_data,
        "ssh_keys": [ssh_key_id],
    })
    droplet_id = resp["droplet"]["id"]
    state["droplet_id"] = droplet_id
    save_state(state)
    print(f"  id: {droplet_id}")

    proxy_ip = None
    print("  waiting for IP", end="", flush=True)
    for _ in range(30):
        time.sleep(5)
        print(".", end="", flush=True)
        d = do.get(f"droplets/{droplet_id}")["droplet"]
        for net in d.get("networks", {}).get("v4", []):
            if net["type"] == "public":
                proxy_ip = net["ip_address"]
                break
        if proxy_ip:
            break
    if not proxy_ip:
        raise RuntimeError("timed out waiting for droplet IP")
    state["proxy_ip"] = proxy_ip
    state["proxy_api_key"] = proxy_key
    save_state(state)
    print(f" {proxy_ip}")

    print("  waiting for proxy service", end="", flush=True)
    for _ in range(60):
        time.sleep(5)
        print(".", end="", flush=True)
        try:
            s = socket.create_connection((proxy_ip, 443), timeout=3)
            s.close()
            break
        except OSError:
            pass
    else:
        print(" (timed out — proxy may still be starting)")
        return proxy_ip, proxy_key
    print(" ready")
    return proxy_ip, proxy_key


def create(config, use_proxy=False):
    if os.path.exists(STATE_FILE):
        print(f"error: {STATE_FILE} already exists — run 'destroy' first")
        sys.exit(1)

    if "system_prompt" not in config:
        print("error: 'system_prompt' not found in config.json")
        sys.exit(1)
    instruction = config["system_prompt"].strip()

    do = Client(config["do_token"])
    name = config["agent_name"]

    # Write state BEFORE each API call so a crashed run leaves enough state for destroy
    state = {"agent_name": name, "created_at": datetime.datetime.now(datetime.UTC).isoformat()}
    save_state(state)

    # 1. Project
    print(f"creating project '{name}'...")
    project = do.post("projects", {
        "name": name,
        "description": config.get("description", ""),
        "purpose": "AI / ML",
        "environment": "Production",
    })["project"]
    state["project_id"] = project["id"]
    save_state(state)
    print(f"  project {project['id']}")

    # 2. Workspace
    print(f"creating workspace '{name}'...")
    state["workspace_uuid"] = None
    save_state(state)
    workspace = do.post("gen-ai/workspaces", {"name": name})["workspace"]
    state["workspace_uuid"] = workspace["uuid"]
    save_state(state)
    print(f"  workspace {workspace['uuid']}")

    # 3. Agent
    print(f"creating agent '{name}'...")
    state["agent_uuid"] = None
    save_state(state)
    agent = do.post("gen-ai/agents", {
        "name": name,
        "instruction": instruction,
        "model_uuid": config["model_uuid"],
        "project_id": state["project_id"],
        "workspace_uuid": state["workspace_uuid"],
        "region": config.get("region", "tor1"),
        "description": config.get("description", ""),
    })["agent"]
    state["agent_uuid"] = agent["uuid"]
    save_state(state)
    print(f"  agent {agent['uuid']}")

    # Poll until deployment URL is assigned
    print("  waiting for deployment url", end="", flush=True)
    for _ in range(30):
        time.sleep(5)
        print(".", end="", flush=True)
        details = do.get(f"gen-ai/agents/{state['agent_uuid']}")["agent"]
        url = details.get("deployment", {}).get("url", "")
        if url:
            state["agent_url"] = url
            save_state(state)
            print(f" {url}")
            break
    else:
        state["agent_url"] = ""
        save_state(state)
        print(" timed out — check DO console for url")

    # 4. Agent API key — create an endpoint access key
    print("creating agent API key...")
    key_resp = do.post(f"gen-ai/agents/{state['agent_uuid']}/api_keys", {"name": f"{name}-key"})
    api_key = key_resp["api_key_info"]["secret_key"]
    state["agent_api_key"] = api_key
    state["agent_api_key_uuid"] = key_resp["api_key_info"]["uuid"]
    save_state(state)
    print(f"  api key {'*' * 8}{api_key[-6:]}")

    # 5. pricing.json — fetch per-token rates for this model
    print("fetching model pricing...")
    model_uuid = config["model_uuid"]
    model_info = fetch_model_info(do, model_uuid)
    if model_info:
        pricing = model_info.get("pricing", {})
        # DO names this field "per_million" but values are per-token (confirmed against published rates)
        inp_price = pricing.get("input_price_per_million")
        out_price = pricing.get("output_price_per_million")
        model_name = model_info.get("name", model_uuid)
        if inp_price is not None:
            update_pricing_file(model_uuid, model_name, inp_price, out_price)
            print(f"  {model_name}: ${inp_price}/tok in, ${out_price}/tok out → saved to {PRICING_FILE}")
        else:
            print(f"  {model_name}: no pricing data in API response")
    else:
        print(f"  no model info available for {model_uuid}")

    # 6. agents.json registry
    registry = {
        "version": 1,
        "agents": {
            name: {
                "id": state["agent_uuid"],
                "url": state["agent_url"],
                "model_uuid": config["model_uuid"],
                "region": config.get("region", "tor1"),
                "api_key": state["agent_api_key"],
            }
        }
    }
    with open(AGENTS_FILE, "w") as f:
        json.dump(registry, f, indent=2)
    os.chmod(AGENTS_FILE, 0o600)

    if use_proxy:
        proxy_ip, proxy_key = create_proxy(do, state, config)
        with open(AGENTS_FILE) as f:
            registry = json.load(f)
        registry["agents"][name]["url"]        = f"https://{proxy_ip}"
        registry["agents"][name]["api_key"]    = proxy_key
        registry["agents"][name]["tls_verify"] = False
        with open(AGENTS_FILE, "w") as f:
            json.dump(registry, f, indent=2)
        os.chmod(AGENTS_FILE, 0o600)

    print(f"\ndone.")
    print(f"  agent url: {state['agent_url']}")
    if use_proxy:
        print(f"  proxy:     https://{state['proxy_ip']}")
        print(f"  ssh:       ssh -i {SSH_KEY_FILE} root@{state['proxy_ip']}")
    print(f"  state:     {STATE_FILE}")
    print(f"  registry:  {AGENTS_FILE}")


def destroy():
    state = load_state()
    if not state:
        print(f"no {STATE_FILE} found — nothing to destroy")
        sys.exit(0)

    config = load_config()
    do = Client(config["do_token"])

    if state.get("agent_uuid"):
        print(f"deleting agent {state['agent_uuid']}...")
        do.delete(f"gen-ai/agents/{state['agent_uuid']}")
        print("  done")

    if state.get("workspace_uuid"):
        print(f"deleting workspace {state['workspace_uuid']}...")
        do.delete(f"gen-ai/workspaces/{state['workspace_uuid']}")
        print("  done")

    if state.get("droplet_id"):
        print(f"deleting proxy droplet {state['droplet_id']}...")
        try:
            do.delete(f"droplets/{state['droplet_id']}")
            print("  done")
        except requests.HTTPError as e:
            print(f"  warning: {e} — delete the droplet manually in the DO console")

    if state.get("proxy_ssh_key_id"):
        print(f"deleting proxy SSH key {state['proxy_ssh_key_id']}...")
        try:
            do.delete(f"account/keys/{state['proxy_ssh_key_id']}")
            print("  done")
        except requests.HTTPError as e:
            print(f"  warning: {e}")

    if "project_id" in state:
        print(f"deleting project {state['project_id']}...")
        try:
            do.delete(f"projects/{state['project_id']}")
            print("  done")
        except requests.HTTPError as e:
            print(f"  warning: {e} — delete the project manually in the DO console")

    for path in [STATE_FILE, AGENTS_FILE, PRICING_FILE, SSH_KEY_FILE, SSH_KEY_FILE + ".pub"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"removed {path}")

    print("\ndone.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        prog="provision.py",
        description="create and destroy DO Gradient AI agent infrastructure",
    )
    ap.add_argument("command", choices=["create", "destroy"])
    ap.add_argument("--proxy", action="store_true",
                    help="also provision a DigitalOcean droplet as a TLS reverse proxy")
    args = ap.parse_args()

    if args.command == "create":
        create(load_config(), use_proxy=args.proxy)
    else:
        destroy()
