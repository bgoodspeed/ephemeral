#!/usr/bin/env python3
"""
provision.py — create and destroy DO Gradient AI agent infrastructure.

Usage:
    python provision.py create
    python provision.py destroy
"""

import json
import os
import sys
import time
import datetime
import requests

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
AGENTS_FILE = "agents.json"
PRICING_FILE = "pricing.json"
BASE = "https://api.digitalocean.com/v2"


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


def create(config):
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

    print(f"\ndone.")
    print(f"  agent url: {state['agent_url']}")
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

    if "project_id" in state:
        print(f"deleting project {state['project_id']}...")
        try:
            do.delete(f"projects/{state['project_id']}")
            print("  done")
        except requests.HTTPError as e:
            print(f"  warning: {e} — delete the project manually in the DO console")

    for path in [STATE_FILE, AGENTS_FILE]:
        if os.path.exists(path):
            os.remove(path)
            print(f"removed {path}")

    print("\ndone.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("create", "destroy"):
        print("usage: python provision.py <create|destroy>")
        sys.exit(1)

    cfg = load_config()

    if sys.argv[1] == "create":
        create(cfg)
    else:
        destroy()
