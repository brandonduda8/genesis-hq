"""Durable, governed lead-to-quote data layer (standard library only)."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
from contextlib import closing
import re
import sqlite3
import uuid

STAGES = frozenset(('new', 'contacted', 'quoted', 'won', 'lost'))
FIELDS = {'customer_name': 120, 'company': 160, 'email': 254,
          'service': 160, 'notes': 2000, 'owner': 80}
MAX_ITEMS = 20
MAX_UNIT_PRICE_CENTS = 100_000_000


class InputError(ValueError):
    pass


class ConflictError(InputError):
    pass


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def normalized_text(value, name, cap, required=False):
    if not isinstance(value, str):
        raise InputError(f'{name} must be text')
    value = value.strip()
    if len(value) > cap or '\x00' in value or (required and not value):
        raise InputError(f'{name} is empty, invalid, or exceeds {cap} characters')
    return value


def normalize_lead(data, existing=None):
    if not isinstance(data, dict) or not data:
        raise InputError('Expected a nonempty object')
    allowed = set(FIELDS) | ({'stage'} if existing is not None else set())
    if set(data) - allowed:
        raise InputError('Unexpected lead fields')
    source = (existing or {}) | data
    vals = {}
    for field, limit in FIELDS.items():
        vals[field] = normalized_text(source.get(field, ''), field, limit,
                                      required=(field in ('customer_name', 'service')))
    if vals['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', vals['email']):
        raise InputError('Invalid email address')
    stage = source.get('stage', 'new')
    if stage not in STAGES:
        raise InputError('Invalid stage')
    vals['stage'] = stage
    return vals


def normalize_items(items):
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise InputError('Quote must be a list of at most 20 items')
    clean = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {'description', 'quantity', 'unit_price_cents'}:
            raise InputError(f'Invalid quote item {i}')
        desc = normalized_text(item['description'], 'description', 160, required=True)
        q, p = item['quantity'], item['unit_price_cents']
        if type(q) is not int or not 1 <= q <= 1000:
            raise InputError('Quantity must be an integer between 1 and 1000')
        if type(p) is not int or not 0 <= p <= MAX_UNIT_PRICE_CENTS:
            raise InputError('Unit price must be a nonnegative number of cents below $1,000,000')
        clean.append({'position': i, 'description': desc, 'quantity': q,
                      'unit_price_cents': p, 'line_total_cents': q * p})
    if sum(x['line_total_cents'] for x in clean) > 100_000_000_000:
        raise InputError('Quote total exceeds safety limit')
    return clean


class Store:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        with closing(self.db()) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, company TEXT NOT NULL,
                    email TEXT NOT NULL, service TEXT NOT NULL, notes TEXT NOT NULL,
                    owner TEXT NOT NULL, stage TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quote_items (
                    lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL, description TEXT NOT NULL,
                    quantity INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL,
                    PRIMARY KEY (lead_id, position)
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL,
                    kind TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY, request_digest TEXT NOT NULL,
                    lead_id TEXT NOT NULL REFERENCES leads(id), created_at TEXT NOT NULL
                );
            ''')
        if self.path.exists():
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def db(self):
        conn = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    @staticmethod
    def row(conn, ident):
        row = conn.execute('SELECT * FROM leads WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise LookupError('Lead not found')
        out = dict(row)
        quote = conn.execute('SELECT position,description,quantity,unit_price_cents FROM quote_items '
                             'WHERE lead_id=? ORDER BY position', (ident,)).fetchall()
        out['quote_items'] = [dict(q) | {'line_total_cents': q['quantity'] * q['unit_price_cents']} for q in quote]
        out['quote_total_cents'] = sum(q['line_total_cents'] for q in out['quote_items'])
        out['is_demo'] = bool(out['is_demo'])
        return out

    def get(self, ident):
        with closing(self.db()) as conn:
            return self.row(conn, ident)

    def list(self, stage=None, query='', limit=250):
        if stage and stage not in STAGES:
            raise InputError('Invalid stage')
        if not isinstance(query, str) or len(query) > 120:
            raise InputError('Search text too long')
        with closing(self.db()) as conn:
            # Filter after bounded retrieval, avoiding SQL wildcard injection concerns.
            ids = conn.execute('SELECT id FROM leads ORDER BY updated_at DESC, id DESC').fetchall()
            leads = [self.row(conn, item['id']) for item in ids]
        if stage:
            leads = [r for r in leads if r['stage'] == stage]
        if query:
            s = query.lower().strip()
            leads = [r for r in leads if any(s in r[k].lower() for k in ('customer_name','company','service','email'))]
        return leads[:limit] if limit is not None else leads

    def create(self, data, idem_key, is_demo=False):
        vals = normalize_lead(data)
        if not isinstance(idem_key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}', idem_key):
            raise InputError('Idempotency-Key header must be 8..100 safe characters')
        fingerprint = hashlib.sha256(json.dumps(vals, sort_keys=True).encode()).hexdigest()
        ident = uuid.uuid4().hex
        now = utcnow()
        conn = self.db()
        try:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT request_digest,lead_id FROM idempotency WHERE key=?', (idem_key,)).fetchone()
            if old:
                if old['request_digest'] != fingerprint:
                    raise ConflictError('Idempotency key reused with different input')
                result = self.row(conn, old['lead_id'])
                conn.execute('COMMIT')
                return result, False
            conn.execute('''INSERT INTO leads(id,customer_name,company,email,service,notes,owner,stage,
                          is_demo,version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,1,?,?)''',
                         (ident, *[vals[k] for k in FIELDS], vals['stage'], int(is_demo), now, now))
            conn.execute('INSERT INTO idempotency VALUES (?,?,?,?)', (idem_key, fingerprint, ident, now))
            conn.execute('INSERT INTO events(lead_id,kind,created_at) VALUES (?,?,?)', (ident, 'LEAD_CREATED', now))
            result = self.row(conn, ident)
            conn.execute('COMMIT')
            return result, True
        except Exception:
            conn.execute('ROLLBACK')
            raise
        finally:
            conn.close()

    def update(self, ident, changes, expected_version):
        if type(expected_version) is not int or expected_version < 1:
            raise InputError('Expected positive integer version')
        conn = self.db()
        try:
            conn.execute('BEGIN IMMEDIATE')
            current = self.row(conn, ident)
            vals = normalize_lead(changes, current)
            if current['version'] != expected_version:
                raise ConflictError('Lead changed elsewhere; refresh before editing')
            now = utcnow()
            conn.execute('''UPDATE leads SET customer_name=?,company=?,email=?,service=?,notes=?,
                         owner=?,stage=?,version=version+1,updated_at=? WHERE id=? AND version=?''',
                         (*[vals[k] for k in FIELDS],vals['stage'],now,ident,expected_version))
            conn.execute('INSERT INTO events(lead_id,kind,created_at) VALUES (?,?,?)', (ident,'LEAD_UPDATED',now))
            result = self.row(conn, ident)
            conn.execute('COMMIT')
            return result
        except Exception:
            conn.execute('ROLLBACK')
            raise
        finally:
            conn.close()

    def save_quote(self, ident, items, expected_version):
        clean = normalize_items(items)
        if type(expected_version) is not int or expected_version < 1:
            raise InputError('Expected positive integer version')
        conn = self.db()
        try:
            conn.execute('BEGIN IMMEDIATE')
            current = self.row(conn, ident)
            if current['version'] != expected_version:
                raise ConflictError('Lead changed elsewhere; refresh before editing')
            conn.execute('DELETE FROM quote_items WHERE lead_id=?',(ident,))
            conn.executemany('INSERT INTO quote_items VALUES (?,?,?,?,?)',
                             [(ident,q['position'],q['description'],q['quantity'],q['unit_price_cents']) for q in clean])
            now = utcnow()
            conn.execute('UPDATE leads SET version=version+1,updated_at=? WHERE id=?',(now,ident))
            conn.execute('INSERT INTO events(lead_id,kind,created_at) VALUES (?,?,?)',(ident,'QUOTE_UPDATED',now))
            result=self.row(conn, ident)
            conn.execute('COMMIT')
            return result
        except Exception:
            conn.execute('ROLLBACK')
            raise
        finally:
            conn.close()

    def seed_demo(self):
        if self.list():
            raise ConflictError('Demo seed available only for an empty workspace')
        samples = [
            {'customer_name':'Jordan Rivera','company':'Cedar & Stone Repairs', 'email':'jordan@example.invalid',
             'service':'Storefront painting', 'notes':'Synthetic demo inquiry - request site measurements', 'owner':'Demo crew'},
            {'customer_name':'Casey Morgan','company':'North Creek Studio', 'email':'casey@example.invalid',
             'service':'Website refresh', 'notes':'Synthetic demo inquiry - landing page + contact form', 'owner':'Demo crew'},
        ]
        for i, data in enumerate(samples):
            self.create(data, 'demo-seed-20261009-'+str(i), is_demo=True)
        return self.list()

    def export_data(self):
        return {'schema_version':'foundry.v0.2','generated_at':utcnow(),
                'notice':'Local customer data backup; not a verified external deliverable',
                'leads':self.list(limit=None)}

    def export_csv(self):
        out=io.StringIO(newline='')
        columns=['id','customer_name','company','email','service','owner','stage','notes',
                 'quote_total_usd','is_demo','created_at','updated_at']
        writer=csv.writer(out)
        writer.writerow(columns)
        for row in self.list(limit=None):
            values=[]
            for col in columns:
                if col=='quote_total_usd': val=f"{row['quote_total_cents']/100:.2f}"
                else: val=str(row[col])
                # Prevent exported spreadsheet cells from becoming formulas.
                if val.startswith(('=', '+', '-', '@','\t','\r','\n')):
                    val="'"+val
                values.append(val)
            writer.writerow(values)
        return out.getvalue()

    def restore_backup(self, payload):
        """Atomic import into EMPTY database only; never overwrite customer records."""
        if not isinstance(payload, dict) or payload.get('schema_version') != 'foundry.v0.2':
            raise InputError('Expected a Foundry v0.2 JSON export')
        records = payload.get('leads')
        if not isinstance(records, list) or not 0 < len(records) <= 2000:
            raise InputError('Backup must contain 1..2000 records')
        prepared = []
        seen = set()
        for lead in records:
            if not isinstance(lead, dict):
                raise InputError('Malformed backup entry')
            ident = lead.get('id')
            if not isinstance(ident, str) or not re.fullmatch(r'[0-9a-f]{32}', ident) or ident in seen:
                raise InputError('Invalid or duplicate backup ID')
            seen.add(ident)
            vals = normalize_lead({**{k: lead.get(k, '') for k in FIELDS},
                                   'stage': lead.get('stage', 'new')}, existing={})
            created, updated = lead.get('created_at'), lead.get('updated_at')
            for stamp in (created, updated):
                if not isinstance(stamp, str) or len(stamp) > 42:
                    raise InputError('Invalid backup timestamp')
                try:
                    dt.datetime.fromisoformat(stamp)
                except ValueError as exc:
                    raise InputError('Invalid backup timestamp') from exc
            version = lead.get('version')
            if type(version) is not int or not 1 <= version <= 1_000_000_000:
                raise InputError('Invalid backup version')
            if type(lead.get('is_demo')) is not bool:
                raise InputError('Backup demo marker must be boolean')
            originals = lead.get('quote_items')
            if not isinstance(originals, list):
                raise InputError('Invalid backup quote items')
            for entry in originals:
                if not isinstance(entry, dict) or set(entry) != {'position','description','quantity','unit_price_cents','line_total_cents'}:
                    raise InputError('Unexpected quote backup fields')
            items = normalize_items([{k:entry[k] for k in ('description','quantity','unit_price_cents')}
                                     for entry in originals])
            if any(orig['position']!=clean['position'] or orig['line_total_cents']!=clean['line_total_cents']
                   for orig, clean in zip(originals, items)):
                raise InputError('Backup quote totals or positions do not reconcile')
            prepared.append((ident, vals, created, updated, version, int(lead['is_demo']), items))
        conn = self.db()
        try:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM leads LIMIT 1').fetchone():
                raise ConflictError('Cannot import into a nonempty workspace')
            for ident, vals, created, updated, version, is_demo, items in prepared:
                conn.execute('INSERT INTO leads(id,customer_name,company,email,service,notes,owner,stage,is_demo,version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (ident, *[vals[k] for k in FIELDS], vals['stage'], is_demo,version,created,updated))
                conn.executemany('INSERT INTO quote_items VALUES (?,?,?,?,?)',
                    [(ident,q['position'],q['description'],q['quantity'],q['unit_price_cents']) for q in items])
                conn.execute('INSERT INTO events(lead_id,kind,created_at) VALUES (?,?,?)',
                             (ident,'LEAD_RESTORED',utcnow()))
            conn.execute('COMMIT')
            return len(prepared)
        except Exception:
            conn.execute('ROLLBACK')
            raise
        finally:
            conn.close()

    def receipt(self):
        with closing(self.db()) as conn:
            row=conn.execute('SELECT COUNT(*) AS count FROM leads').fetchone()
            events=conn.execute('SELECT seq,lead_id,kind,created_at FROM events ORDER BY seq DESC LIMIT 20').fetchall()
        return {'lead_count':row['count'],'recent_events':[dict(e) for e in events],
                'execution':'LOCAL_SOFTWARE_ONLY','independent_review':'NOT_YET_PERFORMED'}
