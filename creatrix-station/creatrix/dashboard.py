"""Generate a static, offline, user-readable Creatrix dashboard from a sanitized audit.

No remote resources, executable JS, identifying IPs, or device secrets.
"""
from __future__ import annotations
import html
from pathlib import Path


def e(value):
    return html.escape(str(value), quote=True)


def gib(n):
    if not isinstance(n, (int, float)):
        return 'Unknown'
    return f'{n/(1024**3):.2f} GiB'


def pct(part, total):
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
    mem_pct=pct(mem.get('MemTotal',0)-mem.get('MemAvailable',0),mem.get('MemTotal',0))
    disk_pct=pct(disks.get('used_bytes',0),disks.get('total_bytes',0))
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
<div class="grid"><section class="card"><div class="k">Visible Linux memory</div><div class="value">{e(gib(mem.get('MemTotal')))}</div><div class="muted">Guest/container, not physical RAM</div><div class="bar"><div class="fill" style="width:{mem_pct}%"></div></div></section>
<section class="card"><div class="k">Available memory</div><div class="value">{e(gib(mem.get('MemAvailable')))}</div><div class="muted">For new work at this moment</div></section>
<section class="card"><div class="k">Swap</div><div class="value">{e(gib(mem.get('SwapTotal')))}</div><div class="muted">{e(swap)}; not physical RAM</div></section>
<section class="card"><div class="k">Root disk free</div><div class="value">{e(gib(disks.get('free_bytes')))}</div><div class="muted">Guest disk only</div><div class="bar"><div class="fill" style="width:{disk_pct}%"></div></div></section>
<section class="card wide"><h2>Compute identity</h2><div class="k">CPU</div><div class="value small">{e(cpu.get('model','UNKNOWN'))}</div><p class="muted">{e(cpu.get('logical_processors','Unknown'))} logical processors · kernel {e(report.get('kernel','?'))}</p><p>Linux: {e(report.get('os',{}).get('PRETTY_NAME','Unknown'))}</p><p class="muted">Instruction sets: {e(', '.join(cpu.get('instruction_sets',[])) or 'Unknown')}</p></section>
<section class="card wide"><h2>Pressure and admission</h2><div class="k">Memory pressure (10 sec)</div><div class="value">{e(pressure)}</div><p class="muted">OOM kills in current cgroup: {e(cgroup.get('memory_events',{}).get('oom_kill','Unknown'))}</p><p>Bounded worker budget: <b>{e(gib(adm.get('proposed_worker_rss_cap_bytes')))}</b></p><p class="muted">{e(advice)}</p></section>
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
