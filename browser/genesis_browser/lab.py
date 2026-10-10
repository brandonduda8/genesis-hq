"""Local-only Genesis Browser Lab. No login, no real sites, no background jobs."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .policy import RunOptions, digest
from .runner import execute

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT/'web'
MIME = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.png':'image/png'}
RUN_ID = re.compile(r'^[a-f0-9]{16}$')
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'none'; frame-ancestors 'none'"


def make_fixture_plan(project: str):
    if not isinstance(project,str) or not 1<=len(project.strip())<=50 or any(ord(ch)<32 for ch in project):
        raise ValueError('Project name must be 1..50 printable characters')
    name=project.strip()
    return {
      'schema':'genesis-browser-plan/v1', 'job_id':'fixture-demo',
      'allowed_origins':['http://127.0.0.1:8777'],
      'actions':[
        {'id':'open','kind':'navigate','url':'http://127.0.0.1:8777/demo.html'},
        {'id':'inspect','kind':'text','role':'heading','name':'Genesis Owned Browser Fixture'},
        {'id':'fill','kind':'fill','role':'textbox','name':'Project','value':name},
        {'id':'create','kind':'click','role':'button','name':'Create sample plan'},
        {'id':'proof','kind':'assert_text','text':'Fixture ready: '+name},
        {'id':'capture','kind':'screenshot'},
      ]}


def handler_factory(*, output_root, browser_binary=None):
    output_root=pathlib.Path(output_root).resolve()
    output_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(output_root,0o700)
    lock=threading.Lock()

    class LabHandler(BaseHTTPRequestHandler):
        def log_message(self,format,*args): pass
        def headers_for(self,status=200,mime='application/json; charset=utf-8',length=None):
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy',CSP)
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            if length is not None:self.send_header('Content-Length',str(length))
            self.end_headers()
        def sendbytes(self,status,data,mime='application/json; charset=utf-8'):
            self.headers_for(status,mime,len(data));self.wfile.write(data)
        def sendjson(self,status,value):self.sendbytes(status,json.dumps(value).encode())
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/api/health':
                return self.sendjson(200,{'name':'Genesis Browser Lab','mode':'FIXTURE_ONLY','external_mutations':'DENIED','independent_review':'PENDING'})
            if path in ('/','/app.js','/app.css'):
                name={'/':'index.html','/app.js':'app.js','/app.css':'app.css'}[path]
                data=(WEB/name).read_bytes()
                return self.sendbytes(200,data,MIME[pathlib.Path(name).suffix])
            m=re.fullmatch(r'/api/runs/([a-f0-9]{16})/(receipt|image)',path)
            if m:
                folder=output_root/m.group(1)
                candidate=folder/('receipt.json' if m.group(2)=='receipt' else 'capture.png')
                if not candidate.is_file():return self.sendjson(404,{'error':'Not found'})
                return self.sendbytes(200,candidate.read_bytes(), 'image/png' if m.group(2)=='image' else 'application/json; charset=utf-8')
            return self.sendjson(404,{'error':'Not found'})
        def do_POST(self):
            if urlparse(self.path).path!='/api/run':return self.sendjson(404,{'error':'Not found'})
            expected='http://127.0.0.1:'+str(self.server.server_port)
            origin=self.headers.get('Origin')
            if origin != expected or self.headers.get('X-Genesis-Lab') != 'fixture-confirmed' or self.headers.get('Content-Type')!='application/json':
                return self.sendjson(403,{'error':'Origin or fixture owner confirmation missing'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<=0 or length>512:return self.sendjson(413,{'error':'Too large'})
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict) or set(data)!={'project'}:return self.sendjson(400,{'error':'Invalid parameters'})
                plan=make_fixture_plan(data['project'])
            except (TypeError,ValueError,KeyError,json.JSONDecodeError):
                return self.sendjson(400,{'error':'Invalid project'})
            if not lock.acquire(blocking=False):
                return self.sendjson(409,{'error':'Browser is busy; one run at a time'})
            try:
                run_id=secrets.token_hex(8)
                result=execute(plan,output_root/run_id, options=RunOptions(fixture=True,execute=True,max_seconds=40),
                   authorization={'plan_sha256':digest(plan),'approved_action_ids':['fill','create'],'purpose':'LOCAL_FIXTURE_TEST_ONLY'},
                   browser_binary=browser_binary)
                return self.sendjson(200 if result['execution'].startswith('EXECUTED') else 502,{'run_id':run_id,'receipt':result,'image_url':'/api/runs/'+run_id+'/image'})
            except Exception as e:
                return self.sendjson(503,{'error':'Runtime unavailable','error_type':type(e).__name__})
            finally: lock.release()
    return LabHandler


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8789)
    p.add_argument('--receipts',default=str(ROOT/'runs'))
    p.add_argument('--browser-binary',default=None)
    args=p.parse_args(argv)
    if not 1024<=args.port<=65535:raise SystemExit('Invalid port')
    # Only loopback, no public binding or credentials.
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_factory(output_root=args.receipts,browser_binary=args.browser_binary))
    print('Genesis Browser Lab ready on http://127.0.0.1:'+str(args.port)+' (fixture-only)')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
