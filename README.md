# TokioAI

**Your AI actually does things.** It doesn't just talk — it executes commands, SSHs into your servers, edits your code, scans your network, deploys your infrastructure, and fixes your problems. All from a single prompt.

TokioAI connects to Claude, GPT, Gemini, Ollama, or any model you want — and gives it **real tools** to interact with your systems. Not wrappers. Not plugins. Native tool calling through each provider's API, the same mechanism the models were trained to use.

```
you → "find why nginx is returning 502 and fix it"

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

TokioAI gives AI models 10 tools to interact with your world:

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
model opus       ← Claude Opus 4.6
model flash      ← Gemini Flash (fast + cheap)
model gpt4o      ← GPT-4o
model llama      ← Local Llama 3.1 via Ollama
model deepseek   ← DeepSeek Coder
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

## Context management

Long sessions don't lose context. TokioAI tracks token usage per model and auto-compacts old messages when the context window fills up. The important stuff stays — the noise gets summarized.

```
stats          ← see token usage and cost
compact        ← manually compress context
```

Sessions persist to disk and can be resumed across restarts.

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   You       │────▶│    TokioAI       │────▶│   AI Provider   │
│  (terminal) │     │  (tool executor)  │     │ Claude/GPT/etc  │
└─────────────┘     └──────┬───────────┘     └────────┬────────┘
                           │                          │
                    ┌──────▼───────────┐    structured tool calls
                    │   Your systems   │◀─────────────┘
                    │  servers, files,  │
                    │  network, docker  │
                    └──────────────────┘
```

TokioAI is the bridge between the model's intelligence and your infrastructure. The model thinks, TokioAI acts.

~1300 lines of Python. No frameworks. No dependencies beyond the provider SDKs. Runs on Linux, macOS, and Windows.

---

## License

MIT — Daniel Dieser ([MrMoz](https://github.com/daletoniris))

Built in Patagonia, Argentina.
