#!/usr/bin/env bash
# GENESIS CREATRIX: one-paste read-only Linux audit + user-level bounded-job launcher.
# No root, package install, remote network, firmware change or service modification.
set -euo pipefail
if [ "$(id -u)" -eq 0 ]; then
  printf 'CREATRIX_STOP: use your normal Chromebook Linux user, not root.\n' >&2
  exit 3
fi
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
root="$HOME/Genesis-Creatrix/reports"
output="$root/$stamp"
num=0
while [ -e "$output" ]; do num=$((num+1)); output="$root/$stamp-$num"; done
mkdir -p "$output"
report="$output/CREATRIX_FIRST_PASS.txt"
{
  printf 'GENESIS_CREATRIX_READONLY_V1\n'
  date -u '+UTC=%Y-%m-%dT%H:%M:%SZ'
  printf 'SOURCE=actual current Linux user runtime (ChromeOS host not audited)\n'
  if [ -r /etc/os-release ]; then grep -E '^(PRETTY_NAME|ID|VERSION_ID)=' /etc/os-release || true; fi
  printf 'KERNEL='; uname -r
  printf 'ARCH='; uname -m
  printf 'LOGICAL_CPUS='; getconf _NPROCESSORS_ONLN 2>/dev/null || true
  printf '\nLINUX_GUEST_MEMORY_KIB\n'
  grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree|SwapCached):' /proc/meminfo || true
  printf '\nLINUX_CGROUP_MEMORY\n'
  for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events; do
    if [ -r "$f" ]; then printf '%s\n' "$(basename "$f")"; cat "$f"; fi
  done
  if [ -r /proc/pressure/memory ]; then printf '\nMEMORY_PSI\n'; cat /proc/pressure/memory; fi
  printf '\nGUEST_ROOT_DISK_KIB\n'
  df -Pk / 2>/dev/null | awk 'NR==2 {printf "total=%s free=%s\n",$2,$4}' || true
  printf '\nTOP_PROCESS_NAMES_AND_RSS_KIB\n'
  ps -eo comm,rss --sort=-rss 2>/dev/null | head -n 16 || true
  printf '\nEXISTING_TOOLS\n'
  for x in python3 git node npm docker podman ssh tailscale netbird ollama systemd-run zramctl; do
    if command -v "$x" >/dev/null 2>&1; then printf '%s=present\n' "$x"; else printf '%s=absent\n' "$x"; fi
  done
  printf '\nREAD_ONLY_SERVICE_STATES\n'
  if command -v systemctl >/dev/null 2>&1; then
    for x in ssh tailscaled netbird docker; do
      printf '%s=' "$x"; systemctl is-active "$x" 2>/dev/null || true
    done
    printf 'penguin-bridge.user='; systemctl --user is-active penguin-bridge.service 2>/dev/null || true
  fi
  printf '\nEND_OF_READ_ONLY_AUDIT\n'
} > "$report"
chmod 600 "$report"
guard="$HOME/.local/bin/genesis-creatrix-run"
mkdir -p "$HOME/.local/bin"
if [ ! -e "$guard" ] && [ ! -L "$guard" ]; then
  cat > "$guard" <<'PY'
#!/usr/bin/env python3
"""Only run explicit jobs under a user-level RAM/CPU cgroup. No auto-starts."""
import os, shutil, subprocess, sys
M=1024*1024

def memory():
    data={}
    with open('/proc/meminfo',encoding='ascii') as f:
        for line in f:
            label,_,other=line.partition(':')
            if label in ('MemTotal','MemAvailable'):
                data[label]=int(other.split()[0])*1024
    try:
        maximum=open('/sys/fs/cgroup/memory.max',encoding='ascii').read().strip()
        current=open('/sys/fs/cgroup/memory.current',encoding='ascii').read().strip()
        if maximum.isdecimal() and current.isdecimal():
            data['MemTotal']=min(data.get('MemTotal',int(maximum)),int(maximum))
            data['MemAvailable']=min(data.get('MemAvailable',int(maximum)),max(0,int(maximum)-int(current)))
    except (OSError,ValueError):
        pass
    return data

def main(args):
    if os.geteuid()==0:
        print('Cannot run Creatrix jobs as root.');return 2
    preview=bool(args and args[0]=='--preview')
    if preview:args=args[1:]
    if args and args[0]=='--': args=args[1:]
    if not args and not preview:
        print('Use: genesis-creatrix-run [--preview] -- program [arguments]');return 2
    mem=memory()
    reserve=max(750*M,int(mem.get('MemTotal',0)*.28))
    cap=min(900*M,int((mem.get('MemAvailable',0)-reserve)*.6))
    if cap<320*M:
        print('BLOCKED_MEMORY_PRESSURE: offload heavy work to S1.');return 3
    cap_mb=cap//M
    print(f'Creatrix job cap {cap_mb}MiB; protected reserve {reserve//M}MiB',flush=True)
    if preview:
        print('PREVIEW_ONLY: no job launched');return 0
    if not shutil.which('systemd-run'):
        print('BLOCKED: systemd user scope unavailable, no unbounded fallback');return 4
    command=['systemd-run','--user','--scope','--quiet','-p',f'MemoryMax={cap_mb}M',
             '-p',f'MemoryHigh={max(256,int(cap_mb*.88))}M','-p','CPUQuota=150%','--',*args]
    return subprocess.call(command)

if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
PY
  chmod 700 "$guard"
  guard_status=CREATED_USER_GUARD
else
  guard_status=EXISTING_GUARD_PRESERVED
fi
printf '\nGENESIS CREATRIX FIRST PASS DONE\n'
printf 'REPORT=%s\nGUARD=%s\n' "$report" "$guard_status"
printf 'No packages installed, no system services restarted, no networks changed.\n'
printf 'For detailed analysis, show the output below (never include secrets):\n'
cat "$report"
