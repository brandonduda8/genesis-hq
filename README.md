# Genesis HQ

The cloud headquarters for the Genesis engineering team. One tap launches a
fully-provisioned 4-core dev box: the worker bridge (Claude / Codex / Gemini
lanes), all three agent CLIs, Docker, and optional Tailscale join so Zane can
SSH straight in.

## Launch

**On your phone:** open this repo on github.com → green **Code** button →
**Codespaces** tab → **Create codespace on main**. The box builds itself
(`provision/setup.sh` runs automatically).

Or via CLI: `gh codespace create -r brandonduda8/genesis-hq -m standardLinux32gb`

## One-time taps (inside the codespace terminal)

1. `claude` then `/login` — Claude Pro OAuth
2. `codex login` — approve on your phone with your ChatGPT account
3. `export GEMINI_API_KEY=...` — your Gemini key (or save it as a Codespaces
   secret so it survives rebuilds)

## Letting Zane in

1. Generate a Tailscale auth key (reusable): https://login.tailscale.com/admin/settings/keys
2. Add it as a Codespaces secret named `TAILSCALE_AUTHKEY`
   (github.com → Settings → Codespaces → New secret)
3. Rebuild the codespace. It joins the tailnet as `genesis-hq` and Zane can
   SSH in and run the worker bridge here.

## Honest limits (free tier)

- **4-core box ≈ 30 hours/month**, then it pauses until next month. 2-core
  would stretch to 60h but this is the "strongest" setting.
- **No GPU.** Heavy training still goes to Kaggle.
- **15 GB storage.** Big checkouts live and die here; the repos are the
  source of truth.
- No surprise billing: the account budget stays $0.

## Dragon OS

HQ boots **Dragon OS** — the operating system for all workers: one work-order
protocol, one dispatcher, one set of laws, on every box. See [DRAGON_OS.md](DRAGON_OS.md).

## What's inside

- `bin/worker-bridge.sh` — unified dispatcher: `probe` / `run <lane> <wo-file>`
- `bin/team-claude.sh` — Claude Code runner (Pro OAuth)
- `bin/team-codex.sh` — ChatGPT/Codex runner (read-only sandbox default)
- `bin/team-gemini.sh` — Gemini CLI runner
- `provision/setup.sh` — the provisioner (idempotent, re-runnable)
- `.devcontainer/devcontainer.json` — the box definition
