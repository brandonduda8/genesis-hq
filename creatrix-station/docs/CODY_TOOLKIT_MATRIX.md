# Cody Factory toolkit — real presence vs proposed placement

| Component | Best host | Practical value | Evidence needed before ACTIVE |
| --- | --- | --- | --- |
| Creatrix Station + Cody Factory | Penguin | Local dashboard, mission evidence, scaffolds, model-free testing | `creatrix --port 8765`, loopback health and UI |
| `codyctl` + read-only stdio MCP | Penguin / S1 | Tool inventory, scaffold/manifest, bounded synthetic tests | Actual local tests & MCP initialize/tools list |
| OpenCode | Penguin only with measured headroom; otherwise S1 | Real LLM coding agent, text/IDE and MCP | Exact binary/version, working model, permitted task receipt |
| OpenHands | S1 | Sandbox-oriented heavy coding worker | Container/model/identity ready, zero-cost quota, verified run |
| ZeroClaw / nanobot / GenesisClaw | S1 first, Penguin only light | Optional extra workers, NOT auto-installed | Pinned binary, permission and model receipt |
| OpenSSH client + ssh-keygen | Both | Verified remote login, host identity | Trusted S1 host fingerprint, authorized client, login proof |
| NetBird | Existing Penguin; S1 pending | Private mesh | Both peers shown in dashboard and bidirectional application health |
| Tailscale | Existing, unchanged | Backup mesh | Transport evidence, no resets or state deletion |
| rsync | Both | Copies only owner-approved workspaces over verified SSH | Strict host key, targeted paths and dry-run |
| Syncthing | S1 optional | Project synchronization | Scoped shared folder, device approval, conflict/recovery drill |
| Git / worktrees / pre-commit | Both | Isolated project development, version evidence | Initial repository state and tests |
| uv / Ruff / pytest / mypy | Both | Fast Python environments and static checks | Pinned wheels/no unauthorized package writes |
| Node.js / TypeScript / ESLint | S1 preferred | Browser extensions, web apps, UIs | Version and dependency integrity |
| Go / Rust / Cargo | S1 | Agent/MCP tooling | Actual host capacity and source checks |
| Docker / rootless Podman | S1 only initially | OpenHands isolation, tests | Root access controlled, sandbox reviewed, no host socket to worker |
| Ollama / llama.cpp | S1 | Real local model route | Verified model/tool-call support, RAM pressure and no public listener |
| VS Code/Codium / Geany | Penguin | IDE and code editing | RAM measurement, extension audit, no giant plugin ecosystem by default |
| btop / ncdu / zram check | Penguin | Diagnose freezes/disk/pressure | OS support and no forced settings |

Recommended first runtime: **Git + Python + read-only MCP on Penguin, OpenCode + OpenHands on S1 after verified SSH access.** More installed packages is not an objective by itself. The objective is stable throughput with independent evidence.

Security: no `curl | sh`, no agent root, no shared private SSH key, no public Ollama/MCP/SSH, no blanket Delete or Powerwash. Fedora migration is optional and separately owner-approved.

References: https://opencode.ai/docs/ ; https://docs.opencode.ai/docs/mcp-servers/ ; https://docs.opencode.ai/docs/permissions/ ; https://docs.openhands.dev/ ; https://docs.mrchromebox.tech/docs/supported-devices .
