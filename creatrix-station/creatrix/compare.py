#!/usr/bin/env python3
"""Read-only before/after comparator for two Creatrix audit reports."""
import argparse
import json
from pathlib import Path


def comparison(before: dict, after: dict) -> dict:
    b = before['memory']; a = after['memory']
    if before.get('schema') != 'genesis-creatrix-audit/1' or after.get('schema') != 'genesis-creatrix-audit/1':
        raise ValueError('Unexpected report schema')
    fields = ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree')
    return {
        'schema': 'genesis-creatrix-compare/1',
        'before_utc': before.get('collected_utc'), 'after_utc': after.get('collected_utc'),
        'memory_delta_bytes': {k: a.get(k, 0) - b.get(k, 0) for k in fields},
        'before_admission': before['admission_plan']['state'],
        'after_admission': after['admission_plan']['state'],
        'services_changed': {k: [before['services'].get(k, 'unknown'), v]
                             for k, v in after['services'].items() if before['services'].get(k, 'unknown') != v},
        'note': 'Compare evidence only. Different container lifecycles or unequal workloads are not controlled experiments.'
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('before'); p.add_argument('after')
    args = p.parse_args()
    b = json.loads(Path(args.before).read_text())
    a = json.loads(Path(args.after).read_text())
    print(json.dumps(comparison(b, a), indent=2))


if __name__ == '__main__':
    main()
