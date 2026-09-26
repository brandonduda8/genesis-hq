# Dragon OS Toolbelt

Everything on the box, and what it's for. Installed automatically by
`provision/setup.sh`; verify anytime with `dragon tools`.

## Languages & runtimes

- **Python 3** — workers, bridges, audits, glue
- **Node.js + npm** — the agent CLIs
- **Docker** — real containers (the home sandbox can't do this; HQ can)
- **Git + GitHub CLI** — the empire's memory

## The workers (agent CLIs)

- **claude** — Claude Code, the Architect. Pro OAuth (`/login`).
- **codex** — ChatGPT/Codex, the Challenger. `codex login`, one tap.
- **gemini** — Gemini CLI, the Scout. Needs `GEMINI_API_KEY`.

## The lanes (API workers, no login)

- **qwen** — qwen3.8-27b via Groq, $0 — `team-qwen.py`
- **goose** — gpt-oss-120b via Groq, $0 — strongest free reasoning
- **gemini-flash** — via LiteLLM gateway, $0
- **grok / thanos** — xAI API, the moment the key lands

## The dispatcher

- **worker-bridge.sh** — `probe` (lane health) / `run <lane> <wo-file>`
  (exclusive lock: one heavy worker at a time)

## The reach

- **Tailscale** — joins the tailnet as `genesis-hq` when `TAILSCALE_AUTHKEY`
  is set, so Zane can SSH straight in and dispatch work here.
- **SOCKS5 / proxy env** — every tool exits through the egress proxy;
  nothing needs direct internet.

## The money layer

- The ten OSS revenue engines (n8n, WordPress care, etc.) run as apps
  **on top of** Dragon OS — the OS is the ground, the engines are the
  crops. They arm only on Brandon's tap.
