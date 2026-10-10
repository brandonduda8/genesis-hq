"""Deterministic Playwright adapter; never delegates to a model or executes page text."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .policy import MUTATIONS, PolicyError, RunOptions, approval_check, digest, read_plan, safe_origin


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _save(path, content):
    path = pathlib.Path(path)
    path.write_bytes(content)
    os.chmod(path, 0o600)
    return hashlib.sha256(content).hexdigest()


def _scrub(message):
    # No page text or field values in exception receipts. Local errors can expose URLs.
    return str(message).split('\n')[0][:180]


def _engine(plan, output_dir, options, authorization, browser_binary):
    from playwright.sync_api import sync_playwright
    output_dir = pathlib.Path(output_dir)
    approved = set(plan['allowed_origins'])
    fixture = options.fixture
    limit = time.monotonic() + options.max_seconds
    receipts = []
    artifacts = []
    summary = {'job_id': plan['job_id'], 'schema': 'genesis-browser-receipt/v1',
               'plan_sha256': digest(plan), 'created_at': _utc(),
               'mode': 'FIXTURE_APPROVED' if fixture else 'OBSERVE_ONLY',
               'execution': 'ATTEMPTED', 'source_authentication': 'NOT_INTEGRATED',
               'authority': 'LOCAL_FIXTURE_FILE_ONLY' if fixture else 'READ_ONLY',
               'actions': receipts, 'artifacts': artifacts, 'network': {'allowed': 0, 'blocked': 0},
               'independent_review': 'PENDING'}
    with sync_playwright() as pw:
        if not browser_binary:
            browser_binary = shutil.which('chromium') or shutil.which('google-chrome')
        if not browser_binary:
            raise RuntimeError('No installed Chromium executable; no automatic install')
        browser = pw.chromium.launch(headless=True, executable_path=browser_binary)
        try:
            context = browser.new_context(accept_downloads=False, service_workers='block',
                                          permissions=[], ignore_https_errors=False)
            try:
                def route_request(route):
                    request = route.request
                    try:
                        origin = safe_origin(request.url, allow_fixture=fixture)
                        allowed_method = request.method in (('GET', 'HEAD', 'POST') if fixture else ('GET', 'HEAD'))
                        allowed = origin in approved and allowed_method
                    except PolicyError:
                        allowed = False
                    if allowed:
                        summary['network']['allowed'] += 1
                        route.continue_()
                    else:
                        summary['network']['blocked'] += 1
                        route.abort()
                context.route('**/*', route_request)
                # The HTTP request interceptor does not cover WebSockets. Explicitly block them.
                if hasattr(context, 'route_web_socket'):
                    context.route_web_socket('**/*', lambda websocket: websocket.close())
                page = context.new_page()
                page.on('dialog', lambda dialog: dialog.dismiss())
                page.on('popup', lambda popup: popup.close())
                page.set_default_timeout(6000)
                page.set_default_navigation_timeout(10000)
                for action in plan['actions']:
                    if time.monotonic() > limit:
                        summary['execution'] = 'BLOCKED_TIME_BUDGET'
                        break
                    began = time.monotonic()
                    outcome = {'id': action['id'], 'kind': action['kind'], 'state': 'FAILED'}
                    receipts.append(outcome)
                    try:
                        kind = action['kind']
                        if kind == 'navigate':
                            if fixture:
                                # The environment forbids loopback Chromium navigation.
                                # Load ONE bundled synthetic HTML fixture directly into a real
                                # isolated Chromium DOM: no external request or account.
                                if urlsplit(action['url']).path != '/demo.html' or urlsplit(action['url']).query:
                                    raise PolicyError('fixture allows only /demo.html')
                                html = (pathlib.Path(__file__).resolve().parents[1] / 'fixtures/demo.html').read_text(encoding='utf-8')
                                page.set_content(html, wait_until='domcontentloaded', timeout=10000)
                                summary['fixture_render'] = 'CHROMIUM_SET_CONTENT; NO HTTP NAVIGATION'
                            else:
                                page.goto(action['url'], wait_until='domcontentloaded', timeout=10000)
                                if safe_origin(page.url, allow_fixture=False) not in approved:
                                    raise PolicyError('redirect left allowed origin')
                        elif kind in {'text', 'fill', 'select', 'click'}:
                            loc = page.get_by_role(action['role'], name=action['name'], exact=True)
                            if kind == 'text':
                                outcome['text_preview'] = loc.inner_text(timeout=6000)[:160]
                            if kind == 'fill':
                                loc.fill(action['value'])
                            if kind == 'select':
                                loc.select_option(label=action['value'])
                            if kind == 'click':
                                loc.click()
                        elif kind == 'assert_text':
                            page.get_by_text(action['text'], exact=True).wait_for(state='visible', timeout=6000)
                        elif kind == 'snapshot':
                            text = page.locator('body').inner_text(timeout=6000)[:10000]
                            name = action['id'] + '-snapshot.txt'
                            sha = _save(output_dir / name, text.encode('utf-8'))
                            artifacts.append({'type': 'dom_text', 'name': name, 'sha256': sha,
                                              'privacy': 'LOCAL_OWNER_ONLY; UNREDACTED'})
                        elif kind == 'screenshot':
                            name = action['id'] + '.png'
                            sha = _save(output_dir / name, page.screenshot(full_page=False, timeout=6000))
                            artifacts.append({'type': 'screenshot', 'name': name, 'sha256': sha,
                                              'privacy': 'LOCAL_OWNER_ONLY; UNREDACTED'})
                        outcome['state'] = 'DONE'
                    except Exception as exc:
                        outcome['error_type'] = exc.__class__.__name__
                        outcome['error'] = _scrub(exc)
                        summary['execution'] = 'FAILED_ACTION'
                        break
                    finally:
                        outcome['elapsed_ms'] = int((time.monotonic() - began) * 1000)
                if summary['execution'] == 'ATTEMPTED':
                    summary['execution'] = 'EXECUTED_NOT_INDEPENDENTLY_VERIFIED'
                summary['finished_at'] = _utc()
            finally:
                context.close()
        finally:
            browser.close()
    return summary


def execute(plan, output_dir, *, options=RunOptions(), authorization=None, browser_binary=None):
    """Default preflight only. Never write to unapproved places without caller opting in."""
    read_plan(plan, fixture=options.fixture)
    if options.fixture and not options.execute:
        # Preflight requires no approval file since it performs no side effects.
        pass
    elif options.fixture:
        approval_check(plan, authorization)
    else:
        if any(a['kind'] in MUTATIONS for a in plan['actions']):
            raise PolicyError('public site mutation not supported')
    preflight = {'job_id': plan['job_id'], 'plan_sha256': digest(plan),
                 'schema': 'genesis-browser-preflight/v1',
                 'execution': 'PREFLIGHT_ONLY',
                 'allowed_origins': plan['allowed_origins'],
                 'actions': [{'id': a['id'], 'kind': a['kind']} for a in plan['actions']],
                 'external_mutation': 'DISABLED',
                 'source_authentication': 'NOT_INTEGRATED'}
    if not options.execute:
        return preflight
    output_dir = pathlib.Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PolicyError('evidence output directory must be empty; never overwrite receipts')
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    result = _engine(plan, output_dir, options, authorization, browser_binary)
    manifest = json.dumps(result, sort_keys=True, indent=2).encode('utf-8') + b'\n'
    _save(output_dir / 'receipt.json', manifest)
    return result
