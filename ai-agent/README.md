# ai-agent

Provision a DigitalOcean Gradient AI agent from the command line and chat with it.


## Prerequisites

- Python 3.x
- A DigitalOcean account with Gradient AI access
- A DO API token (full access) from `cloud.digitalocean.com/account/api/tokens`

```bash
pip install -r requirements.txt
```

## Provision an agent

**1. Copy the example config:**

```bash
cp config.example.json config.json
```

**2. Edit `config.json`:**

```json
{
  "do_token": "dop_v1_your_token_here",
  "agent_name": "my-agent",
  "model_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "system_prompt": "You are a helpful assistant."
}
```

Get your model UUID:
```bash
doctl gradient models list
```

`region` and `description` are optional (defaults: `tor1`, empty).

**3. Provision:**

```bash
python provision.py create
```

This creates a DO project, workspace, and agent, then writes:
- `state.json` — resource IDs needed for cleanup
- `agents.json` — endpoint registry consumed by the CLI


## Usage 

1-shot:

```bash 
python agent.py ask -n 'chatbot name' "your 1 shot query"
```

chat:

```bash 
python agent.py chat -n 'chatbot name' 
```

### Sessions 

start/resume a chat in a given session name (will be created if missing):

```bash 
python agent.py chat --session 'session-name'
```

list sessions

```bash 
python agent.py sessions ls
```

delete a session

```bash 
python agent.py sessions rm session-name
```

## Tear down

```bash
python provision.py destroy
```

Deletes the agent, workspace, and project in the right order, then removes `state.json` and `agents.json`.

