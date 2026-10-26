#!/usr/bin/env python3
"""Cody Creatrix CLI: safe local tools, not an autonomous agent or SSH gateway.

No installs, privileged actions, persistent services, credential access,
subnet scanning, outbound connectivity except explicit single-target TCP22
or public SSH host-key observation when owner invokes that operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time

from creatrix_station import LocalDB
from cody_factory import Factory, TEMPLATE_FILES, available_tools, list_workspaces, factory_snapshot, integration_plan, _project_dir

DEFAULT_DATA_DIR = Path.home()/'.local'/'share'/'genesis-creatrix'
HOSTS = {'s1-lan':'192.168.1.151', 's1-tailnet':'100.126.209.84'}
FINGERPRINT = re.compile(r'^SHA256:[A-Za-z0-9+/]{40,45}=?$')


def emit(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload.get('state') not in {'DENIED', 'BLOCKED', 'FAILED'} else 2


def inspect_scaffold(factory: Factory, slug: str) -> dict:
    obj = factory.inspect_workspace(slug)
    directory = _project_dir(factory.root, slug)
    info = json.loads((directory/'GENESIS_FACTORY.json').read_text())
    expected = TEMPLATE_FILES[info['template']]
    for path, contents in expected.items():
        target = directory/path
        if target.is_symlink() or not target.is_file():
            return {'state':'BLOCKED','reason':'Template file missing or symlink','file':path}
        rendered = contents.replace('{title}', info['title'])
        if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(rendered.encode()).digest():
            return {'state':'BLOCKED','reason':'Scaffold modified; review changes before any execution','file':path}
    allowed = len(expected) + 1
    config = directory/'opencode.json'
    if config.exists() and not config.is_symlink():
        # Only the restricted project-level config created by this harness is recognized.
        try:
            conf=json.loads(config.read_text())
            cp=conf['mcp']['genesis-creatrix']
            prm=conf['permission']
            if (set(conf)!={'$schema','permission','mcp'} or set(conf['mcp'])!={'genesis-creatrix'}
                or cp['type']!='local' or cp['enabled'] is not True
                or cp['command'] != [sys.executable,'-u',str(Path(__file__).resolve().with_name('factory_mcp.py'))]
                or cp.get('environment') != {}
                or any(prm.get(k) != v for k,v in {'*':'ask','edit':'ask','bash':'ask','task':'ask',
                       'webfetch':'deny','websearch':'deny','external_directory':'deny'}.items())):
                return {'state':'BLOCKED','reason':'Unapproved OpenCode configuration'}
            allowed+=1
        except (OSError,ValueError,TypeError,KeyError,AttributeError):
            return {'state':'BLOCKED','reason':'Cannot validate OpenCode configuration'}
    if len(obj['files']) != allowed:
        return {'state':'BLOCKED','reason':'Unexpected project files; no automatic execution'}
    return {'state':'TEMPLATE_MATCH','files':obj['files'],'template':info['template'], 'project':slug}


def _limits(memory_bytes:int):
    resource.setrlimit(resource.RLIMIT_AS,(memory_bytes,memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU,(18,20))
    os.umask(0o077)


def run_scaffold_tests(factory: Factory, slug: str, approved: bool) -> dict:
    if not approved:
        return {'state':'DENIED','reason':'Explicit --approve-template-tests required; never run arbitrary repositories via browser'}
    chk=inspect_scaffold(factory,slug)
    if chk['state']!='TEMPLATE_MATCH': return chk
    kind=chk['template']
    project = _project_dir(factory.root,slug)
    if kind=='browser-extension':
        manifest=json.loads((project/'manifest.json').read_text())
        return {'state':'TEMPLATE_VALIDATED','manifest_version':manifest.get('manifest_version'),'permissions':manifest.get('permissions',[]),'executed_code':False}
    if kind=='web-static':
        return {'state':'TEMPLATE_VALIDATED','files_hashes_verified':len(chk['files']),'executed_code':False}
    # Only bundled, unmodified template files may execute; small temporary resource scope.
    from cody_factory import now_utc
    env={'PATH':'/usr/bin:/bin','HOME':str(project),'LANG':'C.UTF-8',
         'PYTHONPATH':'','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
         'PYTHONHASHSEED':'0'}
    t0=time.monotonic()
    try:
        done=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
             cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
             stderr=subprocess.STDOUT,text=True,errors='replace',timeout=15,
             preexec_fn=lambda: _limits(512*1024*1024),check=False)
    except subprocess.TimeoutExpired:
        return {'state':'FAILED','reason':'15 second template test timeout'}
    out={'state':'TEMPLATE_TESTS_PASS' if done.returncode==0 else 'FAILED',
         'source':'BUNDLED_UNMODIFIED_TEMPLATE_ONLY','exit_code':done.returncode,
         'duration_ms':int((time.monotonic()-t0)*1000),
         'output_tail':done.stdout[-4000:],'executed_code':True,'utc':now_utc()}
    return out


def ssh_public_hostkey(endpoint: str, expected: str|None=None) -> dict:
    """Observe a named owner's SSH public host key; never authenticate or copy a private key."""
    address=HOSTS[endpoint]
    if expected is not None and not FINGERPRINT.fullmatch(expected):
        return {'state':'DENIED','reason':'Expected fingerprint must be a valid SHA256 SSH host-key fingerprint'}
    if not (shutil.which('ssh-keyscan') and shutil.which('ssh-keygen')):
        return {'state':'BLOCKED','reason':'OpenSSH public host-key tools not installed'}
    try:
        scan=subprocess.run(['ssh-keyscan','-T','5','-t','ed25519',address],
            capture_output=True,text=True,errors='replace',timeout=7,check=False,stdin=subprocess.DEVNULL)
        pub='\n'.join(s for s in scan.stdout.splitlines() if s and not s.lstrip().startswith('#'))
        if not pub:
            return {'state':'BLOCKED','reason':'No public host key received','endpoint':endpoint}
        fp=subprocess.run(['ssh-keygen','-lf','-','-E','sha256'],
            input=pub+'\n',capture_output=True,text=True,errors='replace',timeout=4,check=False)
        if fp.returncode or len(fp.stdout.split())<2:
            return {'state':'BLOCKED','reason':'Could not parse public SSH fingerprint'}
        observed=fp.stdout.split()[1]
        if not FINGERPRINT.fullmatch(observed):
            return {'state':'BLOCKED','reason':'Invalid fingerprint format'}
        match=observed==expected if expected else None
        return {'state':'VERIFIED_MATCH' if match is True else ('MISMATCH_STOP' if match is False else 'OBSERVED_UNTRUSTED'),
                'endpoint':endpoint,'public_hostkey_fingerprint':observed,
                'host_identity_verified':match is True,
                'ssh_authenticated':False,
                'reason':'Expected fingerprint must come from independent trusted S1 console or anchor; observation alone is not identity proof'}
    except (OSError,subprocess.TimeoutExpired):
        return {'state':'BLOCKED','reason':'Read-only fingerprint probe failed'}


def generate_opencode_config(factory:Factory, slug:str) -> dict:
    project=_project_dir(factory.root,slug)
    conf=project/'opencode.json'
    if conf.exists() or conf.is_symlink():
        return {'state':'BLOCKED','reason':'Project already has an opencode.json file; never overwrite it'}
    chk=inspect_scaffold(factory,slug)
    if chk['state']!='TEMPLATE_MATCH': return chk
    # OpenCode v1: strict-by-default. This is a proposal; OpenCode may have other config schema in v2.
    config={'$schema':'https://opencode.ai/config.json',
      'permission':{'*':'ask','edit':'ask','bash':'ask','task':'ask',
                    'webfetch':'deny','websearch':'deny','external_directory':'deny'},
      'mcp':{'genesis-creatrix':{
          'type':'local','command':[sys.executable,'-u',str(Path(__file__).resolve().with_name('factory_mcp.py'))],
          'enabled':True,'environment':{}}}}
    with conf.open('x',encoding='utf-8') as f:
        json.dump(config,f,indent=2);f.write('\n')
    os.chmod(conf,0o600)
    return {'state':'CONFIG_STAGED_NOT_PAIRED','path':str(conf),
            'mcp':'read-only stdio server','model_configured':False,
            'opencode_running':False,'auto_install':False,
            'note':'Review config against installed OpenCode major version before running; no global config touched.'}


def parser():
    p=argparse.ArgumentParser(prog='codyctl',description='Cody Factory governed workstation CLI')
    p.add_argument('--data-dir',default=str(DEFAULT_DATA_DIR),help='Local owner data directory')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor',help='Local tools and role presence only')
    sub.add_parser('integrations',help='Nonsecret OpenCode/OpenHands/MCP/SSH readiness')
    sub.add_parser('projects',help='List local factory scaffolds')
    a=sub.add_parser('new',help='Create an owned local starter and mission entry')
    a.add_argument('slug');a.add_argument('--title',required=True);a.add_argument('--template',choices=sorted(TEMPLATE_FILES),default='genesis-fullstack')
    b=sub.add_parser('inspect',help='Hash source and verify scaffold state');b.add_argument('slug')
    b=sub.add_parser('test',help='Explicit bounded tests for unmodified bundled scaffold ONLY');b.add_argument('slug');b.add_argument('--approve-template-tests',action='store_true')
    b=sub.add_parser('opencode-config',help='Stage local read-only MCP + ask-before-effects project config');b.add_argument('slug')
    b=sub.add_parser('ssh-hostkey',help='Observe fixed S1 public host fingerprint without login');b.add_argument('--endpoint',choices=sorted(HOSTS),default='s1-lan');b.add_argument('--expected')
    sub.add_parser('mcp-command',help='Show explicit local stdio MCP command')
    return p


def main(argv=None)->int:
    args=parser().parse_args(argv)
    if os.geteuid()==0:
        return emit({'state':'DENIED','reason':'Run as regular user, never sudo/root'})
    try:
        root=Path(args.data_dir).expanduser().resolve()
        if root.is_symlink(): return emit({'state':'DENIED','reason':'Data directory symlink refused'})
        if args.cmd in {'doctor','integrations','mcp-command','ssh-hostkey'}:
            if args.cmd=='doctor':return emit(factory_snapshot(root))
            if args.cmd=='integrations':return emit(integration_plan())
            if args.cmd=='mcp-command':return emit({'state':'READY_FOR_LOCAL_LAUNCH','command':[sys.executable,'-u',str(Path(__file__).with_name('factory_mcp.py'))], 'stdio_only':True, 'secrets':False})
            return emit(ssh_public_hostkey(args.endpoint,args.expected))
        db=LocalDB(root)
        factory=Factory(root,db)
        if args.cmd=='projects':return emit({'state':'LOCAL_SCAFFOLDS_ONLY','projects':list_workspaces(root)})
        if args.cmd=='new':return emit(factory.create_workspace(args.slug,args.title,args.template))
        if args.cmd=='inspect':return emit(inspect_scaffold(factory,args.slug))
        if args.cmd=='test':return emit(run_scaffold_tests(factory,args.slug,args.approve_template_tests))
        if args.cmd=='opencode-config':return emit(generate_opencode_config(factory,args.slug))
    except (ValueError,FileExistsError,OSError,KeyError,TypeError) as e:
        return emit({'state':'BLOCKED','reason':str(e)[:300]})
    return emit({'state':'BLOCKED','reason':'Unknown command'})

if __name__=='__main__':raise SystemExit(main())
