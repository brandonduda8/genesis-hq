"""Local-first Foundry HTTP server. Only read/write scoped JSON; no model calls."""
from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import parse_qs, urlsplit

from .core import ConflictError, InputError, Store

FILES = {'/': ('index.html','text/html; charset=utf-8'),
         '/app.js': ('app.js','text/javascript; charset=utf-8'),
         '/style.css': ('style.css','text/css; charset=utf-8')}
MAX_BODY = 1_000_000
ALLOWED_BIND = {'127.0.0.1', 'localhost', '::1'}


def require_safe_bind(bind, token):
    if bind not in ALLOWED_BIND and (not token or len(token) < 32):
        raise ValueError('Non-loopback binding requires FOUNDRY_OWNER_TOKEN (at least 32 characters)')
    if token and len(token) < 32:
        raise ValueError('FOUNDRY_OWNER_TOKEN must be at least 32 characters')


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, store, owner_token=''):
        require_safe_bind(address[0], owner_token)
        self.store = store
        self.owner_token = owner_token
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'GenesisFoundry/0.2'

    def log_message(self, fmt, *args):
        # Never log Authorization, request bodies or customer data.
        return

    def headers_common(self, content_type='application/json; charset=utf-8'):
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")

    def respond(self, status, payload, kind='application/json; charset=utf-8', attachment=None):
        data = payload if isinstance(payload,bytes) else (
            json.dumps(payload,ensure_ascii=False).encode('utf-8') if isinstance(payload, (dict,list))
            else str(payload).encode('utf-8'))
        self.send_response(status)
        self.headers_common(kind)
        if attachment:
            self.send_header('Content-Disposition',f'attachment; filename="{attachment}"')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        owner = self.server.owner_token
        if not owner:
            return True  # localhost-only binding was enforced at startup
        actual=self.headers.get('Authorization','')
        wanted='Bearer '+owner
        return hmac.compare_digest(actual, wanted)

    def guard(self, mutation=False):
        if not self.allowed():
            self.respond(401,{'error':'Owner access required'})
            return False
        if mutation:
            # A cross-origin page cannot set this custom header without a CORS preflight.
            if self.headers.get('X-Foundry-Client') != 'v0.2':
                self.respond(403,{'error':'Missing same-origin client header'})
                return False
            origin=self.headers.get('Origin')
            if origin:
                hostname=self.headers.get('Host','')
                valid={'http://'+hostname,'https://'+hostname}
                if origin not in valid:
                    self.respond(403,{'error':'Origin rejected'})
                    return False
        return True

    def json_body(self):
        if self.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
            raise InputError('JSON Content-Type required')
        try:
            n=int(self.headers.get('Content-Length','-1'))
        except ValueError as exc:
            raise InputError('Invalid content length') from exc
        if n<2 or n>MAX_BODY:
            raise InputError('Invalid or oversized body')
        raw=self.rfile.read(n)
        try:
            data=json.loads(raw)
        except (json.JSONDecodeError,UnicodeDecodeError) as exc:
            raise InputError('Malformed JSON') from exc
        if not isinstance(data,dict):
            raise InputError('Expected a JSON object')
        return data

    def execute(self, callback):
        try:
            callback()
        except ConflictError as exc:
            self.respond(409, {'error':str(exc)})
        except (InputError, ValueError) as exc:
            self.respond(400, {'error':str(exc)})
        except LookupError:
            self.respond(404, {'error':'Record not found'})
        except Exception:
            self.respond(500, {'error':'Internal server error'})

    def do_GET(self):
        path=urlsplit(self.path)
        if path.path in FILES:
            file,mime=FILES[path.path]
            payload=(Path(__file__).parent/'web'/file).read_bytes()
            self.respond(200,payload,mime)
            return
        if path.path=='/api/health':
            self.respond(200,{'product':'Genesis Foundry v0.2','mode':'LOCAL_FIRST',
                'external_model_calls':'DISABLED','email_sending':'DISABLED',
                'persistent_storage':'SQLITE','authentication':'REQUIRED' if self.server.owner_token else 'LOOPBACK_ONLY'})
            return
        if not self.guard():
            return
        def work():
            if path.path=='/api/leads':
                qs=parse_qs(path.query)
                self.respond(200,{'leads':self.server.store.list(qs.get('stage',[None])[0],qs.get('q',[''])[0])})
            elif path.path=='/api/receipt':
                self.respond(200,self.server.store.receipt())
            elif path.path=='/api/export.json':
                self.respond(200,self.server.store.export_data(),attachment='foundry-backup.json')
            elif path.path=='/api/export.csv':
                self.respond(200,self.server.store.export_csv(),'text/csv; charset=utf-8',attachment='foundry-leads.csv')
            elif re.fullmatch(r'/api/leads/[0-9a-f]{32}',path.path):
                self.respond(200,self.server.store.get(path.path.split('/')[-1]))
            else:
                self.respond(404,{'error':'Not found'})
        self.execute(work)

    def do_POST(self):
        if not self.guard(mutation=True):
            return
        def work():
            path=urlsplit(self.path).path
            if path=='/api/leads':
                payload=self.json_body()
                result,created=self.server.store.create(payload,self.headers.get('Idempotency-Key',''))
                self.respond(201 if created else 200,result)
            elif path=='/api/demo-seed':
                self.json_body()  # must be an empty JSON object
                self.respond(201,{'leads':self.server.store.seed_demo(), 'notice':'SYNTHETIC DATA ONLY'})
            elif path=='/api/restore':
                count=self.server.store.restore_backup(self.json_body())
                self.respond(201, {'imported_records':count, 'notice':'IMPORTED_INTO_EMPTY_WORKSPACE'})
            else:
                self.respond(404,{'error':'Not found'})
        self.execute(work)

    def do_PATCH(self):
        if not self.guard(mutation=True):
            return
        def work():
            path=urlsplit(self.path).path
            if not re.fullmatch(r'/api/leads/[0-9a-f]{32}',path):
                self.respond(404,{'error':'Not found'});return
            body=self.json_body()
            if type(body.get('expected_version')) is not int:
                raise InputError('expected_version is required')
            version=body.pop('expected_version')
            self.respond(200,self.server.store.update(path.split('/')[-1],body,version))
        self.execute(work)

    def do_PUT(self):
        if not self.guard(mutation=True):
            return
        def work():
            path=urlsplit(self.path).path
            if not re.fullmatch(r'/api/leads/[0-9a-f]{32}/quote',path):
                self.respond(404,{'error':'Not found'});return
            body=self.json_body()
            if set(body)!={'items','expected_version'}:
                raise InputError('Expected items and expected_version')
            self.respond(200,self.server.store.save_quote(path.split('/')[-2],body['items'],body['expected_version']))
        self.execute(work)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=str(Path.home()/'.genesis'/'foundry.sqlite'))
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8787)
    args=parser.parse_args(argv)
    token=os.environ.get('FOUNDRY_OWNER_TOKEN','')
    require_safe_bind(args.bind,token)
    server=Server((args.bind,args.port),Store(args.db),token)
    print(f'Genesis Foundry v0.2 at http://{args.bind}:{server.server_port} (local-first; no agent execution)',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
