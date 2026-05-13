# TokioAI

**Your AI actually does things.** It doesn't just talk — it executes commands, SSHs into your servers, edits your code, scans your network, deploys your infrastructure, and fixes your problems. All from a single prompt.

TokioAI connects to Claude, GPT, Gemini, Ollama, or any model you want — and gives it **real tools** to interact with your systems. Not wrappers. Not plugins. Native tool calling through each provider's API, the same mechanism the models were trained to use.

```
you > "find why nginx is returning 502 and fix it"

TokioAI:
  [execute_local] systemctl status nginx
  [execute_local] journalctl -u nginx --since "10 min ago"
  [execute_local] cat /etc/nginx/sites-enabled/default
  [execute_local] curl -s http://localhost:8080/health
  [edit_file] /etc/nginx/sites-enabled/default — fixed proxy_pass upstream
  [execute_local] nginx -t && systemctl reload nginx
  [execute_local] curl -I http://localhost

  Fixed. The upstream was pointing to port 3000 but your app moved to 8080.
  Updated the proxy_pass directive and reloaded nginx. Returning 200 now.
```

No copy-pasting commands. No "here's what you should do". It **does it**.

---

## What it actually does

TokioAI gives AI models 15 tools to interact with your world:

| Tool | What it does |
|------|-------------|
| `execute_local` | Run any shell command on your machine |
| `execute_raspi` | SSH into a Raspberry Pi |
| `execute_gcp` | SSH into a GCP VM |
| `execute_router` | SSH into your router |
| `ssh_connect` | SSH into **any** server (IP + user + password) |
| `read_file` | Read files — local or remote (`raspi:/path`, `gcp:/path`) |
| `write_file` | Write files — local or remote |
| `edit_file` | Surgical find-and-replace in files |
| `search_files` | grep across your codebase |
| `diagnose` | System health check (CPU, RAM, disk, network, Docker) |
| `memory` | Read/write persistent memory that survives across sessions |
| `tasks` | Track tasks with status (pending, in_progress, done, blocked) |
| `pidog` | Control a PiDog robot via HTTP API |
| `picar` | Control a PiCar-X robot via HTTP API |
| `home_assistant` | Control smart home via Home Assistant (lights, Alexa, sensors, switches) |

These aren't gimmicks. They use **native function calling** — the same tool-use protocol built into Claude, GPT, and Gemini's APIs. The model decides what tool to call, with what arguments, inspects the result, and decides the next step. Multiple rounds. No regex parsing. No prompt hacking.

### Real examples

**Cybersecurity:**
```
"scan 192.168.1.0/24 for open ports and check for known CVEs"
"audit the firewall rules on the router and harden them"
"analyze this pcap file for suspicious traffic"
```

**DevOps:**
```
"deploy the new version to production — build, test, push, restart"
"the database is slow, find the bottleneck and fix it"
"set up a Docker Compose stack with postgres, redis, and nginx"
```

**Engineering:**
```
"refactor this function to handle concurrent requests"
"write tests for the auth module and run them"
"find all SQL injection vulnerabilities in the codebase"
```

**Infrastructure:**
```
"SSH into the prod server and check why disk is at 95%"
"configure the Raspberry Pi as a network monitor"
"set up Tailscale between all my machines"
```

**Robotics:**
```
"make the PiDog bark and do a pushup"
"move PiCar forward 3 steps and take a photo"
"check battery and sensor status on both robots"
```

TokioAI doesn't care what you throw at it. If it can be done from a terminal, it can do it.

---

## How tool calling works

Traditional AI wrappers paste your question into a prompt and pray. TokioAI uses **native tool calling** — the structured protocol each AI provider exposes for function execution:

```
1. You say: "check disk space and clean up if needed"

2. TokioAI sends your message + tool definitions to the model

3. The model responds with a structured tool call:
   {"name": "execute_local", "input": {"command": "df -h"}}

4. TokioAI executes it, feeds the output back to the model

5. The model analyzes the output, decides next action:
   {"name": "execute_local", "input": {"command": "du -sh /var/log/* | sort -rh | head -20"}}

6. Repeat until the task is done (up to 25 rounds)
```

This is not string parsing. Not regex extraction. The model returns structured JSON that maps directly to function calls. Same mechanism used by ChatGPT plugins, Claude's computer use, and Gemini's function calling — except here the tools are **your actual infrastructure**.

---

## Works with any model

Switch providers and models whenever you want. Same tools, same interface, different brain:

| Provider | Models | What you need |
|----------|--------|---------------|
| **Claude** (Anthropic API) | Opus, Sonnet, Haiku | `ANTHROPIC_API_KEY` |
| **Claude** (Vertex AI) | Same models, Google billing | `VERTEX_PROJECT` + credentials |
| **OpenAI** | GPT-4o, GPT-5, o3 | `OPENAI_API_KEY` |
| **Gemini** (Google AI) | Flash, Pro | `GEMINI_API_KEY` (free tier available) |
| **OpenRouter** | 200+ models from every provider | `OPENROUTER_API_KEY` |
| **Ollama** | Llama, Mistral, DeepSeek, Qwen — local, free | Just run Ollama |

Switch at runtime:
```
model opus       <- Claude Opus 4.6
model flash      <- Gemini Flash (fast + cheap)
model gpt4o      <- GPT-4o
model llama      <- Local Llama 3.1 via Ollama
model deepseek   <- DeepSeek Coder
```

---

## Install

```bash
git clone https://github.com/TokioAI/tokioai.git
cd tokioai

# Install with your preferred provider
pip install -e ".[claude]"     # Claude (Anthropic API)
pip install -e ".[vertex]"     # Claude (Vertex AI)
pip install -e ".[openai]"     # OpenAI / OpenRouter
pip install -e ".[gemini]"     # Google Gemini
pip install -e ".[all]"        # Everything

# Configure
tokioai --setup

# Go
tokioai
```

That's it. The setup wizard asks for your API key and writes the config. Takes 30 seconds.

### Quick config for each provider

**Claude (fastest setup):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
tokioai
```

**Gemini (free):**
```bash
pip install -e ".[gemini]"
export GEMINI_API_KEY=...  # Get one free at aistudio.google.com
tokioai
```

**Ollama (local, free, private):**
```bash
pip install -e ".[openai]"
ollama pull llama3.1:8b
export OLLAMA_HOST=http://localhost:11434
tokioai
```

---

## Usage

```bash
# Interactive — open a session and keep working
tokioai

# One-shot — run a single task
tokioai "find all TODO comments in this project"

# Specific model
tokioai --model sonnet "explain this Dockerfile"

# Persistent mode — keeps working autonomously until you say stop
tokioai --persistent

# Unlimited tool rounds (default: 25)
tokioai --unlimited
```

### Commands inside a session

| Command | Short | What it does |
|---------|-------|-------------|
| `model <name>` | `m` | Switch model |
| `models` | | List all available models |
| `stats` | `s` | Token usage and cost |
| `compact` | `c` | Compress context to free space |
| `reset` | `r` | Fresh conversation |
| `config` | | Show current config |
| `help` | `?` | Full help |

---

## Persistent memory

TokioAI remembers things across sessions. The AI can store facts, infrastructure details, preferences, and task context in a local memory file (`~/.tokioai/memory.md`) that gets loaded into every conversation.

```
you > "remember that the prod database is on port 5433, not the default"

TokioAI:
  [memory] append: "Prod database runs on port 5433 (non-standard)"

  Got it. I'll remember that for future sessions.
```

Next session:
```
you > "connect to the prod database and check replication lag"

TokioAI:
  [execute_local] psql -h prod-db -p 5433 -U ...   <- remembered the port

  Replication lag is 0.3s, within normal range.
```

Memory is managed via the `memory` tool:
- **read** — show all stored memory
- **append** — add a new fact
- **write** — replace entire memory
- **clear** — wipe memory

The AI also tracks tasks with the `tasks` tool:
- **list** — show pending/active tasks
- **add** — create a new task
- **update** — change status (pending, in_progress, done, blocked)
- **clear_done** — remove completed tasks

### Memory sync across machines

If you run TokioAI on multiple computers and want them to share memory, you can connect them to a central TokioAI Agent server:

```bash
# In ~/.tokioai/.env
TOKIO_AGENT_URL=http://your-server:8001
```

When this is set:
- **On startup**, the CLI downloads shared memory from the agent and merges it with local memory
- **When saving**, the CLI uploads memory to the agent so other machines can access it
- If the agent is unreachable, the CLI continues with local memory — no errors, no blocking

When `TOKIO_AGENT_URL` is not set (the default), memory is fully local. No network calls, no external dependencies.

**Setting up the agent server:**

The TokioAI Agent exposes a simple REST API:
- `GET /memory` — returns the shared memory content
- `POST /memory` — updates shared memory (JSON body: `{"memory": "content here"}`)

Any HTTP server that implements these two endpoints works. You can use the full TokioAI Agent (Docker) or build your own.

---

## Remote access

TokioAI can SSH into your machines and operate on them directly. Configure in `~/.tokioai/.env`:

```bash
# Raspberry Pi
RASPI_IP=192.168.1.100
RASPI_SSH_USER=pi
SSH_KEY_RASPI=~/.ssh/id_rsa

# Cloud VM
GCP_SSH_HOST=your-server-ip
GCP_SSH_USER=user
SSH_KEY_GCP=~/.ssh/id_rsa

# Router
ROUTER_IP=192.168.1.1
```

Or SSH into any server on demand — just tell TokioAI the IP and it'll use the `ssh_connect` tool.

For password-based SSH: `pip install paramiko`

---

## Robot control

TokioAI can control robots over HTTP. Currently supported:

| Robot | What it is | Tool |
|-------|-----------|------|
| **PiDog** | SunFounder quadruped robot (Raspberry Pi) | `pidog` |
| **PiCar-X** | SunFounder autonomous car (Raspberry Pi) | `picar` |

Configure the robot URLs in `~/.tokioai/.env`:

```bash
PIDOG_URL=http://192.168.1.50:5001
PICAR_URL=http://192.168.1.51:5002
```

Each robot runs a small HTTP proxy on its Raspberry Pi that translates REST calls into hardware commands. The AI can:

- **Query status** — battery, sensors, IMU, distance
- **Move** — walk, turn, drive, steer
- **Actions** — bark, pushup, sit, stretch, wag tail (PiDog)
- **Speak** — play sounds through the robot's speaker
- **Take photos** — capture snapshots from the robot's camera

```
you > "make PiDog bark twice then do a pushup"

TokioAI:
  [pidog] speak: bark
  [pidog] speak: bark
  [pidog] do_action: pushup

  Done! PiDog barked twice and did a pushup.
```

The robots work alongside all other tools — you can combine robot control with SSH, file editing, diagnostics, and anything else in a single conversation.

---

## Smart home (Home Assistant)

TokioAI can control your smart home through [Home Assistant](https://www.home-assistant.io/). Lights, speakers, Alexa, switches, sensors, vacuum robots — anything HA can control, TokioAI can control.

Configure in `~/.tokioai/.env`:

```bash
HA_URL=http://your-homeassistant-ip:8123
HA_TOKEN=your-long-lived-access-token
```

To create a long-lived access token: HA web UI → Profile → Long-Lived Access Tokens → Create Token.

The `home_assistant` tool supports:

| Action | What it does |
|--------|-------------|
| `list_entities` | List all HA entities (optionally filtered by domain) |
| `get_state` | Get current state of any entity (lights, sensors, media players) |
| `call_service` | Call any HA service (turn_on, turn_off, volume_set, etc.) |
| `alexa_play_music` | Play music on Alexa/Echo devices via HA |
| `alexa_speak` | Make Alexa speak text (TTS) |

```
you > "turn on the living room lights and play jazz on Alexa"

TokioAI:
  [home_assistant] list_entities: domain=light
  [home_assistant] call_service: light/turn_on on light.living_room
  [home_assistant] alexa_play_music: "jazz" on media_player.jarvis

  Done! Living room lights are on and jazz is playing on Alexa.
```

If `HA_URL` and `HA_TOKEN` are not set, the tool simply isn't available — no errors, no impact on other functionality.

---

## Context management

Long sessions don't lose context. TokioAI tracks token usage per model and auto-compacts old messages when the context window fills up. The important stuff stays — the noise gets summarized.

When auto-compaction runs, persistent memory is injected into the summary so the AI never forgets your infrastructure details, preferences, or active tasks — even after context compression.

```
stats          <- see token usage and cost
compact        <- manually compress context
```

Sessions persist to disk (`~/.tokioai_session.json`) and resume automatically on restart (within 7 days).

---

## Configuration reference

All configuration goes in `~/.tokioai/.env`. See `.env.example` for a full template.

### Provider settings

| Variable | Description |
|----------|-------------|
| `TOKIOAI_PROVIDER` | Active provider: `anthropic`, `anthropic-vertex`, `openai`, `gemini`, `gemini-vertex`, `openrouter`, `ollama` |
| `TOKIOAI_MODEL` | Default model (e.g., `opus`, `sonnet`, `flash`, `gpt4o`) |

### API keys (one per provider)

| Variable | Provider |
|----------|----------|
| `ANTHROPIC_API_KEY` | Claude (Anthropic API) |
| `VERTEX_PROJECT` | Claude (Vertex AI) — also needs `GOOGLE_APPLICATION_CREDENTIALS` |
| `OPENAI_API_KEY` | OpenAI |
| `GEMINI_API_KEY` | Google Gemini |
| `OPENROUTER_API_KEY` | OpenRouter |
| `OLLAMA_HOST` | Ollama (default: `http://localhost:11434`) |

### SSH hosts (optional)

| Variable | Description |
|----------|-------------|
| `RASPI_IP` | Raspberry Pi IP address |
| `RASPI_SSH_USER` | SSH user for the Pi |
| `SSH_KEY_RASPI` | Path to SSH key for Pi |
| `GCP_SSH_HOST` | Cloud VM IP address |
| `GCP_SSH_USER` | SSH user for the VM |
| `SSH_KEY_GCP` | Path to SSH key for VM |
| `ROUTER_IP` | Router IP address |

### Robots (optional)

| Variable | Description |
|----------|-------------|
| `PIDOG_URL` | PiDog robot proxy URL (e.g., `http://192.168.1.50:5001`) |
| `PICAR_URL` | PiCar-X robot proxy URL (e.g., `http://192.168.1.51:5002`) |

### Home Assistant (optional)

| Variable | Description |
|----------|-------------|
| `HA_URL` | Home Assistant URL (e.g., `http://192.168.1.100:8123`) |
| `HA_TOKEN` | Home Assistant long-lived access token |

### Memory sync (optional)

| Variable | Description |
|----------|-------------|
| `TOKIO_AGENT_URL` | TokioAI Agent URL for shared memory across machines |

### Other

| Variable | Description |
|----------|-------------|
| `MAX_TOKENS` | Max tokens per response (default: `16384`) |

---

## Architecture

```
+-----------+     +----------------+     +---------------+
|   You     |---->|    TokioAI     |---->|  AI Provider  |
| (terminal)|     | (tool executor)|     | Claude/GPT/...|
+-----------+     +------+---------+     +------+--------+
                         |                      |
                  +------v---------+   structured tool calls
                  |  Your systems  |<-----------+
                  | servers, files,|
                  | network, robots|
                  +----------------+
```

TokioAI is the bridge between the model's intelligence and your infrastructure. The model thinks, TokioAI acts.

~2000 lines of Python. No frameworks. No dependencies beyond the provider SDKs. Runs on Linux, macOS, and Windows.

---

## File structure

```
tokioai/
  tokioai_cli/
    __init__.py          # Package init
    __main__.py          # Entry point (python -m tokioai_cli)
    ops.py               # Engine: providers, tools, memory, compaction
    interactive.py       # Interactive REPL with readline, streaming, sessions
  pyproject.toml         # Package config + dependencies
  .env.example           # Configuration template
  README.md              # This file
```

Local data (created on first run):
```
~/.tokioai/
  .env                   # Your configuration
  memory.md              # Persistent memory
  tasks.json             # Task tracking
  SOUL.md                # Optional: infrastructure context loaded into every session
~/.tokioai_session.json  # Session state (auto-resume)
```

---

## SOUL.md — infrastructure context

If you create `~/.tokioai/SOUL.md`, its contents are loaded into every conversation as permanent context. Use it to describe your infrastructure so TokioAI always knows your setup:

```markdown
# My Infrastructure

## Servers
- prod-web: 10.0.1.10 (nginx + app, Ubuntu 22.04)
- prod-db: 10.0.1.20 (PostgreSQL 16, port 5433)
- staging: 10.0.2.10 (everything-in-one)

## Common tasks
- Deploy: `cd /opt/app && git pull && docker compose up -d --build`
- DB backup: `pg_dump -h prod-db -p 5433 -U app mydb > /backups/$(date +%F).sql`

## Credentials
- DB user: app (password in /opt/app/.env)
- SSH: all servers use ~/.ssh/id_ed25519
```

This is optional but powerful — the AI starts every conversation already knowing your world.

---

## License

MIT — Daniel Dieser ([MrMoz](https://github.com/daletoniris))

Built in Patagonia, Argentina.
