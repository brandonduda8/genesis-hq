"""Pure, dependency-free policy gate for Genesis Browser v0.1.

External targets are observation-only; fixture-owned targets may be automated
only with per-action approval bound to the SHA-256 of the exact plan bytes.
This is a LOCAL development gate, not an authenticated Genesis permission service.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

SCHEMA = 'genesis-browser-plan/v1'
JOB = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$')
ACTION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
ORIGIN = re.compile(r'^[a-z0-9.-]+$')
OBSERVE = {'navigate', 'text', 'assert_text', 'screenshot', 'snapshot'}
MUTATIONS = {'click', 'fill', 'select'}
ALL = OBSERVE | MUTATIONS
BLOCKED_CLICK_LABELS = re.compile(r'\b(buy|pay|checkout|order now|purchase|send|publish|post|delete|erase|subscribe|transfer|sign[ -]?in|log[ -]?in|register|withdraw)\b', re.I)

class PolicyError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def safe_origin(url: str, *, allow_fixture=False) -> str:
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 32 for c in url):
        raise PolicyError('invalid URL')
    parsed = urlsplit(url)
    if parsed.username is not None or parsed.password is not None or parsed.hostname is None:
        raise PolicyError('URL credentials/missing hostname forbidden')
    host = parsed.hostname.lower().rstrip('.')
    if not host or not ORIGIN.fullmatch(host) or host.endswith('.local'):
        raise PolicyError('invalid host')
    try:
        port = parsed.port
    except ValueError as e:
        raise PolicyError('invalid port') from e
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if allow_fixture and parsed.scheme == 'http' and host in ('127.0.0.1', 'localhost') and port and 1024 <= port <= 65535:
        return f'http://{host}:{port}'
    if parsed.scheme != 'https' or ip is not None or host == 'localhost' or host.endswith('.localhost') or '.' not in host:
        raise PolicyError('only HTTPS DNS public origins, or explicit localhost fixture')
    if port not in (None, 443):
        raise PolicyError('nonstandard external ports denied')
    return f'https://{host}'


def read_plan(plan, *, fixture=False):
    if not isinstance(plan, dict) or set(plan) != {'schema', 'job_id', 'allowed_origins', 'actions'}:
        raise PolicyError('unknown or missing plan fields')
    if plan['schema'] != SCHEMA or not isinstance(plan['job_id'], str) or not JOB.fullmatch(plan['job_id']):
        raise PolicyError('invalid schema or job ID')
    origins = plan['allowed_origins']
    if not isinstance(origins, list) or not 1 <= len(origins) <= 3 or len(set(map(str, origins))) != len(origins):
        raise PolicyError('1-3 unique explicitly allowed origins required')
    accepted = []
    for origin in origins:
        valid = safe_origin(origin, allow_fixture=fixture)
        if origin != valid:
            raise PolicyError('allowed_origins must be canonical origins without paths')
        accepted.append(valid)
    if fixture and any(not (o.startswith("http://127.0.0.1:") or o.startswith("http://localhost:")) for o in accepted):
        raise PolicyError("fixture mode is restricted to localhost only")
    actions = plan['actions']
    if not isinstance(actions, list) or not 1 <= len(actions) <= 30:
        raise PolicyError('1-30 actions required')
    seen = set()
    for action in actions:
        if not isinstance(action, dict):
            raise PolicyError('action must be an object')
        kind = action.get('kind')
        aid = action.get('id')
        if kind not in ALL or not isinstance(aid, str) or not ACTION.fullmatch(aid) or aid in seen:
            raise PolicyError('invalid/duplicate action or kind')
        seen.add(aid)
        fields = {
            'navigate': {'id', 'kind', 'url'},
            'text': {'id', 'kind', 'role', 'name'},
            'assert_text': {'id', 'kind', 'text'},
            'screenshot': {'id', 'kind'},
            'snapshot': {'id', 'kind'},
            'click': {'id', 'kind', 'role', 'name'},
            'fill': {'id', 'kind', 'role', 'name', 'value'},
            'select': {'id', 'kind', 'role', 'name', 'value'},
        }[kind]
        if set(action) != fields:
            raise PolicyError('unexpected/missing action fields for ' + aid)
        if kind == 'navigate':
            if safe_origin(action['url'], allow_fixture=fixture) not in accepted:
                raise PolicyError('navigation outside origin allowlist')
        if kind in {'text', 'click', 'fill', 'select'}:
            if action['role'] not in {'button', 'textbox', 'combobox', 'link', 'heading', 'status', 'paragraph'}:
                raise PolicyError('unsupported semantic role')
            if not isinstance(action['name'], str) or not 1 <= len(action['name']) <= 140:
                raise PolicyError('invalid role name')
        if kind == 'assert_text' and (not isinstance(action['text'], str) or not 1 <= len(action['text']) <= 300):
            raise PolicyError('invalid assertion text')
        if kind in {'fill', 'select'}:
            if not isinstance(action['value'], str) or len(action['value']) > 1200:
                raise PolicyError('input exceeds bound')
        if kind == 'click' and BLOCKED_CLICK_LABELS.search(action['name']):
            raise PolicyError('sensitive action name prohibited; no payments, outreach, publish or accounts')
        if kind in MUTATIONS and not fixture:
            raise PolicyError('v0.1 refuses mutation outside fixture mode')
    return plan


def approval_check(plan, authorization):
    ids = [a['id'] for a in plan['actions'] if a['kind'] in MUTATIONS]
    if not ids:
        return
    if not isinstance(authorization, dict) or set(authorization) != {'plan_sha256', 'approved_action_ids', 'purpose'}:
        raise PolicyError('per-action approval file required for mutations')
    if authorization['plan_sha256'] != digest(plan) or not isinstance(authorization['approved_action_ids'], list):
        raise PolicyError('approval not bound to this exact plan')
    if set(authorization['approved_action_ids']) != set(ids) or len(authorization['approved_action_ids']) != len(ids):
        raise PolicyError('each mutating action must be explicitly approved exactly once')
    if authorization['purpose'] != 'LOCAL_FIXTURE_TEST_ONLY':
        raise PolicyError('approval purpose unsupported; no live authority integrated')


@dataclass(frozen=True)
class RunOptions:
    fixture: bool = False
    execute: bool = False
    max_seconds: int = 60
    screenshot: bool = True

    def __post_init__(self):
        if not 5 <= self.max_seconds <= 120:
            raise PolicyError('execution time limit must be 5-120s')
