#!/usr/bin/env python3
"""Read-only and privacy-minimizing Linux guest audit for Genesis Creatrix.

This is not a ChromeOS host or firmware audit. It executes only local
read-only probes and writes reports into the caller-selected output dir.
No sudo, network, service starts, package installs, secrets, or SSH commands.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import html
import platform
import re
import shutil
import subprocess
import sys

APP_VERSION = '0.1.0'
EXPECTED_BOARD = 'ELEMI'
TARGET_BINARIES = ('python3', 'git', 'node', 'npm', 'go', 'rustc', 'cargo', 'docker', 'podman',
                   'ssh', 'ss', 'tailscale', 'netbird', 'ollama', 'code', 'codium',
                   'flatpak', 'lspci', 'zramctl', 'systemctl')
SERVICES = ('ssh', 'sshd', 'tailscaled', 'netbird', 'docker', 'podman', 'fail2ban')
INTERESTING_PORTS = {22, 80, 443, 4001, 8080, 8081, 8443, 11434, 18789, 18790}


def read_text(path: str, max_chars: int = 20000) -> str:
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')[:max_chars]
    except (OSError, ValueError):
        return ''


def call(args: list[str], timeout: float = 4.0) -> str:
    if not args or shutil.which(args[0]) is None:
        return ''
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                check=False, stdin=subprocess.DEVNULL,
                                env={'PATH': os.defpath, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ''
    return result.stdout[:64000]


def meminfo(raw: str) -> dict:
    found = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'([A-Za-z_()]+):\s*(\d+)\s*(kB)?', line.strip())
        if match and match.group(1) in ('MemTotal', 'MemAvailable', 'MemFree', 'SwapTotal',
                                         'SwapFree', 'SwapCached', 'Shmem', 'Cached', 'Buffers', 'SReclaimable'):
            found[match.group(1)] = int(match.group(2)) * (1024 if match.group(3) else 1)
    return found


def cgroup_bytes(raw: str):
    s = raw.strip()
    if s.isdecimal():
        return int(s)
    return None


def cgroup_events(raw: str) -> dict:
    allowed = ('low', 'high', 'max', 'oom', 'oom_kill', 'oom_group_kill')
    items = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in allowed and parts[1].isdecimal():
            items[parts[0]] = int(parts[1])
    return items


def pressure(raw: str):
    out = {}
    for line in raw.splitlines():
        bits = line.split()
        if not bits or bits[0] not in ('some', 'full'):
            continue
        vals = {}
        for item in bits[1:]:
            if '=' not in item:
                continue
            k, v = item.split('=', 1)
            if k in ('avg10', 'avg60', 'avg300'):
                try:
                    vals[k] = float(v)
                except ValueError:
                    pass
        out[bits[0]] = vals
    return out


def cpu_name(raw: str):
    for line in raw.splitlines():
        if line.startswith('model name') and ':' in line:
            return line.split(':', 1)[1].strip()[:120]
    return 'UNKNOWN'


def os_release(raw: str):
    values = {}
    for line in raw.splitlines():
        if '=' not in line or line.startswith('#'):
            continue
        k, v = line.split('=', 1)
        if k in ('ID', 'VERSION_ID', 'PRETTY_NAME'):
            values[k] = v.strip().strip('"')[:120]
    return values


def cpu_flags(raw: str) -> list[str]:
    allowed = ('avx', 'avx2', 'avx512f', 'fma', 'sse4_2', 'vmx', 'hypervisor')
    for line in raw.splitlines():
        if line.startswith('flags') and ':' in line:
            bits = set(line.split(':', 1)[1].split())
            return [item for item in allowed if item in bits]
    return []


def disk(path: str):
    try:
        x = shutil.disk_usage(path)
        return {'total_bytes': x.total, 'free_bytes': x.free, 'used_bytes': x.used}
    except OSError:
        return {}


def process_rss(raw: str) -> list[dict]:
    procs = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[-1].isdecimal():
            continue
        name = parts[0][:60]
        # Only command name, never arguments/environment/user/pid.
        if name.startswith('['):
            continue
        procs.append({'process': name, 'rss_kib': int(parts[-1])})
    return sorted(procs, key=lambda x: x['rss_kib'], reverse=True)[:16]


def swap_devices(raw: str) -> list[dict]:
    devices = []
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        # Expose only zram vs physical/virtual file category; no arbitrary paths.
        kind = 'ZRAM' if fields[0].startswith('/dev/zram') else ('SWAP_FILE' if '/' in fields[0] else 'OTHER')
        devices.append({'kind': kind, 'size': fields[1][:24], 'used': fields[2][:24], 'priority': fields[3][:12]})
    return devices[:8]


def listening_ports(raw: str) -> list[int]:
    hits = set()
    for line in raw.splitlines():
        for token in line.split():
            if ':' not in token:
                continue
            tail = token.rsplit(':', 1)[-1]
            if tail.isdecimal() and int(tail) in INTERESTING_PORTS:
                hits.add(int(tail))
    return sorted(hits)


def capacity_plan(mem: dict, cgroup_max: int | None, peak_process_kib: int = 0) -> dict:
    total = mem.get('MemTotal', 0)
    available = mem.get('MemAvailable', 0)
    effective_total = min(total, cgroup_max) if cgroup_max and total else total
    # A conservative admission heuristic; not a kernel-enforced limit.
    reserve = max(600 * 1024**2, int(effective_total * 0.28)) if effective_total else 0
    if not total or not available:
        state = 'UNKNOWN'
        worker_budget = 0
    elif available <= reserve:
        state = 'CRITICAL'
        worker_budget = 0
    elif available < reserve + 600 * 1024**2:
        state = 'CONSTRAINED'
        worker_budget = 0
    else:
        state = 'AVAILABLE_FOR_ONE_BOUNDED_WORKER'
        worker_budget = min(700 * 1024**2, int((available - reserve) * 0.55))
    return {
        'state': state,
        'reserve_bytes': reserve,
        'proposed_worker_rss_cap_bytes': worker_budget,
        'one_heavy_worker_max': True,
        'peak_single_process_rss_kib': peak_process_kib,
        'note': 'Planning only; no resource changes applied. Crostini memory is not physical RAM.'
    }


def collect(label: str = 'unverified-host') -> dict:
    rawmem = read_text('/proc/meminfo')
    mem = meminfo(rawmem)
    rawprocs = call(['ps', '-eo', 'comm,rss', '--no-headers'])
    top = process_rss(rawprocs)
    cgroup = cgroup_bytes(read_text('/sys/fs/cgroup/memory.max'))
    osdata = os_release(read_text('/etc/os-release'))
    binaries = {name: bool(shutil.which(name)) for name in TARGET_BINARIES}
    service_states = {}
    if binaries.get('systemctl'):
        for s in SERVICES:
            # 'is-active' checks only state; no journal or secret-bearing arguments.
            state = call(['systemctl', 'is-active', s]).strip()[:40]
            service_states[s] = state if state in ('active', 'inactive', 'failed', 'activating', 'deactivating') else 'unknown'
    out = {
        'schema': 'genesis-creatrix-audit/1',
        'audit_version': APP_VERSION,
        'collected_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'reported_device_label': label,
        'identity_verified': False,
        'scope': 'CURRENT_LINUX_RUNTIME_ONLY; NOT_CHROMEOS_HOST',
        'hardware_board_live': 'UNKNOWN_FROM_LINUX_GUEST',
        'hardware_board_prior_user_report': EXPECTED_BOARD,
        'kernel': platform.release(),
        'architecture': platform.machine(),
        'os': osdata,
        'cpu': {'model': cpu_name(read_text('/proc/cpuinfo')), 'logical_processors': os.cpu_count(),
                'instruction_sets': cpu_flags(read_text('/proc/cpuinfo'))},
        'memory': mem,
        'cgroup': {
            'memory_limit_bytes': cgroup,
            'memory_current_bytes': cgroup_bytes(read_text('/sys/fs/cgroup/memory.current')),
            'memory_events': cgroup_events(read_text('/sys/fs/cgroup/memory.events')),
            'memory_pressure': pressure(read_text('/proc/pressure/memory')),
        },
        'swap_devices': swap_devices(call(['swapon', '--noheadings', '--show=NAME,SIZE,USED,PRIO'])),
        'disk_guest_root': disk('/'),
        'disk_guest_home': disk(str(Path.home())),
        'tools_available': binaries,
        'services': service_states,
        'top_processes_rss_only': top,
        'ports_listening_selected_only': listening_ports(call(['ss', '-H', '-ltn'])),
        'gpu': {'lspci_vga_names': gpu_names(call(['lspci', '-nn'])) if binaries.get('lspci') else [],
                'physical_gpu_access': 'UNVERIFIED_IN_GUEST'},
        'battery': {'capacity_pct_if_exposed': read_battery()},
        'network': {'not_probed': True, 'note': 'No outgoing connections or IP addresses collected'},
        'safety': {'sudo_used': False, 'configuration_modified': False,
                   'secrets_or_shell_arguments_collected': False,
                   'remote_endpoint_contacted': False}
    }
    out['admission_plan'] = capacity_plan(mem, cgroup, max((p['rss_kib'] for p in top), default=0))
    return out


def gpu_names(lspci_raw: str) -> list[str]:
    result = []
    for line in lspci_raw.splitlines():
        if any(x in line for x in ('VGA compatible controller', '3D controller', 'Display controller')):
            # Device name only, not PCI address or UUID.
            result.append(line.split(': ', 1)[-1][:140])
    return result[:6]


def read_battery() -> int | None:
    for path in Path('/sys/class/power_supply').glob('BAT*/capacity'):
        val = read_text(str(path)).strip()
        if val.isdecimal() and 0 <= int(val) <= 100:
            return int(val)
    return None


def gib(value: int | None):
    return 'unknown' if value is None else f'{value / (1024**3):.2f} GiB'


def render(report: dict) -> str:
    mem = report['memory']; cg = report['cgroup']; plan = report['admission_plan']; disk_root = report['disk_guest_root']
    row = [
        '# Genesis Creatrix: Read-only Audit', '',
        f"- Date UTC: `{report['collected_utc']}`",
        f"- User-supplied device label: `{report['reported_device_label']}` (NOT independently verified)",
        f"- Audited scope: **{report['scope']}**",
        f"- Earlier board report: **{report['hardware_board_prior_user_report']}** (not observable from Crostini)",
        f"- Linux OS: {report['os'].get('PRETTY_NAME', 'unknown')}",
        f"- Kernel: `{report['kernel']}`", '',
        '## CPU / Memory / Storage',
        f"- CPU: {report['cpu']['model']} / {report['cpu']['logical_processors']} visible logical processors",
        f"- Guest MemTotal: {gib(mem.get('MemTotal'))}; MemAvailable: {gib(mem.get('MemAvailable'))}",
        f"- Guest SwapTotal: {gib(mem.get('SwapTotal'))}; SwapFree: {gib(mem.get('SwapFree'))}",
        f"- Container cgroup memory limit: {gib(cg.get('memory_limit_bytes'))}",
        f"- Guest swap devices (no paths): {report.get('swap_devices', [])}",
        f"- Memory pressure avg10: {cg.get('memory_pressure', {}).get('some', {}).get('avg10', 'unknown')}",
        f"- OOM kill count (cgroup): {cg.get('memory_events', {}).get('oom_kill', 'unknown')}",
        f"- Guest root total/free: {gib(disk_root.get('total_bytes'))} / {gib(disk_root.get('free_bytes'))}",
        '- ChromeOS host storage: UNKNOWN (guest disk is not the host disk)', '',
        '## Resource governor proposal (NOT applied)',
        f"- Admission state: **{plan['state']}**",
        f"- Recommended memory reserve: {gib(plan['reserve_bytes'])}",
        f"- Heavy-worker RSS budget: {gib(plan['proposed_worker_rss_cap_bytes'])}",
        '- Background heavyweight workers: at most 1, preferably moved to Genesis S1.', '',
        '## Observed tools (presence only; not health)',
    ]
    row.extend(f"- `{name}`: {'present' if exists else 'absent'}" for name, exists in report['tools_available'].items())
    row.extend(['', '## Selected service states'])
    row.extend(f"- `{name}`: `{state}`" for name, state in report['services'].items())
    row.extend(['', f"Selected listening port numbers (no IPs): {report['ports_listening_selected_only']}", '',
                '## Largest processes by RSS (names only)', ''])
    row.extend(f"- `{p['process']}`: {p['rss_kib'] / 1024:.1f} MiB" for p in report['top_processes_rss_only'][:12])
    row.extend(['', '## Hard limitations',
                '- A Linux guest audit cannot inspect the ChromeOS firmware, physical RAM slots, ChromeOS browser or full ChromeOS disk.',
                '- Device identity and SSH access are not proven by this output.',
                '- No services were stopped, no network requests made, no packages installed, and no privileges escalated.',
                '- An operator must verify the board/HWID and backup/recovery before any native Fedora firmware work.', ''])
    return '\n'.join(row)



import html


def e(value):
    return html.escape(str(value), quote=True)


def html_gib(n):
    if not isinstance(n, (int, float)):
        return 'Unknown'
    return f'{n/(1024**3):.2f} GiB'


def html_pct(part, total):
    if not isinstance(part, (int,float)) or not isinstance(total,(int,float)) or total<=0:
        return 0
    return max(0,min(100,round(part/total*100)))


def build(report: dict) -> str:
    mem=report.get('memory',{})
    cgroup=report.get('cgroup',{})
    disks=report.get('disk_guest_root',{})
    adm=report.get('admission_plan',{})
    cpu=report.get('cpu',{})
    rss=report.get('top_processes_rss_only',[])
    mem_pct=html_pct(mem.get('MemTotal',0)-mem.get('MemAvailable',0),mem.get('MemTotal',0))
    disk_pct=html_pct(disks.get('used_bytes',0),disks.get('total_bytes',0))
    top=''.join(f'<tr><td>{e(p.get("process","unknown"))}</td><td>{p.get("rss_kib",0)/1024:.1f} MiB</td></tr>' for p in rss[:10])
    if not top: top='<tr><td colspan="2">No process data</td></tr>'
    tools=report.get('tools_available',{})
    tool_items=''.join(f'<span class="chip {"ok" if ok else "off"}">{e(k)}: {"detected" if ok else "absent"}</span>' for k,ok in sorted(tools.items()))
    services=report.get('services',{})
    service_items=''.join(f'<span class="chip {"ok" if v=="active" else "off"}">{e(k)}: {e(v)}</span>' for k,v in sorted(services.items()))
    state=adm.get('state','UNKNOWN')
    if state=='CRITICAL': advice='Memory is tight: stop competing heavyweight processes after review. Do not launch more agents locally.'
    elif state=='CONSTRAINED': advice='Keep one small interactive worker at most; route heavy builds and AI to S1.'
    elif state=='AVAILABLE_FOR_ONE_BOUNDED_WORKER': advice='There is room for one bounded job, but reserve enough memory for ChromeOS and the bridge.'
    else: advice='More evidence is required before scheduling work.'
    pressure=cgroup.get('memory_pressure',{}).get('some',{}).get('avg10','Unknown')
    swap=', '.join(x.get('kind','UNKNOWN') for x in report.get('swap_devices',[])) or 'Not detected'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GENESIS CREATRIX / Host Health</title><style>
:root{{--bg:#080b15;--panel:#131a2c;--panel2:#171e32;--fg:#eff4ff;--soft:#9eadd0;--edge:#303957;--violet:#ae8bff;--mint:#78e3c3;--gold:#ffd286}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.55 system-ui,-apple-system,sans-serif;color:var(--fg);background:radial-gradient(ellipse at 15% 0%,#2a2049 0%,#0a1020 34%,var(--bg) 80%)}}
main{{max-width:1090px;margin:auto;padding:34px 20px 72px}}h1{{font-size:clamp(2rem,6vw,3.8rem);line-height:1.05;letter-spacing:-.04em;margin:10px 0}}h2{{font-size:1.06rem;margin:0 0 15px}}p{{margin:.3rem 0 1rem}}.eyebrow{{font-weight:750;letter-spacing:.2em;font-size:.75rem;color:var(--mint)}}.hero{{padding:24px 0 28px}}.muted{{color:var(--soft)}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}.card{{background:linear-gradient(145deg,rgba(27,34,58,.96),rgba(16,22,40,.96));border:1px solid var(--edge);border-radius:17px;padding:19px}}.k{{font-size:.74rem;color:var(--soft);text-transform:uppercase;letter-spacing:.1em}}.value{{font-size:1.85rem;font-weight:760;letter-spacing:-.035em;margin-top:5px}}.value.small{{font-size:1.07rem}}.bar{{height:9px;background:#35405d;border-radius:30px;overflow:hidden;margin:13px 0 0}}.fill{{height:100%;background:linear-gradient(90deg,var(--mint),var(--violet));width:0}}.wide{{grid-column:span 2}}.full{{grid-column:span 4}}.tag{{display:inline-block;border-radius:100px;border:1px solid #65518a;color:#dbc9ff;padding:5px 11px;font-size:.83rem}}table{{width:100%;border-collapse:collapse}}td{{padding:8px 0;border-bottom:1px solid var(--edge)}}td:last-child{{text-align:right;font-variant-numeric:tabular-nums}}.chip{{display:inline-block;padding:5px 9px;margin:3px 3px 3px 0;border-radius:9px;border:1px solid var(--edge);font-size:.75rem}}.chip.ok{{border-color:#267a64;color:#9cecd0}}.chip.off{{color:var(--soft)}}.step{{display:grid;grid-template-columns:32px 1fr;gap:7px;margin-top:12px}}.num{{color:var(--violet);font-weight:750}}footer{{border-top:1px solid var(--edge);margin-top:27px;padding-top:18px;font-size:.83rem;color:var(--soft)}}@media(max-width:760px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.wide{{grid-column:span 2}}.full{{grid-column:span 2}}}}@media(max-width:450px){{.grid{{grid-template-columns:1fr}}.wide,.full{{grid-column:span 1}}}}
</style></head><body><main>
<header class="hero"><div class="eyebrow">GENESIS / CREATRIX ENGINEERING STATION</div><h1>Make a small machine<br><span style="color:var(--violet)">do extraordinary work.</span></h1><p class="muted">Real Linux resource evidence. No fake RAM, no hidden optimization, no host modifications.</p><span class="tag">{e(state)}</span> <span class="tag">{e(report.get('scope','UNKNOWN'))}</span></header>
<div class="grid"><section class="card"><div class="k">Visible Linux memory</div><div class="value">{e(html_gib(mem.get('MemTotal')))}</div><div class="muted">Guest/container, not physical RAM</div><div class="bar"><div class="fill" style="width:{mem_pct}%"></div></div></section>
<section class="card"><div class="k">Available memory</div><div class="value">{e(html_gib(mem.get('MemAvailable')))}</div><div class="muted">For new work at this moment</div></section>
<section class="card"><div class="k">Swap</div><div class="value">{e(html_gib(mem.get('SwapTotal')))}</div><div class="muted">{e(swap)}; not physical RAM</div></section>
<section class="card"><div class="k">Root disk free</div><div class="value">{e(html_gib(disks.get('free_bytes')))}</div><div class="muted">Guest disk only</div><div class="bar"><div class="fill" style="width:{disk_pct}%"></div></div></section>
<section class="card wide"><h2>Compute identity</h2><div class="k">CPU</div><div class="value small">{e(cpu.get('model','UNKNOWN'))}</div><p class="muted">{e(cpu.get('logical_processors','Unknown'))} logical processors · kernel {e(report.get('kernel','?'))}</p><p>Linux: {e(report.get('os',{}).get('PRETTY_NAME','Unknown'))}</p><p class="muted">Instruction sets: {e(', '.join(cpu.get('instruction_sets',[])) or 'Unknown')}</p></section>
<section class="card wide"><h2>Pressure and admission</h2><div class="k">Memory pressure (10 sec)</div><div class="value">{e(pressure)}</div><p class="muted">OOM kills in current cgroup: {e(cgroup.get('memory_events',{}).get('oom_kill','Unknown'))}</p><p>Bounded worker budget: <b>{e(html_gib(adm.get('proposed_worker_rss_cap_bytes')))}</b></p><p class="muted">{e(advice)}</p></section>
<section class="card wide"><h2>Largest guest processes</h2><table><thead><tr><td>Process name</td><td>RSS</td></tr></thead><tbody>{top}</tbody></table></section>
<section class="card wide"><h2>Service presence</h2>{service_items}<h2 style="margin-top:20px">Available local tools</h2>{tool_items}</section>
<section class="card full"><h2>Creatrix upgrade path</h2>
<div class="step"><div class="num">01</div><div>Protect running Tailscale, NetBird, SSH and Penguin bridge. Diagnose causes of freezing before removing services.</div></div>
<div class="step"><div class="num">02</div><div>Use Chrome's Maximum Memory Saver and reduce idle browser tabs/extensions from ChromeOS itself.</div></div>
<div class="step"><div class="num">03</div><div>Run large jobs through the bounded <code>genesis-creatrix-run</code> launcher. Route models and heavy builds to S1 when authenticated.</div></div>
<div class="step"><div class="num">04</div><div>Consider native Fedora 44 LXQt after owner-verified HWID, storage, Wi-Fi/audio/suspend checks, ChromeOS backup and recovery media.</div></div></section></div>
<footer>Collected {e(report.get('collected_utc','UNKNOWN'))}. Labeled host: {e(report.get('reported_device_label','UNKNOWN'))} (operator-reported). Hardware board and ChromeOS host internals not measured from this guest. No secrets, private IPs or process arguments collected.</footer>
</main></body></html>'''


def write_dashboard(report: dict, path: Path):
    path.write_text(build(report), encoding='utf-8')
    return path



GUARD_SOURCE = r'''#!/usr/bin/env python3
"""Run explicitly selected processes in a bounded user scope; no automatic service changes."""
import os
import shutil
import subprocess
import sys

MIB = 1024 * 1024

def _mem():
    d={}
    with open('/proc/meminfo', encoding='ascii') as f:
        for line in f:
            k, _, v = line.partition(':')
            if k in ('MemTotal', 'MemAvailable'):
                d[k] = int(v.split()[0]) * 1024
    try:
        raw=open('/sys/fs/cgroup/memory.max', encoding='ascii').read().strip()
        current=open('/sys/fs/cgroup/memory.current', encoding='ascii').read().strip()
        if raw.isdecimal() and current.isdecimal():
            limit=int(raw); used=int(current)
            d['MemTotal']=min(d.get('MemTotal',limit),limit)
            d['MemAvailable']=min(d.get('MemAvailable',limit),max(0,limit-used))
    except (OSError, ValueError):
        pass
    return d

def main(argv):
    if argv and argv[0] == '--help':
        print('usage: genesis-creatrix-run [--preview] -- <command> [args...]')
        return 0
    preview = bool(argv and argv[0]=='--preview')
    if preview: argv=argv[1:]
    if argv and argv[0]=='--': argv=argv[1:]
    if not argv and not preview:
        print('Choose a single workload. Use --preview to inspect resource budget.')
        return 2
    if os.geteuid() == 0:
        print('Refusing to run as root.')
        return 2
    m = _mem()
    avail=m.get('MemAvailable',0); total=m.get('MemTotal',0)
    reserve=max(750*MIB,int(total*.28))
    budget=min(900*MIB,int((avail-reserve)*.60))
    if budget < 320*MIB:
        print('BLOCKED_MEMORY_PRESSURE: not enough headroom for safe bounded job.')
        print('Offload heavy work to Genesis S1 once authorized, or free memory after reviewing processes.')
        return 3
    budget_mb=budget//MIB
    print(f'CREATRIX_BUDGET: up to {budget_mb}MiB; reserve {reserve//MIB}MiB; user-scope only',flush=True)
    if preview:
        print('DRY_RUN: no workload started')
        return 0
    if shutil.which('systemd-run') is None:
        print('BLOCKED_NO_SYSTEMD_SCOPE: cannot enforce memory cap, refusing uncontrolled launch.')
        return 4
    cmd=['systemd-run','--user','--scope','--quiet','-p',f'MemoryMax={budget_mb}M','-p',f'MemoryHigh={max(256,int(budget_mb*.88))}M',
         '-p','CPUQuota=150%','--',*argv]
    return subprocess.call(cmd,stdin=sys.stdin)

if __name__=='__main__':
    raise SystemExit(main(sys.argv[1:]))
'''


def _create_guard(path: Path) -> str:
    """Only create an unchanged, unique user-owned wrapper. Never overwrite modified work."""
    import stat
    expected=hashlib.sha256(GUARD_SOURCE.encode('utf-8')).hexdigest()
    if path.exists():
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return 'GUARD_NOT_WRITTEN_EXISTING_FILE_DIFFERS'
        return 'GUARD_ALREADY_INSTALLED'
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic create exclusive; no deletion, no sudo, no arbitrary tmp path.
    with path.open('x', encoding='utf-8') as f:
        f.write(GUARD_SOURCE)
    path.chmod(0o700)
    return 'GUARD_INSTALLED_USER_ONLY'


def _write_report_safely(path: Path, text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        f.write(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Genesis Creatrix: inspect and prepare a user-level safe heavy-work launcher.')
    ap.add_argument('--label', default='penguin', help='Operator label only, not independent host verification')
    ap.add_argument('--out', default=None, help='User-owned audit output directory')
    ap.add_argument('--audit-only', action='store_true', help='Read-only audit, no launcher installed')
    ap.add_argument('--report-json', action='store_true', help='Print sanitized JSON output')
    args = ap.parse_args(argv)
    if os.geteuid() == 0:
        print('Refusing to run as root. Use the normal Linux user account.', file=sys.stderr)
        return 3
    root=Path.home()/'Genesis-Creatrix'
    if args.out:
        out=Path(args.out).expanduser().resolve()
        # Never overwrite user files. Allow operator-chosen directories without deleting data.
    else:
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        out=root/'reports'/stamp
        suffix=0
        while out.exists():
            suffix+=1
            out=root/'reports'/f'{stamp}-{suffix}'
    r=collect(args.label)
    raw=json.dumps(r,indent=2,sort_keys=True)+'\n'
    out.mkdir(parents=True,exist_ok=True)
    _write_report_safely(out/'CREATRIX_AUDIT.json',raw)
    _write_report_safely(out/'CREATRIX_AUDIT.md',render(r))
    _write_report_safely(out/'CREATRIX_DASHBOARD.html',build(r))
    _write_report_safely(out/'CREATRIX_SHA256.txt',hashlib.sha256(raw.encode()).hexdigest()+'  CREATRIX_AUDIT.json\n')
    if not args.audit_only:
        guardian = Path.home()/'.local'/'bin'/'genesis-creatrix-run'
        status = _create_guard(guardian)
    else:
        status = 'AUDIT_ONLY_NO_LAUNCHER'
    mem=r['memory']
    print(f'CREATRIX_REPORT={out}')
    print(f'CREATRIX_STATUS={r["admission_plan"]["state"]}')
    print(f'CREATRIX_RAM_VISIBLE_GIB={mem.get("MemTotal",0)/1024**3:.2f}')
    print(f'CREATRIX_RAM_AVAILABLE_GIB={mem.get("MemAvailable",0)/1024**3:.2f}')
    print(f'CREATRIX_SWAP_GIB={mem.get("SwapTotal",0)/1024**3:.2f}')
    print(f'CREATRIX_CGROUP_OOM_KILLS={r["cgroup"]["memory_events"].get("oom_kill","UNKNOWN")}')
    print(f'CREATRIX_SAFETY_GUARD={status}')
    print('CREATRIX_BROWSER_DASHBOARD=' + str(out/'CREATRIX_DASHBOARD.html'))
    print('No sudo, installs, host firmware, VPN, SSH, system services, or user data changes were performed.')
    if args.report_json:
        print(raw)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
