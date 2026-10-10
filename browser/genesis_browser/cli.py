"""Genesis Browser: preflight default, scope-checked Playwright execution."""
import argparse
import json
import sys

from .policy import RunOptions, PolicyError
from .runner import execute


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', help='Declarative JSON plan')
    parser.add_argument('--execute', action='store_true', help='Run plan after preflight (no live mutations)')
    parser.add_argument('--fixture', action='store_true', help='Enable localhost fixture and local approved mutations')
    parser.add_argument('--approval-file', help='Local fixture action approval JSON; NOT production Genesis authority')
    parser.add_argument('--output', default='./genesis-browser-receipts', help='Must be empty for an execution')
    parser.add_argument('--browser-binary', help='Use an already installed Chromium; never downloads')
    parser.add_argument('--timeout', type=int, default=60)
    args=parser.parse_args(argv)
    try:
        with open(args.plan,encoding='utf-8') as f: plan=json.load(f)
        auth=None
        if args.approval_file:
            with open(args.approval_file,encoding='utf-8') as f: auth=json.load(f)
        result=execute(plan,args.output,options=RunOptions(fixture=args.fixture,execute=args.execute,max_seconds=args.timeout),authorization=auth,browser_binary=args.browser_binary)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0 if result['execution'] not in ('FAILED_ACTION','BLOCKED_TIME_BUDGET') else 1
    except (ValueError,OSError,PolicyError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)}),file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({'status':'UNAVAILABLE','error_type':type(exc).__name__,'note':'Browser could not start or execution was interrupted; no completion receipt'}),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
