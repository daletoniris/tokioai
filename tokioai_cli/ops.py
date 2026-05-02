#!/usr/bin/env python3
"""
TokioAI Ops — Multi-provider AI operations engine.

Supports: Claude Vertex AI, Claude API, OpenAI, Gemini (API key), OpenRouter, Ollama.

Configuration via ~/.tokioai/.env or environment variables.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Optional, Callable

# ---------------------------------------------------------------------------
# Model aliases — human-friendly names → real model IDs
# ---------------------------------------------------------------------------

MODEL_ALIASES = {
    # ── Claude (Anthropic) ──
    "opus": "claude-opus-4-6",
    "opus4": "claude-opus-4-6",
    "opus-4": "claude-opus-4-6",
    "opus46": "claude-opus-4-6",
    "opus-4.6": "claude-opus-4-6",
    "claude-opus-4": "claude-opus-4-6",
    "opus3": "claude-3-opus-20240229",
    "sonnet": "claude-sonnet-4-6",
    "sonnet4": "claude-sonnet-4-6",
    "sonnet-4": "claude-sonnet-4-6",
    "sonnet46": "claude-sonnet-4-6",
    "claude-sonnet-4": "claude-sonnet-4-6",
    "sonnet37": "claude-3-7-sonnet-20250219",
    "sonnet35": "claude-3-5-sonnet-20241022",
    "haiku": "claude-3-5-haiku-20241022",
    "haiku35": "claude-3-5-haiku-20241022",
    # ── OpenAI ──
    "gpt4o": "gpt-4o",
    "gpt4": "gpt-4o",
    "gpt": "gpt-4o",
    "o1": "o1",
    "o3": "o3",
    "o3-mini": "o3-mini",
    "gpt5": "gpt-5",
    # ── Gemini ──
    "flash": "gemini-2.5-flash",
    "gemini-flash": "gemini-2.5-flash",
    "flash3": "gemini-3-flash-preview",
    "gemini3": "gemini-3-flash-preview",
    "gemini-3": "gemini-3-flash-preview",
    "gemini-3-flash": "gemini-3-flash-preview",
    "gemini31": "gemini-3.1-pro-preview",
    "gemini-3.1": "gemini-3.1-pro-preview",
    "gemini-3.1-pro": "gemini-3.1-pro-preview",
    "gemini-pro": "gemini-2.5-pro",
    "pro": "gemini-2.5-pro",
    "pro-preview": "gemini-2.5-pro-preview-06-05",
    "gemini": "gemini-2.5-flash",
    # ── Ollama (local) ──
    "llama": "llama3.1:8b",
    "llama3": "llama3.1:8b",
    "codellama": "codellama:13b",
    "mistral": "mistral:7b",
    "deepseek": "deepseek-coder-v2:16b",
    "qwen": "qwen2.5-coder:14b",
    # ── OpenRouter ──
    "or-claude": "anthropic/claude-sonnet-4",
    "or-gpt": "openai/gpt-4o",
    "or-gemini": "google/gemini-2.5-flash-preview",
    "or-llama": "meta-llama/llama-3.1-405b-instruct",
    "or-deepseek": "deepseek/deepseek-r1",
}


def resolve_model(name: str) -> str:
    """Resolve model alias to full model name."""
    return MODEL_ALIASES.get(name.lower().strip(), name)


def list_aliases() -> dict[str, list[str]]:
    """Group aliases by provider for display."""
    groups = {
        "Claude": [], "OpenAI": [], "Gemini": [],
        "Ollama": [], "OpenRouter": [],
    }
    seen = set()
    for alias, model in MODEL_ALIASES.items():
        if model in seen:
            continue
        seen.add(model)
        if "claude" in model:
            groups["Claude"].append((alias, model))
        elif "gpt" in model or model in ("o1", "o3", "o3-mini"):
            groups["OpenAI"].append((alias, model))
        elif "gemini" in model:
            groups["Gemini"].append((alias, model))
        elif ":" in model:
            groups["Ollama"].append((alias, model))
        elif "/" in model:
            groups["OpenRouter"].append((alias, model))
    return groups


# ---------------------------------------------------------------------------
# Provider detection — auto-detect from env vars
# ---------------------------------------------------------------------------

def detect_provider() -> str:
    """Auto-detect the best available provider from env vars."""
    explicit = os.getenv("TOKIOAI_PROVIDER", "").lower().strip()
    if explicit:
        return explicit

    # Vertex AI credentials → anthropic-vertex
    if os.getenv("VERTEX_PROJECT") or os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"):
        return "anthropic-vertex"

    # Direct Anthropic API key
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return "openai"

    # Gemini (API key)
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"

    # OpenRouter
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"

    # Ollama
    if os.getenv("OLLAMA_HOST"):
        return "ollama"

    return "anthropic"  # default


def detect_model() -> str:
    """Get the configured model, resolved from aliases."""
    raw = (
        os.getenv("TOKIOAI_MODEL")
        or os.getenv("VERTEX_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or os.getenv("CLAUDE_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or ""
    )
    if raw:
        return resolve_model(raw)

    # Default per provider
    provider = detect_provider()
    defaults = {
        "anthropic-vertex": "claude-opus-4-6",
        "anthropic": "claude-opus-4-6",
        "openai": "gpt-4o",
        "gemini": "gemini-2.5-flash",
        "gemini-vertex": "gemini-3.1-pro-preview",
        "openrouter": "anthropic/claude-opus-4",
        "ollama": "llama3.1:8b",
    }
    return defaults.get(provider, "claude-opus-4-6")


# Export for interactive.py — these are set AFTER .env is loaded
PROVIDER = detect_provider()
MODEL = detect_model()
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT") or os.getenv("ANTHROPIC_VERTEX_PROJECT_ID", "")
VERTEX_REGION = os.getenv("VERTEX_REGION") or os.getenv("ANTHROPIC_VERTEX_REGION") or os.getenv("CLOUD_ML_REGION", "global")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "16384"))

# SSH keys (optional — for remote execution)
SSH_RASPI = os.path.expanduser(os.getenv("SSH_KEY_RASPI", "~/.ssh/id_rsa"))
SSH_GCP = os.path.expanduser(os.getenv("SSH_KEY_GCP", "~/.ssh/google_compute_engine"))

# Hosts (optional)
RASPI_IP = os.getenv("RASPI_IP", "")
RASPI_TS = os.getenv("RASPI_TAILSCALE_IP", "")
RASPI_USER = os.getenv("RASPI_SSH_USER", "pi")
GCP_IP = os.getenv("GCP_SSH_HOST", "")
GCP_USER = os.getenv("GCP_SSH_USER", "user")
ROUTER_IP = os.getenv("ROUTER_IP", "")


# ---------------------------------------------------------------------------
# System prompt — TokioAI personality
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are TokioAI — specialized in cybersecurity, hacking, engineering, DevOps, and creative problem solving.

You execute commands, fix bugs, deploy infrastructure, audit security, and build solutions. You have full access to the user's terminal.

## Your Expertise
- **Cybersecurity**: Penetration testing, vulnerability assessment, network security, OSINT, forensics, incident response, WAF/IDS/IPS, hardening
- **Hacking**: Ethical hacking, CTF, reverse engineering, exploit development, social engineering awareness
- **Engineering**: Full-stack development, system architecture, API design, database optimization, algorithms
- **DevOps**: CI/CD, Docker, Kubernetes, Terraform, Ansible, cloud infrastructure (GCP/AWS/Azure), monitoring
- **Networking**: TCP/IP, DNS, firewalls, VPN, SDN, wireless security, packet analysis
- **Creative**: Unconventional solutions, automation, scripting, tool building

## Available Tools
- **execute_local**: Run any shell command on the user's machine
- **execute_raspi**: SSH to Raspberry Pi (if configured)
- **execute_gcp**: SSH to GCP VM (if configured)
- **execute_router**: SSH to router (if configured)
- **ssh_connect**: SSH to ANY server with username/password — ask the user for IP, user, and password if not provided. Use this for ad-hoc server connections. The password is used only for the connection and never stored.
- **read_file / write_file / edit_file**: File operations (local or remote via raspi:/gcp: prefix)
- **search_files**: grep across files
- **diagnose**: System health check

## Your Approach
1. Understand the request — ask only if truly ambiguous
2. Diagnose first — read logs, check status, gather info
3. Act — fix, build, deploy, configure
4. Verify — confirm the fix works
5. Report — concise summary of what you did

## Rules
- Be DIRECT. Act first, explain after.
- NEVER give up. If something fails, try alternatives.
- Show results, not just descriptions.
- When fixing something: diagnose → root cause → fix → verify.
- When building something: plan → implement → test → deliver.
- Always mask credentials in output.
- Use Spanish if the user speaks Spanish, English otherwise.
- Be creative. Think like a hacker. Find elegant solutions."""


# ---------------------------------------------------------------------------
# Tool definitions for Claude/OpenAI/Gemini native tool use
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "execute_local",
        "description": "Execute a shell command on the local machine. Use for any system operation: install packages, check processes, network scans, file operations, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute (bash)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30, max 300)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "execute_raspi",
        "description": "Execute a command on the Raspberry Pi via SSH. Uses LAN IP, falls back to Tailscale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to run on Raspi"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30, max 300)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "execute_gcp",
        "description": "Execute a command on the GCP VM via SSH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to run on GCP"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30, max 300)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "execute_router",
        "description": "Execute a command on the router via SSH (root).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to run on router as root"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from local or remote systems. Use raspi:/path or gcp:/path for remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path. Use raspi:/path or gcp:/path for remote"},
                "lines": {"type": "integer", "description": "Max lines to read (default: all)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Prefix with raspi: or gcp: for remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path. Use raspi:/path or gcp:/path for remote"},
                "content": {"type": "string", "description": "File content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace a specific string in a file. old_text must be unique in the file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path. Use raspi:/path or gcp:/path for remote"},
                "old_text": {"type": "string", "description": "Exact text to find (must be unique)"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for text patterns across files. Like grep -rn.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text or regex pattern to search"},
                "path": {"type": "string", "description": "Directory to search (default: cwd). Use raspi:/path or gcp:/path"},
                "glob": {"type": "string", "description": "File filter glob (e.g., '*.py')"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "diagnose",
        "description": "Run system health diagnostics on local, raspi, gcp, or all targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target: local, raspi, gcp, router, all",
                    "enum": ["local", "raspi", "gcp", "router", "all"],
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "ssh_connect",
        "description": "Connect to a remote server via SSH with username and password (no key required). Use this to execute commands on any server. The connection is non-interactive — runs a command and returns the output. If no command is given, runs 'hostname && uname -a && uptime' to test the connection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "IP address or hostname of the server"},
                "username": {"type": "string", "description": "SSH username"},
                "password": {"type": "string", "description": "SSH password"},
                "command": {"type": "string", "description": "Command to execute on the remote server. Default: 'hostname && uname -a && uptime'"},
                "port": {"type": "integer", "description": "SSH port (default: 22)"},
                "timeout": {"type": "integer", "description": "Connection timeout in seconds (default: 10)"},
            },
            "required": ["host", "username", "password"],
        },
    },
]


# ---------------------------------------------------------------------------
# Command execution — safe, never touches terminal
# ---------------------------------------------------------------------------

def _run_cmd(cmd: str, timeout: int = 30) -> str:
    """Execute a local command. stdin=DEVNULL so it NEVER competes with readline."""
    try:
        r = subprocess.run(
            cmd, shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=min(timeout, 300),
        )
        out = (r.stdout + r.stderr).strip()
        return out[:16000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"


def _ssh_cmd(host: str, key: str, user: str, cmd: str, timeout: int = 30) -> str:
    """Run a command via SSH. -T and BatchMode=yes to NEVER touch the terminal."""
    if not host:
        return "ERROR: Host not configured. Set the corresponding env var in ~/.tokioai/.env"
    # Quote key path for Windows paths with spaces
    key_quoted = f'"{key}"' if " " in key else key
    ssh = (
        f'ssh -T -i {key_quoted} -o ConnectTimeout=5 -o StrictHostKeyChecking=no '
        f'-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR '
        f'-o BatchMode=yes {user}@{host} "{cmd}"'
    )
    return _run_cmd(ssh, timeout)


def _raspi_cmd(cmd: str, timeout: int = 30) -> str:
    if RASPI_IP:
        result = _ssh_cmd(RASPI_IP, SSH_RASPI, RASPI_USER, cmd, timeout)
        if not result.startswith("ERROR") and not result.startswith("TIMEOUT"):
            return result
    if RASPI_TS:
        return _ssh_cmd(RASPI_TS, SSH_RASPI, RASPI_USER, cmd, timeout)
    return "ERROR: Raspi not configured. Set RASPI_IP or RASPI_TAILSCALE_IP in ~/.tokioai/.env"


def _gcp_cmd(cmd: str, timeout: int = 30) -> str:
    return _ssh_cmd(GCP_IP, SSH_GCP, GCP_USER, cmd, timeout)


def _ssh_password_cmd(host: str, username: str, password: str, cmd: str,
                      port: int = 22, timeout: int = 10) -> str:
    """SSH with username/password using paramiko. Falls back to sshpass if paramiko unavailable."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, port=port, username=username, password=password,
                          timeout=timeout, allow_agent=False, look_for_keys=False)
            stdin, stdout, stderr = client.exec_command(cmd, timeout=max(timeout, 30))
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            client.close()
            result = (out + err).strip()
            if exit_code != 0:
                result = f"[exit code {exit_code}]\n{result}"
            return result[:16000] if result else "(no output)"
        except paramiko.AuthenticationException:
            return f"ERROR: Authentication failed for {username}@{host} — wrong username or password"
        except paramiko.SSHException as e:
            return f"ERROR: SSH error connecting to {host}: {e}"
        except Exception as e:
            client.close()
            return f"ERROR: {e}"
    except ImportError:
        # Fallback: sshpass (Linux only)
        sshpass_cmd = (
            f'sshpass -p "{password}" ssh -T -p {port} '
            f'-o ConnectTimeout={timeout} -o StrictHostKeyChecking=no '
            f'-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR '
            f'{username}@{host} "{cmd}"'
        )
        result = _run_cmd(sshpass_cmd, timeout + 5)
        if "sshpass" in result.lower() and "not found" in result.lower():
            return (
                "ERROR: paramiko not installed and sshpass not available.\n"
                "Install paramiko: pip install paramiko\n"
                "Or install sshpass: sudo apt install sshpass"
            )
        return result


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return the result string."""
    timeout = input_data.get("timeout", 30)

    if name == "execute_local":
        return _run_cmd(input_data["command"], timeout)

    elif name == "execute_raspi":
        return _raspi_cmd(input_data["command"], timeout)

    elif name == "execute_gcp":
        return _gcp_cmd(input_data["command"], timeout)

    elif name == "execute_router":
        cmd = input_data["command"]
        if ROUTER_IP:
            return _raspi_cmd(
                f'ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@{ROUTER_IP} "{cmd}"'
            )
        return "ERROR: Router not configured. Set ROUTER_IP in ~/.tokioai/.env"

    elif name == "read_file":
        path = input_data["path"]
        max_lines = input_data.get("lines", 0)
        tail = f" | head -n {max_lines}" if max_lines else ""
        if path.startswith("raspi:"):
            return _raspi_cmd(f"cat {path[6:]}{tail}")
        elif path.startswith("gcp:"):
            return _gcp_cmd(f"cat {path[4:]}{tail}")
        else:
            try:
                with open(path, "r") as f:
                    content = f.read()
                if max_lines:
                    content = "\n".join(content.split("\n")[:max_lines])
                return content[:16000]
            except Exception as e:
                return f"ERROR: {e}"

    elif name == "write_file":
        path = input_data["path"]
        content = input_data["content"]
        if path.startswith("raspi:"):
            remote_path = path[6:]
            tmp = f"/tmp/tokio_deploy_{int(time.time())}"
            with open(tmp, "w") as f:
                f.write(content)
            result = _run_cmd(f"scp -i {SSH_RASPI} -o StrictHostKeyChecking=no {tmp} {RASPI_USER}@{RASPI_IP}:{remote_path}")
            os.unlink(tmp)
            return result if result.startswith("ERROR") else f"Written to raspi:{remote_path}"
        elif path.startswith("gcp:"):
            remote_path = path[4:]
            tmp = f"/tmp/tokio_deploy_{int(time.time())}"
            with open(tmp, "w") as f:
                f.write(content)
            _run_cmd(f"scp -i {SSH_GCP} -o StrictHostKeyChecking=no {tmp} {GCP_USER}@{GCP_IP}:/tmp/_deploy_tmp")
            result = _gcp_cmd(f"sudo cp /tmp/_deploy_tmp {remote_path}")
            os.unlink(tmp)
            return result if result.startswith("ERROR") else f"Written to gcp:{remote_path}"
        else:
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                return f"Written to {path}"
            except Exception as e:
                return f"ERROR: {e}"

    elif name == "edit_file":
        path = input_data["path"]
        old_text = input_data["old_text"]
        new_text = input_data["new_text"]
        if path.startswith("raspi:") or path.startswith("gcp:"):
            content = execute_tool("read_file", {"path": path})
            if content.startswith("ERROR"):
                return content
            count = content.count(old_text)
            if count == 0:
                return f"ERROR: old_text not found in {path}"
            if count > 1:
                return f"ERROR: old_text appears {count} times — must be unique"
            new_content = content.replace(old_text, new_text, 1)
            return execute_tool("write_file", {"path": path, "content": new_content})
        else:
            try:
                with open(path, "r") as f:
                    content = f.read()
                count = content.count(old_text)
                if count == 0:
                    return f"ERROR: old_text not found in {path}"
                if count > 1:
                    return f"ERROR: old_text appears {count} times — must be unique"
                new_content = content.replace(old_text, new_text, 1)
                with open(path, "w") as f:
                    f.write(new_content)
                return f"Edited {path} (replaced 1 occurrence)"
            except Exception as e:
                return f"ERROR: {e}"

    elif name == "search_files":
        pattern = input_data["pattern"]
        path = input_data.get("path", os.getcwd())
        glob_filter = input_data.get("glob", "")
        include = f"--include='{glob_filter}'" if glob_filter else ""
        if path.startswith("raspi:"):
            return _raspi_cmd(f"grep -rn {include} '{pattern}' {path[6:] or '/home'} | head -30")
        elif path.startswith("gcp:"):
            return _gcp_cmd(f"grep -rn {include} '{pattern}' {path[4:] or '/home'} | head -30")
        else:
            return _run_cmd(f"grep -rn {include} '{pattern}' {path} | head -50")

    elif name == "diagnose":
        target = input_data["target"]
        results = []
        if target in ("local", "all"):
            results.append("\n=== LOCAL ===")
            results.append(_run_cmd("uname -a"))
            results.append(_run_cmd("uptime && free -h | head -2"))
            results.append(_run_cmd("df -h / | tail -1"))
            results.append(_run_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo 'Docker not available'"))
        if target in ("raspi", "all"):
            results.append("\n=== RASPBERRY PI ===")
            results.append(_raspi_cmd("uptime && free -h | head -2"))
            results.append(_raspi_cmd("df -h / | tail -1"))
            results.append(_raspi_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo 'No docker'"))
        if target in ("gcp", "all"):
            results.append("\n=== GCP ===")
            results.append(_gcp_cmd("uptime && free -h | head -2"))
            results.append(_gcp_cmd("df -h / | tail -1"))
            results.append(_gcp_cmd("sudo docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo 'No docker'"))
        if target in ("router", "all"):
            results.append("\n=== ROUTER ===")
            if ROUTER_IP:
                results.append(_raspi_cmd(f'ssh -o ConnectTimeout=5 root@{ROUTER_IP} "uptime; free | head -2"'))
            else:
                results.append("Router not configured")
        return "\n".join(results)

    elif name == "ssh_connect":
        host = input_data["host"]
        username = input_data["username"]
        password = input_data["password"]
        command = input_data.get("command", "hostname && uname -a && uptime")
        port = input_data.get("port", 22)
        timeout = input_data.get("timeout", 10)
        return _ssh_password_cmd(host, username, password, command, port, timeout)

    return f"ERROR: Unknown tool '{name}'"


# ---------------------------------------------------------------------------
# Client initialization — one function, all providers
# ---------------------------------------------------------------------------

def init_client(provider: str):
    """Initialize AI client. Returns (client, client_type)."""
    provider = provider.lower().strip()

    if provider in ("anthropic-vertex", "claude-vertex", "vertex"):
        project = VERTEX_PROJECT
        region = VERTEX_REGION
        if not project:
            print("\033[31mERROR: Vertex AI project not configured.\033[0m")
            print("Set VERTEX_PROJECT or ANTHROPIC_VERTEX_PROJECT_ID in ~/.tokioai/.env")
            print("Then run: gcloud auth application-default login")
            sys.exit(1)
        # Auto-detect credentials
        sa_paths = [
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
        ]
        for sa_path in sa_paths:
            if sa_path and os.path.isfile(sa_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
                break
        try:
            from anthropic import AnthropicVertex
            client = AnthropicVertex(region=region, project_id=project)
            return client, "anthropic"
        except ImportError:
            print("\033[31mERROR: anthropic[vertex] not installed\033[0m")
            print("Run: pip install 'anthropic[vertex]'")
            sys.exit(1)

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("\033[31mERROR: ANTHROPIC_API_KEY not set\033[0m")
            print("Get your key at: https://console.anthropic.com/")
            sys.exit(1)
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=api_key), "anthropic"
        except ImportError:
            print("\033[31mERROR: anthropic not installed. Run: pip install anthropic\033[0m")
            sys.exit(1)

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("\033[31mERROR: OPENAI_API_KEY not set\033[0m")
            print("Get your key at: https://platform.openai.com/api-keys")
            sys.exit(1)
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key), "openai"
        except ImportError:
            print("\033[31mERROR: openai not installed. Run: pip install openai\033[0m")
            sys.exit(1)

    elif provider == "gemini-vertex":
        project = os.getenv("GEMINI_VERTEX_PROJECT") or os.getenv("VERTEX_PROJECT") or os.getenv("ANTHROPIC_VERTEX_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
        region = os.getenv("GEMINI_VERTEX_REGION") or os.getenv("CLOUD_ML_REGION", "us-central1")
        if not project:
            print("\033[31mERROR: Gemini Vertex project not configured.\033[0m")
            print("Set GEMINI_VERTEX_PROJECT in ~/.tokioai/.env")
            sys.exit(1)
        sa_paths = [
            os.getenv("GEMINI_SA_PATH", ""),
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
        ]
        sa_file = ""
        for p in sa_paths:
            if p and os.path.isfile(p):
                sa_file = p
                break
        try:
            from google import genai
            if sa_file:
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    sa_file, scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                client = genai.Client(vertexai=True, project=project, location=region, credentials=creds)
            else:
                client = genai.Client(vertexai=True, project=project, location=region)
            return client, "gemini"
        except ImportError:
            print("\033[31mERROR: google-genai not installed. Run: pip install google-genai\033[0m")
            sys.exit(1)

    elif provider in ("gemini", "google"):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            print("\033[31mERROR: GEMINI_API_KEY or GOOGLE_API_KEY not set\033[0m")
            print("Get your key at: https://aistudio.google.com/apikey")
            sys.exit(1)
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            return client, "gemini"
        except ImportError:
            print("\033[31mERROR: google-genai not installed. Run: pip install google-genai\033[0m")
            sys.exit(1)

    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            print("\033[31mERROR: OPENROUTER_API_KEY not set\033[0m")
            print("Get your key at: https://openrouter.ai/keys")
            sys.exit(1)
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            return client, "openai"  # OpenRouter uses OpenAI-compatible API
        except ImportError:
            print("\033[31mERROR: openai not installed. Run: pip install openai\033[0m")
            sys.exit(1)

    elif provider in ("ollama", "local"):
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=f"{host}/v1",
                api_key="ollama",
            )
            return client, "openai"
        except ImportError:
            print("\033[31mERROR: openai not installed. Run: pip install openai\033[0m")
            sys.exit(1)

    else:
        print(f"\033[31mERROR: Unknown provider '{provider}'\033[0m")
        print("Available: anthropic-vertex, anthropic, openai, gemini, openrouter, ollama")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Convert tools to OpenAI function calling format
# ---------------------------------------------------------------------------

def _tools_to_openai(tools: list) -> list:
    """Convert Anthropic-style tools to OpenAI function calling format."""
    result = []
    for tool in tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        })
    return result


# ---------------------------------------------------------------------------
# TokioOps — Main engine
# ---------------------------------------------------------------------------

class TokioOps:
    """TokioAI Operations engine with native tool use."""

    # Auto-compact: triggers on message count OR estimated token size
    COMPACT_THRESHOLD = 16        # compact early to save $$$
    COMPACT_KEEP_RECENT = 6       # keep last N messages intact
    COMPACT_TOKEN_LIMIT = 60000   # compact if estimated tokens exceed this
    MAX_TOOL_RESULT = 8000        # truncate tool results beyond this (chars ~2K tokens)
    # Cheap model for summarization (Sonnet = ~5x cheaper than Opus)
    COMPACT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, provider: str = None, model: str = None):
        self._provider_name = provider or PROVIDER
        self._model = model or MODEL
        self._client, self._client_type = init_client(self._provider_name)
        self._messages: list[dict] = []
        self._gemini_history: list = []  # Persistent Gemini contents
        self._max_turns = 100
        self._max_rounds = 25
        self._max_time = 600
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._last_tracked_input = 0
        self._last_tracked_output = 0
        self._compaction_count = 0

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    @property
    def provider(self) -> str:
        return self._provider_name

    @property
    def token_usage_str(self) -> str:
        return f"{self._total_input_tokens:,} in / {self._total_output_tokens:,} out"

    def switch_model(self, new_model: str, new_provider: str = None):
        """Switch to a different model (and optionally provider) at runtime."""
        if new_provider and new_provider != self._provider_name:
            self._provider_name = new_provider
            self._client, self._client_type = init_client(new_provider)
        self._model = new_model

    def _extract_text(self, msg: dict) -> str:
        """Extract readable text from a message for summarization."""
        content = msg.get("content", "")
        if isinstance(content, str):
            return content[:500]
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", "")[:200])
                    elif item.get("type") == "tool_result":
                        parts.append(f"[tool_result: {str(item.get('content', ''))[:100]}]")
                    elif item.get("type") == "tool_use":
                        parts.append(f"[tool: {item.get('name', '?')}]")
                elif hasattr(item, "text"):
                    parts.append(str(item.text)[:200] if item.text else "")
                elif hasattr(item, "type") and item.type == "tool_use":
                    parts.append(f"[tool: {getattr(item, 'name', '?')}]")
            return " ".join(parts)[:500]
        return str(content)[:500]

    def _has_tool_use(self, msg: dict) -> bool:
        """Check if a message contains tool_use blocks (assistant) or tool_result blocks (user)."""
        content = msg.get("content", "")
        if isinstance(content, str):
            return False
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    t = item.get("type", "")
                    if t in ("tool_use", "tool_result"):
                        return True
                elif hasattr(item, "type") and item.type in ("tool_use", "tool_result"):
                    return True
        return False

    def _find_safe_cut(self, target_keep: int) -> int:
        """Find a safe index to cut messages so we don't split tool_use/tool_result pairs.
        Returns the index where recent messages start (everything before gets summarized)."""
        n = len(self._messages)
        # Start from the target cut point and scan backwards to find a safe boundary
        # A safe boundary is: after an assistant text-only message, or after a user text-only message
        cut = max(0, n - target_keep)
        # Scan forward from cut to find the first safe point
        for i in range(cut, n):
            msg = self._messages[i]
            # Safe if this is a user message with plain text (not tool_results)
            # and previous message (if any) is assistant with plain text (not tool_use)
            if not self._has_tool_use(msg):
                if msg.get("role") == "user" and isinstance(msg.get("content", ""), str):
                    return i
                if msg.get("role") == "assistant" and i + 1 < n:
                    next_msg = self._messages[i + 1]
                    if next_msg.get("role") == "user" and not self._has_tool_use(next_msg):
                        return i + 1
        # Fallback: keep more messages to be safe
        return n  # don't compact if no safe cut found

    def _estimate_tokens(self) -> int:
        """Rough estimate of total tokens in messages (~4 chars per token)."""
        total = 0
        for msg in self._messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        total += len(str(item.get("content", "") or item.get("text", ""))) // 4
                    elif hasattr(item, "text") and item.text:
                        total += len(item.text) // 4
            else:
                total += len(str(content)) // 4
        return total

    def _compact_messages(self, on_text=None):
        """Auto-compact old messages into a summary when conversation gets too long."""
        est_tokens = self._estimate_tokens()
        needs_compact = (len(self._messages) >= self.COMPACT_THRESHOLD or
                         est_tokens > self.COMPACT_TOKEN_LIMIT)
        if not needs_compact:
            return

        cut_idx = self._find_safe_cut(self.COMPACT_KEEP_RECENT)
        if cut_idx <= 2:
            return  # nothing to compact

        old_msgs = self._messages[:cut_idx]
        recent_msgs = self._messages[cut_idx:]

        # Build a digest of old messages for summarization
        digest_lines = []
        for msg in old_msgs:
            role = msg.get("role", "?")
            text = self._extract_text(msg)
            if text.strip():
                digest_lines.append(f"[{role}] {text}")

        digest = "\n".join(digest_lines)
        if len(digest) > 8000:
            digest = digest[:8000] + "\n... (truncated)"

        summary_prompt = (
            "Summarize the following conversation history concisely. "
            "Keep: key decisions, commands run, results, errors, file paths, IPs, and pending tasks. "
            "Drop: routine tool outputs, repeated attempts, verbose logs.\n\n"
            f"{digest}"
        )

        summary = None
        # Try Gemini Flash first — cheapest option (~$0.0001 per compact)
        try:
            from google import genai
            from google.genai import types as _gtypes
            _compact_project = (os.getenv("GEMINI_VERTEX_PROJECT") or os.getenv("VERTEX_PROJECT")
                                or os.getenv("ANTHROPIC_VERTEX_PROJECT_ID") or "")
            if _compact_project:
                _gc = genai.Client(vertexai=True, project=_compact_project, location="global")
                _gr = _gc.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=summary_prompt,
                    config=_gtypes.GenerateContentConfig(
                        system_instruction="Summarize concisely. Keep: decisions, commands, results, errors, paths, IPs, pending tasks. Drop: verbose logs.",
                        max_output_tokens=1024,
                    ),
                )
                summary = _gr.text
        except Exception:
            pass

        # Fallback: use the main model's own client (works with any provider: Opus, Ollama, OpenAI, etc.)
        if not summary:
            try:
                if self._client_type == "anthropic":
                    resp = self._client.messages.create(
                        model=self._model,
                        max_tokens=1024,
                        system="Summarize concisely. Keep: decisions, commands, results, errors, paths, IPs, pending tasks.",
                        messages=[{"role": "user", "content": summary_prompt}],
                        timeout=30.0,
                    )
                    summary = "".join(b.text for b in resp.content if hasattr(b, "text"))
                    if hasattr(resp, "usage"):
                        self._total_input_tokens += getattr(resp.usage, "input_tokens", 0)
                        self._total_output_tokens += getattr(resp.usage, "output_tokens", 0)
                elif self._client_type == "openai":
                    resp = self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": "Summarize concisely. Keep: decisions, commands, results, errors, paths, IPs, pending tasks."},
                            {"role": "user", "content": summary_prompt},
                        ],
                        max_tokens=1024,
                        timeout=30.0,
                    )
                    summary = resp.choices[0].message.content or ""
            except Exception:
                pass

        # Last resort: raw truncation
        if not summary:
            summary = digest[:3000]

        # Replace old messages with the summary
        self._messages = [
            {"role": "user", "content": f"[Previous conversation summary]\n{summary}"},
            {"role": "assistant", "content": "Understood. I have the context from our previous conversation. Let's continue."},
        ] + recent_msgs

        self._compaction_count += 1
        if on_text:
            on_text(f"\n⚡ Context compacted ({len(old_msgs)} messages summarized, keeping {len(recent_msgs)} recent)\n")

    def chat(self, user_input: str, on_tool_start=None, on_tool_end=None, on_text=None) -> str:
        """Process a user request with tool use. Fully synchronous — NEVER touches terminal."""
        if self._client_type == "anthropic":
            return self._chat_anthropic(user_input, on_tool_start, on_tool_end, on_text)
        elif self._client_type == "openai":
            return self._chat_openai(user_input, on_tool_start, on_tool_end, on_text)
        elif self._client_type == "gemini":
            return self._chat_gemini(user_input, on_tool_start, on_tool_end, on_text)
        else:
            return f"ERROR: Unknown client type {self._client_type}"

    # ── Anthropic (Claude — direct API or Vertex) ─────────

    def _chat_anthropic(self, user_input, on_tool_start, on_tool_end, on_text) -> str:
        self._compact_messages(on_text)
        self._messages.append({"role": "user", "content": user_input})

        for turn in range(self._max_turns):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=self._messages,
                    timeout=120.0,
                )
            except Exception as e:
                err_str = str(e).lower()
                # Auto-compact on context length errors and retry once
                if any(k in err_str for k in ("prompt is too long", "context length", "max_tokens", "token limit", "request too large")):
                    if len(self._messages) > 6:
                        self._compact_messages(on_text)
                        continue  # retry with compacted context
                return f"API Error: {e}"

            # Track tokens
            if hasattr(response, "usage"):
                self._total_input_tokens += getattr(response.usage, "input_tokens", 0)
                self._total_output_tokens += getattr(response.usage, "output_tokens", 0)

            # Check for tool use
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if tool_blocks:
                # Emit any text before tools
                for block in response.content:
                    if hasattr(block, "text") and block.text and on_text:
                        on_text(block.text)

                self._messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tb in tool_blocks:
                    if on_tool_start:
                        on_tool_start(tb.name, tb.input)
                    result = execute_tool(tb.name, tb.input)
                    if on_tool_end:
                        on_tool_end(tb.name, result)
                    # Truncate very large tool results to avoid blowing context
                    if len(result) > self.MAX_TOOL_RESULT:
                        result = result[:self.MAX_TOOL_RESULT] + "\n... (truncated)"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tb.id,
                        "content": result,
                    })

                self._messages.append({"role": "user", "content": tool_results})

            else:
                # No tools — extract final text
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text
                self._messages.append({"role": "assistant", "content": text})
                return text

        return "Max tool turns reached."

    # ── OpenAI / OpenRouter / Ollama ───────────────────

    def _chat_openai(self, user_input, on_tool_start, on_tool_end, on_text) -> str:
        self._compact_messages(on_text)
        self._messages.append({"role": "user", "content": user_input})
        openai_tools = _tools_to_openai(TOOLS)

        for turn in range(self._max_turns):
            try:
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + self._messages
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=msgs,
                    tools=openai_tools,
                    max_tokens=MAX_TOKENS,
                    timeout=120.0,
                )
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ("prompt is too long", "context length", "max_tokens", "token limit", "request too large")):
                    if len(self._messages) > 6:
                        self._compact_messages(on_text)
                        continue
                return f"API Error: {e}"

            # Track tokens
            if hasattr(response, "usage") and response.usage:
                self._total_input_tokens += getattr(response.usage, "prompt_tokens", 0)
                self._total_output_tokens += getattr(response.usage, "completion_tokens", 0)

            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                self._messages.append(msg)

                # Emit text if any
                if msg.content and msg.content.strip() and on_text:
                    on_text(msg.content)

                for tc in msg.tool_calls:
                    fn = tc.function
                    args = json.loads(fn.arguments) if fn.arguments else {}
                    if on_tool_start:
                        on_tool_start(fn.name, args)
                    result = execute_tool(fn.name, args)
                    if on_tool_end:
                        on_tool_end(fn.name, result)
                    if len(result) > self.MAX_TOOL_RESULT:
                        result = result[:self.MAX_TOOL_RESULT] + "\n... (truncated)"
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                text = msg.content or ""
                self._messages.append({"role": "assistant", "content": text})
                return text

        return "Max tool turns reached."

    # ── Gemini (Google AI — API key) ──────────────────

    def _chat_gemini(self, user_input, on_tool_start, on_tool_end, on_text) -> str:
        """Gemini chat with function calling via google-genai SDK."""
        # Simple Gemini history truncation — keep last 30 entries
        if len(self._gemini_history) > 40:
            self._gemini_history = self._gemini_history[-30:]
            if on_text:
                on_text("\n⚡ Gemini context trimmed (keeping last 30 turns)\n")
        try:
            from google.genai import types

            # Build tool declarations
            fn_decls = []
            for tool in TOOLS:
                props = {}
                required = tool["input_schema"].get("required", [])
                for pname, pdef in tool["input_schema"].get("properties", {}).items():
                    ptype = pdef.get("type", "string").upper()
                    props[pname] = types.Schema(
                        type=ptype,
                        description=pdef.get("description", ""),
                    )
                fn_decls.append(types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=types.Schema(
                        type="OBJECT",
                        properties=props,
                        required=required,
                    ),
                ))

            gemini_tools = [types.Tool(function_declarations=fn_decls)]

            # Append new user message to persistent history
            self._gemini_history.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_input)],
            ))
            # Work with a copy so tool-call turns are included
            contents = list(self._gemini_history)

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=gemini_tools,
                max_output_tokens=MAX_TOKENS,
            )

            for turn in range(self._max_turns):
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )

                # Track tokens
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    self._total_input_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                    self._total_output_tokens += getattr(response.usage_metadata, "candidates_token_count", 0)

                # Check for function calls
                fn_calls = []
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fn_calls.append(part.function_call)
                    elif hasattr(part, "text") and part.text:
                        text_parts.append(part.text)

                if text_parts and on_text:
                    on_text("\n".join(text_parts))

                if not fn_calls:
                    # Save assistant response to persistent history
                    self._gemini_history.append(response.candidates[0].content)
                    return "\n".join(text_parts)

                # Execute function calls
                contents.append(response.candidates[0].content)
                fn_response_parts = []
                for fc in fn_calls:
                    args = dict(fc.args) if fc.args else {}
                    if on_tool_start:
                        on_tool_start(fc.name, args)
                    result = execute_tool(fc.name, args)
                    if on_tool_end:
                        on_tool_end(fc.name, result)
                    fn_response_parts.append(types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result},
                    ))

                contents.append(types.Content(
                    role="user",
                    parts=fn_response_parts,
                ))

            # Save final state of conversation to persistent history
            self._gemini_history = contents
            return "Max tool turns reached."

        except ImportError:
            return "ERROR: google-genai not installed. Run: pip install google-genai"
        except Exception as e:
            return f"Gemini API Error: {e}"

    def reset(self):
        """Clear conversation history."""
        self._messages = []
        self._gemini_history = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
