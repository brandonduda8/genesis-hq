# The Empire Blueprint v1.0

**Every service a business needs, recreated at $0 — each held to a 10/10
standard that never stops rising.**

The rule: we do not rent what we can build. Every paid service below has a
free recreation that is *better* — because it's ours, it compounds, and no
vendor can take it away. When money comes, we buy back *time*, not capability.

## The audit protocol (how anything reaches 10/10)

1. **A worker builds it** — any lane, one mission at a time.
2. **Zane audits it** — tests, diffs, honesty. Nothing counts until verified.
3. **Brandon taps it** — his word is the only ship button.
4. **The standard is written down** — what 10/10 means for that service,
   in this file, versioned. If it isn't written, it isn't the standard.

## The raising ritual

On the first of every month, every LIVE service is re-scored 1–10 against
its written standard. Anything below 10 gets a work order. The standard
itself is re-read: if the bar got easy, the bar moves up. The version number
bumps (v1.0 → v1.1) and the change is logged at the bottom of this file.
**Greatness is a direction, not a destination.**

---

## COMPUTE & BUILD

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Heavy dev VM | $50–200/mo cloud box | **Genesis HQ** (Codespaces 4-core, free 30h/mo) + this always-on box | Boots Dragon OS itself; `dragon status` all green; any lane dispatchable | READY — quota resets Oct 1 |
| 24/7 home base | $20/mo VPS | This sandbox: keepalives, crons, proxies | 19+/20 healthy on dashboard; self-heals in <5 min | LIVE |
| Permanent cloud VM | $30/mo | Oracle A1 ARM (4 OCPU/24GB, Always Free) | Docker builds run here; HQ workloads migrate over | QUEUED — retry cron every 2h |
| GPU training | $300+/mo | Kaggle 30 GPU-hrs/week (T4/P100) | One GPU at a time; every run banked on his tap; adapters harvested clean | LIVE |
| CI/CD | $40/mo runners | GitHub Actions free tier | Every PR green before merge; JVM + unit gates | LIVE (player PR proof) |
| Containers | paid registry | Docker on HQ/penguin + GHCR free | Any service ships as an image; reproducible builds | READY |

## DATA & STORAGE

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Postgres | $25/mo managed | Neon free tier (live, tunneled) | Virtual keys + spend tracking; migrations clean | LIVE |
| File/CDN | $20/mo S3+CDN | Cloudflare R2 free tier / GH releases | Every artifact has a permanent link; nothing in /tmp | QUEUED |
| Secrets | $40/mo vault | Secure Vault + Codespaces secrets (0600 files) | No raw secret ever in chat, repo, or log | LIVE |

## AI & AGENTS

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Coding agent | $20–200/mo seats | **Worker bridge**: Claude (Pro) + Codex + Gemini + Qwen + goose, $0 marginal | `probe` all READY; one-lock dispatch; every result audited | LIVE (5 lanes) |
| Frontier API | $100+/mo tokens | Groq free tier (gpt-oss-120b) + Gemini free + z.ai flash | Strongest free model primary; hot backups on 429 | LIVE |
| Custom brains | $500/mo fine-tune APIs | Kaggle LoRA pipeline (perfect-build queue) | Loss curves honest; readiness eval before any claim | LIVE (queue running) |
| Agent OS | $200/mo frameworks | **Dragon OS** — one protocol, every box | `dragon boot` green on any machine; laws enforced | LIVE (repo) |

## MONEY

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Invoicing | $30/mo SaaS | **Apex Invoicing** (live, auth-enforced) | "Invoice X for $Y" → sent in one message | LIVE |
| Payments | 3% + terminals | Stripe (his tap) / Cash App + PayPal manual rails | Every dollar lands in the ledger | READY — Stripe key = his tap |
| Job pipeline | $50/mo boards | Sprint system + job swarm (walkable-first) | 50-target queue; every submit confirmed same day | LIVE |
| Outreach CRM | $100/mo | Audit outreach engine + ledger | Every prospect tracked; follow-ups armed, never spammy | LIVE |
| Analytics | $30/mo | Plausible self-hosted (needs Oracle VM) | Real numbers, no vendor lock | PARKED — needs the VM |

## MUSIC & BRAND

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Distribution | $25/yr DistroKid | SoundOn $0 (no lock-in decision pending) | Catalog live only after HIS voice pick | READY — his call |
| Music player | $10/mo apps | **Genesis Player** (Tidal-grade, golden) | 10/10 = his "I need to be amazed" bar, nothing ships cold | BUILDING — PR #1 open |
| Discovery | $12/mo A&R tools | Apollo hunts (Audius + live catalog) | Daily finds, one taste-fit line each, unheard sounds only | LIVE |
| Content pipeline | $50/mo schedulers | TikTok machine + Shorts prep | Every short tracked goal→post→paid | BUILDING |
| Design | $20/mo Canva | Olivia brand system (charcoal→ember→gold) | Every visual amazons before it ships | LIVE (bar set) |

## REACH & OPS

| Service | The paid version | Our $0 recreation | 10/10 standard | Status |
|---|---|---|---|---|
| Uptime watch | $30/mo | Health dashboard (5-min probes) | 0 failed; degraded explained in one line | LIVE |
| SMS/voice | $40/mo | Voice bridge + Twilio (his tap) | Ember talks on his real phone call | READY — mic + API taps |
| Email infra | $20/mo | Gmail + autopilot triage | Inbox zero by machine; his tap on every send | LIVE |

---

## Scoreboard v1.0 (2026-09-26)

- LIVE: 14 · READY (needs his tap): 7 · BUILDING: 3 · QUEUED: 3 · PARKED: 1
- The empire currently recreates roughly **$1,500+/mo** of paid services at $0.

## Changelog

- **v1.0 (2026-09-26)** — First full catalog. 28 services mapped. Standard set: 10/10 or it gets a work order.
