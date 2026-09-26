# Dragon OS

**The operating system for Brandon's workers.**

One OS, every machine. Dragon OS boots the same way on this HQ codespace,
on the home server, and on the Oracle VM when it lands: same work-order
protocol, same worker lanes, same laws. A worker never cares which box it's
on — it reads the inbox, does the work, writes the outbox, and the foreman
(Zane) audits everything before it counts.

## How it works

```
boot.sh      →  system init: verifies tools, lanes, tailnet, docker
dragon       →  the CLI: status | tools | workers | boot | laws
inbox/       →  work orders land here (one file = one mission)
outbox/      →  finished work lands here (audited before it counts)
LAWS.md      →  the constitution — autonomy WITH boundaries
TOOLBELT.md  →  every tool on the box and what it's for
```

## The vision

Power without chaos. Every worker on the team — Claude the Architect,
Codex the Challenger, Gemini the Scout, Qwen the Alternate, Grok/Thanos
when keyed — speaks the same protocol: `worker-bridge.sh run <lane> <wo>`.
Dragon OS is the ground they all stand on. The strongest version of it is
not the box — it's the discipline: one mission at a time, audited results,
zero dollars burned, and the empire compounding every single day.

**If we ain't improving we ain't moving.**
