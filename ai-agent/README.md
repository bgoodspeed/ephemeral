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
- `pricing.json` — per-token rates fetched from the DO models API (used for cost display)


## Usage

1-shot:

```bash
python agent.py ask "your question"
python agent.py ask -n my-agent "your question"   # specify agent if you have more than one
```

After each response, token usage and estimated cost are printed to stderr:

```
[tokens: 141 in / 52 out | $0.000426]
```

For scripting, `--json` wraps the response in a JSON envelope that includes the `usage` field:

```bash
python agent.py ask --json "your question"
# {"agent": "my-agent", "content": "...", "usage": {"prompt_tokens": 141, "completion_tokens": 52, "total_tokens": 193}}
```

Chat (interactive REPL):

```bash
python agent.py chat
python agent.py chat -n my-agent
```

### Sessions

Named sessions persist conversation history across invocations.

Start or resume a session:

```bash
python agent.py chat --session my-session
```

List all sessions:

```bash
python agent.py sessions list
```

Show token usage and cost breakdown for a session:

```bash
python agent.py sessions usage my-session
```

```
TURN        IN       OUT          COST
   1       141         2     $0.000251
   2       148        26     $0.000348
 ---  --------  --------  ------------
 TOT       289        28     $0.000599
```

Delete a session:

```bash
python agent.py sessions rm my-session
```

Session files are stored at `~/.local/share/doagent/sessions/` (mode 0600).


## Pricing

`pricing.json` is written automatically by `provision.py create`. Per-token rates come from the DO models API and are keyed by `model_uuid`, so multiple agents backed by different models each get their own entry. If `pricing.json` is missing or a model has no pricing data, token counts are still shown but cost is omitted.


## Tear down

```bash
python provision.py destroy
```

Deletes the agent, workspace, and project in the right order, then removes `state.json` and `agents.json`.
