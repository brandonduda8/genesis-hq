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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Read-only Genesis Creatrix Linux audit (no sudo/network).')
    p.add_argument('--out', default='./creatrix-evidence', help='Where to write sanitized JSON and Markdown')
    p.add_argument('--label', default='unverified-linux-runtime', help='Operator-supplied device label, not proof')
    p.add_argument('--json-stdout', action='store_true', help='Print sanitized JSON to stdout')
    a = p.parse_args(argv)
    r = collect(a.label)
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    report = json.dumps(r, indent=2, sort_keys=True) + '\n'
    md = render(r)
    (d / 'CREATRIX_AUDIT.json').write_text(report, encoding='utf-8')
    (d / 'CREATRIX_AUDIT.md').write_text(md, encoding='utf-8')
    digest = hashlib.sha256(report.encode()).hexdigest()
    (d / 'SHA256.txt').write_text(digest + '  CREATRIX_AUDIT.json\n', encoding='ascii')
    if a.json_stdout:
        print(report)
    else:
        print(f'CREATRIX_LOCAL_AUDIT_WRITTEN={d} SHA256={digest} admission={r["admission_plan"]["state"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
