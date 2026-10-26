"""Cody Factory: owner-controlled, dependency-free local software production harness.

No network installs, agent execution, sudo, remote shell, package management,
credential access, or arbitrary project-code execution. Local scaffolds and static
source inspection use a dedicated user-owned workspace. Explicitly reports
upstream agent presence as DETECTED, never as a running/paired service.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import threading
import uuid

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
MAX_PROJECTS = 40
MAX_SCANNED_BYTES = 512_000
MAX_PROJECT_FILES = 100

TOOL_CATALOG = [
    ("opencode", "OpenCode", "AI coding", "penguin-or-s1", "headless runs and TUI", "https://opencode.ai/docs/"),
    ("openhands", "OpenHands", "AI coding", "s1-preferred", "Docker sandbox and agent SDK", "https://docs.openhands.dev/"),
    ("zeroclaw", "ZeroClaw", "agent dock", "penguin-evaluate", "lightweight Rust agent, review permissions", "https://github.com/zeroclaw-labs/zeroclaw"),
    ("nanobot", "nanobot", "agent dock", "penguin-evaluate", "Python assistant runtime", "https://github.com/HKUDS/nanobot"),
    ("git", "Git", "source control", "both", "repositories, branches and worktrees", "https://git-scm.com/"),
    ("ssh", "OpenSSH", "private transports", "both", "authenticated remote shell (owner-approved only)", "https://www.openssh.com/"),
    ("ssh-keygen", "SSH key verifier", "private transports", "both", "local public-key fingerprint checks", "https://www.openssh.com/"),
    ("netbird", "NetBird", "private transports", "both", "authenticated mesh peer (not equivalent to SSH)", "https://netbird.io/"),
    ("tailscale", "Tailscale", "private transports", "both", "existing tailnet, do not alter", "https://tailscale.com/"),
    ("rsync", "rsync", "transfers", "both", "selective authorized copies", "https://rsync.samba.org/"),
    ("syncthing", "Syncthing", "transfers", "s1-preferred", "approved synced project material", "https://syncthing.net/"),
    ("tmux", "tmux", "terminal", "both", "resumable terminal sessions", "https://github.com/tmux/tmux"),
    ("zellij", "Zellij", "terminal", "both", "modern terminal panes", "https://zellij.dev/"),
    ("code", "VS Code", "IDE", "penguin", "editor integration and extensions", "https://code.visualstudio.com/"),
    ("codium", "VSCodium", "IDE", "penguin", "OSS editor alternative", "https://vscodium.com/"),
    ("rg", "ripgrep", "code search", "both", "fast repo searches", "https://github.com/BurntSushi/ripgrep"),
    ("fd", "fd", "code search", "both", "filesystem search", "https://github.com/sharkdp/fd"),
    ("uv", "uv", "Python tooling", "both", "versioned Python virtualenvs", "https://docs.astral.sh/uv/"),
    ("ruff", "Ruff", "Python tooling", "both", "linter and formatter", "https://docs.astral.sh/ruff/"),
    ("pytest", "pytest", "Python tooling", "both", "test automation", "https://pytest.org/"),
    ("node", "Node.js", "web tooling", "s1-preferred", "web runtimes/builds", "https://nodejs.org/"),
    ("npm", "npm", "web tooling", "s1-preferred", "JS package manager", "https://www.npmjs.com/"),
    ("docker", "Docker", "containers", "s1-only", "OpenHands/code sandbox candidate", "https://docs.docker.com/"),
    ("podman", "Podman", "containers", "s1-only", "rootless container candidate", "https://podman.io/"),
    ("go", "Go", "systems", "s1-preferred", "Go builds and testing", "https://go.dev/"),
    ("cargo", "Cargo", "systems", "s1-preferred", "Rust builds and testing", "https://doc.rust-lang.org/cargo/"),
    ("ollama", "Ollama", "model provider", "s1-preferred", "local CPU model candidate", "https://ollama.com/"),
]

CODY_ROLES = [
    {"name":"CODY","role":"Principal engineer","power":"Orchestrate reviewed mission plans and evidence","state":"DESIGN_ONLY"},
    {"name":"ATLAS","role":"Architect","power":"Boundaries, ADRs, interfaces","state":"PROFILE_ONLY"},
    {"name":"MUSE","role":"Strategist","power":"User goals, creative synthesis","state":"PROFILE_ONLY"},
    {"name":"SPARK","role":"Prototyper","power":"UI concepts, demos, extension ideas","state":"PROFILE_ONLY"},
    {"name":"FORGE","role":"Builder","power":"Tests, code, reproducible artifacts","state":"PROFILE_ONLY"},
    {"name":"PROOF","role":"QA reviewer","power":"Independent test receipts","state":"PROFILE_ONLY"},
    {"name":"SENTINEL","role":"Security","power":"Reject unsafe permission and key changes","state":"PROFILE_ONLY"},
]

TEMPLATE_FILES = {
  "python-cli": {
    "README.md": "# {title}\n\nA Genesis Creatrix factory starter. No network or secrets required.\n\n## Run\n\n`python3 main.py`\n\n## Tests\n\n`python3 -m unittest discover -s tests -v` (run locally after reviewing source).\n",
    "main.py": "def greet(name: str = 'Genesis') -> str:\n    return f'Hello, {name}! Build something useful.'\n\n\nif __name__ == '__main__':\n    print(greet())\n",
    "tests/test_main.py": "import unittest\nfrom main import greet\n\n\nclass SmokeTest(unittest.TestCase):\n    def test_greeting(self):\n        self.assertEqual(greet('Cody'), 'Hello, Cody! Build something useful.')\n",
    ".gitignore": "__pycache__/\n.pytest_cache/\n.venv/\n.env\n*.key\n",
    ".vscode/extensions.json": '{"recommendations":["ms-python.python","charliermarsh.ruff","eamodio.gitlens","continue.continue"]}\n',
  },
  "web-static": {
    "README.md": "# {title}\n\nA fast, local-first website scaffold. Open `index.html` in a browser. No build dependencies.\n",
    "index.html": "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Genesis Starter</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><main><p class=\"kicker\">GENESIS / FACTORY</p><h1>Build the future.</h1><p>A working local-first canvas.</p></main><script src=\"app.js\"></script></body></html>\n",
    "style.css": "*{box-sizing:border-box}body{min-height:100vh;margin:0;background:#080d1d;color:#edf3ff;font:16px system-ui,sans-serif;display:grid;place-items:center}main{padding:48px;border:1px solid #43436e;border-radius:24px;background:linear-gradient(135deg,#1b1648,#0e233e)}h1{font-size:clamp(40px,8vw,74px);letter-spacing:-.05em}.kicker{color:#85eff0;font-size:12px;letter-spacing:.3em}\n",
    "app.js": "document.documentElement.dataset.genesis='ready';\n",
    ".gitignore": ".env\nnode_modules/\n.DS_Store\n",
    ".vscode/extensions.json": '{"recommendations":["esbenp.prettier-vscode","dbaeumer.vscode-eslint","eamodio.gitlens","continue.continue"]}\n',
  },
}


# Extra self-contained templates: no remote installs, services, or external privileges.
TEMPLATE_FILES.update({
  "mcp-stdio": {
    "README.md": "# {title}\n\nLocal-only Model Context Protocol server. Read-only demo tools, never SSH or secret access.\n\nRun: `python3 server.py` then send newline-delimited JSON-RPC.\n",
    "server.py": 'import json\nimport sys\n\nTOOLS = [{"name": "project_info", "description": "Return a static, nonsecret project capability statement", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}}]\n\ndef process(msg):\n    if not isinstance(msg, dict):\n        return {"jsonrpc":"2.0", "id":None, "error":{"code":-32600, "message":"Invalid Request"}}\n    method, mid = msg.get(\'method\'), msg.get(\'id\')\n    if not isinstance(method,str):\n        return {"jsonrpc":"2.0", "id":mid, "error":{"code":-32600, "message":"Invalid method"}}\n    if method.startswith(\'notifications/\') or \'id\' not in msg:\n        return None\n    if method == \'initialize\':\n        return {"jsonrpc":"2.0", "id":mid, "result":{"protocolVersion":"2025-11-25", "capabilities":{"tools":{}}, "serverInfo":{"name":"creatrix-project-demo", "version":"0.1.0"}}}\n    if method == \'tools/list\':\n        return {"jsonrpc":"2.0", "id":mid, "result":{"tools":TOOLS}}\n    if method == \'ping\':\n        return {"jsonrpc":"2.0", "id":mid, "result":{}}\n    if method == \'tools/call\' and msg.get(\'params\',{}).get(\'name\') == \'project_info\' and msg.get(\'params\',{}).get(\'arguments\',{}) in ({},None):\n        return {"jsonrpc":"2.0", "id":mid, "result":{"content":[{"type":"text", "text":"Local synthetic MCP sample; no filesystem/network tools"}]}}\n    return {"jsonrpc":"2.0", "id":mid, "error":{"code":-32601, "message":"Unknown method or tool"}}\n\nfor line in sys.stdin:\n    if len(line) > 65536: continue\n    try:\n        r = process(json.loads(line))\n    except (ValueError,TypeError,AttributeError):\n        r = {"jsonrpc":"2.0", "id":None, "error":{"code":-32700, "message":"Parse error"}}\n    if r is not None: print(json.dumps(r, separators=(\',\',\':\')), flush=True)\n',
    "tests/test_server.py": "import importlib.util\nfrom pathlib import Path\nimport unittest\n\np=Path(__file__).resolve().parents[1]/'server.py'\nspec=importlib.util.spec_from_file_location('factory_demo_mcp',p)\nmod=importlib.util.module_from_spec(spec)\n# Module must not execute reading stdin during import; test via safe subprocess in integration suite instead.\nclass StaticTest(unittest.TestCase):\n    def test_file_exists(self): self.assertTrue(p.is_file())\n",
    ".gitignore": "__pycache__/\n.venv/\n.env\n*.key\n",
    "AGENTS.md": "# Cody Agent Governance\n\nThis project is a read-only MCP starter. No tool may access secrets, network, shell, other projects or host data without separate approval. Evidence is mandatory.\n",
  },
  "browser-extension": {
    "README.md": "# {title}\n\nLocal-only minimal Chromium Manifest V3 extension. No host permissions or network calls. Review the source before loading unpacked.\n",
    "manifest.json": '{"manifest_version":3,"name":"Cody Creatrix Starter","description":"Owner-reviewed demo; no permissions","version":"0.1.0","action":{"default_popup":"popup.html"}}\n',
    "popup.html": '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Creatrix</title><link rel="stylesheet" href="popup.css"></head><body><main><h1>Cody Creator</h1><p id="result">Local only · permissions none</p><button id="run">Run local demo</button></main><script src="popup.js"></script></body></html>\n',
    "popup.css": "body{font:14px system-ui;background:#11152c;color:#eff2ff;min-width:300px;padding:20px}main{display:grid;gap:12px}button{padding:12px;background:#92cdfa;border:0;border-radius:10px;font:inherit}\n",
    "popup.js": "document.getElementById('run').addEventListener('click',()=>{document.getElementById('result').textContent='Demo completed locally; no external data accessed.'});\n",
    ".gitignore": ".env\n*.key\n.DS_Store\n",
    "AGENTS.md": "# Cody Extension Rules\n\nDefault permission set is empty. No host permissions, cookies, credential stores, arbitrary browsing, or network hooks without owner approval and review.\n",
  },
  "genesis-fullstack": {
    "README.md": "# {title}\n\nCody Factory full-stack starter with offline Python CLI, MCP server and Chrome extension. All components are separate; no network or model integration is automatic.\n",
    "src/main.py": "def create_result(task='Genesis'):\n    return {'task':task,'status':'TEMPLATE_ONLY'}\n",
    "tests/test_main.py": "import unittest\nfrom src.main import create_result\nclass TestProject(unittest.TestCase):\n def test_result(self): self.assertEqual(create_result('Cody')['status'],'TEMPLATE_ONLY')\n",
    "src/__init__.py": "",
    "extension/manifest.json": '{"manifest_version":3,"name":"Cody Creatrix Suite","version":"0.1.0","action":{"default_popup":"popup.html"}}\n',
    "extension/popup.html": '<!doctype html><html><head><meta charset="utf-8"><title>Creatrix</title></head><body><h1>CREATRIX</h1><p>Local sandbox, no permissions.</p></body></html>\n',
    "mcp/server.py": "# Read-only MCP server starter. Review and replace with the tested mcp-stdio template before enabling.\n",
    "AGENTS.md": "# Cody Factory Governance\n\nKeep the Genesis Mission Forge as the authoritative task ledger. Implement tests first. Do not run unreviewed code, install dependencies, open remote ports or access owner secrets. Require owner approval for deploy and SSH.\n",
    ".gitignore": ".env\n*.key\nnode_modules/\n.venv/\n__pycache__/\n",
  },
})

TEMPLATE_FILES["genesis-fullstack"]["mcp/server.py"] = TEMPLATE_FILES["mcp-stdio"]["server.py"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def available_tools() -> list[dict]:
    """Executable presence only; no version flag, shell or network requests."""
    result = []
    for exe, label, group, placement, purpose, source in TOOL_CATALOG:
        path = shutil.which(exe)
        result.append({"name": label, "executable": exe, "category": group,
                       "placement": placement, "purpose": purpose, "source": source,
                       "installed": path is not None, "state": "DETECTED_NOT_VERIFIED_RUNNING" if path else "ABSENT_OR_NOT_IN_PATH"})
    return result


def factory_snapshot(data_dir: Path) -> dict:
    tools = available_tools()
    return {
        "schema": "genesis-cody-factory/1",
        "time_utc": now_utc(),
        "runtime": "THIS_PROCESS_ONLY; NOT_CODY_HOST_VERIFIED",
        "toolchain": tools,
        "detected_tools": sum(t["installed"] for t in tools),
        "agent_dock": {name: next((t["state"] for t in tools if t["executable"]==name),"UNKNOWN") for name in ("opencode","openhands","zeroclaw","nanobot")},
        "mcp": {"implementation":"stdio read-only included", "active":"NOT_STARTED_BY_DASHBOARD", "network_exposed":False},
        "transports": {"ssh":"REQUIRES_PINNED_HOST_KEY_AND_EXISTING_AUTH", "netbird":"STATUS_UNVERIFIED", "github_mailbox":"HISTORICAL_ONLY_UNLESS_ACKED"},
        "workspace_count": len(list_workspaces(data_dir)),
        "auto_install": False,
        "autonomous_execution": "NOT_ENABLED; owner approval required",
        "roles": CODY_ROLES,
    }


def _workspace_root(data_dir: Path) -> Path:
    return data_dir / "factory-projects"


def _project_dir(data_dir: Path, slug: str) -> Path:
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        raise ValueError("Workspace name must be 3-40 lowercase letters/digits/hyphens; start with a letter")
    root = _workspace_root(data_dir)
    if root.is_symlink():
        raise ValueError("Workspace root is a symlink")
    child = root / slug
    if child.is_symlink():
        raise ValueError("Workspace path is a symlink")
    return child


def list_workspaces(data_dir: Path) -> list[dict]:
    root = _workspace_root(data_dir)
    if not root.is_dir() or root.is_symlink():
        return []
    result=[]
    for child in sorted(root.iterdir()):
        if child.is_dir() and not child.is_symlink() and SLUG_RE.fullmatch(child.name):
            manifest=child/"GENESIS_FACTORY.json"
            if not manifest.is_file() or manifest.is_symlink():
                continue
            try:
                meta=json.loads(manifest.read_text(encoding="utf-8")[:8192])
                if meta.get("schema") != "genesis-factory-workspace/1" or meta.get("slug") != child.name:
                    continue
                result.append({"slug":child.name,"title":meta.get("title",child.name)[:100],"template":meta.get("template"),"created_utc":meta.get("created_utc"),"stage":meta.get("stage","CREATED_UNVERIFIED")})
                if len(result)>=MAX_PROJECTS:
                    break
            except (OSError,ValueError,TypeError):
                continue
    return result


def _safe_write(path: Path, content: str):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        f.write(content)


class Factory:
    """User-owned workspace inside the SAME Creatrix data root, no new mission DB."""
    def __init__(self,data_dir:Path, mission_db=None):
        self.root=data_dir
        self.mission_db=mission_db
        self.lock=threading.RLock()

    def create_workspace(self,slug:str,title:str,template:str)->dict:
        if not isinstance(title,str) or not 1<=len(title.strip())<=90 or any(ord(c)<32 for c in title):
            raise ValueError("Project title required (1-90 characters)")
        if template not in TEMPLATE_FILES:
            raise ValueError("Unsupported project template")
        project=_project_dir(self.root,slug)
        with self.lock:
            if len(list_workspaces(self.root))>=MAX_PROJECTS:
                raise ValueError("Factory workspace limit reached")
            root=_workspace_root(self.root)
            root.mkdir(mode=0o700,parents=True,exist_ok=True)
            os.chmod(root,0o700)
            try:
                project.mkdir(mode=0o700)
            except FileExistsError as exc:
                raise ValueError("Workspace already exists") from exc
            meta={"schema":"genesis-factory-workspace/1","slug":slug,"title":title.strip(),"template":template,"created_utc":now_utc(),"stage":"SCAFFOLDED_NOT_EXECUTED","mission_id":None}
            try:
                for rel,body in TEMPLATE_FILES[template].items():
                    candidate=Path(rel)
                    if candidate.is_absolute() or ".." in candidate.parts:
                        raise RuntimeError("Invalid internal factory template")
                    _safe_write(project/candidate,body.replace("{title}",title.strip()))
                # Link to canonical Creatrix MissionOS store, no separate queue.
                if self.mission_db:
                    mission=self.mission_db.create("CODY | "+title.strip()[:100],"engineering","Project scaffold "+slug+" requires independent tests and review")
                    meta["mission_id"]=mission["id"]
                _safe_write(project/"GENESIS_FACTORY.json",json.dumps(meta,indent=2)+"\n")
                return {"slug":slug,"stage":meta["stage"],"template":template,"path":str(project),"mission_id":meta["mission_id"],"meaning":"Files generated locally only; no agent launched"}
            except Exception:
                # Roll back ONLY files created by this operation; new directory was exclusive.
                shutil.rmtree(project)
                raise

    def inspect_workspace(self,slug:str)->dict:
        project=_project_dir(self.root,slug)
        manifest=project/"GENESIS_FACTORY.json"
        if not project.is_dir() or not manifest.is_file() or manifest.is_symlink():
            raise ValueError("Unknown factory workspace")
        meta=json.loads(manifest.read_text(encoding="utf-8"))
        if meta.get("slug")!=slug or meta.get("schema")!="genesis-factory-workspace/1":
            raise ValueError("Invalid workspace manifest")
        if meta.get("template") not in TEMPLATE_FILES:
            raise ValueError("Unknown workspace template")
        files=[]
        for p in sorted(project.rglob("*")):
            if p.is_symlink():
                raise ValueError("Workspace contains symlink; inspection denied")
            if not p.is_file():
                continue
            if any(part in {".git",".venv","__pycache__","node_modules"} for part in p.relative_to(project).parts):
                continue
            if len(files)>=MAX_PROJECT_FILES:
                raise ValueError("Too many files for bounded inspection")
            size=p.stat().st_size
            if size>MAX_SCANNED_BYTES:
                raise ValueError("File too large for bounded inspection")
            # Do not inspect unrelated additions, sensitive env files or arbitrary private data.
            relative=p.relative_to(project).as_posix()
            if relative not in TEMPLATE_FILES[meta["template"]] and relative not in ("GENESIS_FACTORY.json", "opencode.json"):
                raise ValueError("Unexpected user-created file; needs reviewed custom harness")
            data=p.read_bytes()
            files.append({"path":relative,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
        return {"project":slug,"template":meta["template"],"mission_id":meta.get("mission_id"),"files":files,"verified_running":False,"status":"STATIC_AUDIT_ONLY","time_utc":now_utc()}


def integration_plan() -> dict:
    """Never alter real agent/global configs; generate documented guarded proposals."""
    return {
       "opencode": {"status":"ADAPTER_PREPARED_NOT_INSTALLED","host":"S1 preferred / Penguin memory-gated","interaction":"opencode run, with repo scope and bash/edit ask approvals","requires":["actual executable","model configured","owner-approved isolated worktree","quota confirmed"]},
       "openhands": {"status":"ADAPTER_PREPARED_NOT_INSTALLED","host":"S1 only","interaction":"OpenHands CLI, sandboxed container, owner review","requires":["Docker/sandbox verified","actual executable",">=4 GiB headroom measured","approved model","isolated workspace"]},
       "zeroclaw": {"status":"ADAPTER_PREPARED_NOT_INSTALLED","host":"Penguin probe or S1","interaction":"read-only assistant candidate; no shell permissions","requires":["pinned release","reviewed config","model access","bounded tools"]},
       "mcp": {"status":"LOCAL_STDIO_IMPLEMENTED","host":"owner console","interaction":"python3 factory_mcp.py","requires":["local client process","stdio-only","no credential forwarding"]},
       "ssh": {"status":"READ_ONLY_DESIGN_ONLY","host":"Penguin to S1 after trust","interaction":"verify pinned ED25519 host key; scoped non-root account","requires":["host key anchored from S1 console","existing authorized client identity","owner permissions"]},
       "transmitters": {"status":"NOT_ACTIVATED","host":"existing GitHub/Tailscale/NetBird","interaction":"verified mailbox receipts, scoped authenticated transports","requires":["real peer ACK","independent identity","stop controls"]},
    }
