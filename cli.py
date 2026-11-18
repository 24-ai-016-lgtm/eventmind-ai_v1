"""Single command for initial pack and each update. Prints real trace and saves results."""
import argparse
import json
import sys
from pathlib import Path
from eventmind.state import process,load,save,trace_summary
from eventmind.independent_audit import audit


def main():
    ap=argparse.ArgumentParser(description='EventMind one-command planner and updater')
    ap.add_argument('input',help='Path to message pack or one new message file')
    ap.add_argument('--state',default='outputs/state.json',help='Previous state file; created automatically')
    ap.add_argument('--fresh',action='store_true',help='Start new plan instead of updating existing one')
    args=ap.parse_args()
    text=Path(args.input).read_text(encoding='utf-8')
    state_path=Path(args.state)
    previous=None if args.fresh or not state_path.exists() else load(state_path)
    try:
        result=process(text,previous)
    except Exception as exc:
        print('Processing failed:',str(exc),file=sys.stderr)
        return 1
    audit_result = audit(result)
    result["independent_audit"] = audit_result

    if not audit_result["independently_valid"]:
        result["valid"] = False
        failed = [
            c["check"]
            for c in audit_result["checks"]
            if not c["pass"]
        ]
        result["warnings"].append(
            "Independent audit failed: " + ", ".join(failed)
        )

    save(result,state_path)
    save(result['plan'],state_path.with_name('plan.json'))
    save(result['trace'],state_path.with_name('trace.json'))
    print('=== PLAN ===')
    print(json.dumps(result['plan'],ensure_ascii=False,indent=2))
    print('\n=== REJECTED MESSAGES ===')
    print(json.dumps(result['rejected'],ensure_ascii=False,indent=2))
    print('\n=== VALIDATION ===')
    print(json.dumps({'valid':result['valid'],'warnings':result['warnings']},indent=2))
    print('\\n=== INDEPENDENT AUDIT ===')
    print(json.dumps(audit_result, indent=2))
    print('\\n=== FULL REAL MODEL TRACE ===')
    print(json.dumps(result['trace'],ensure_ascii=False,indent=2))
    print('\n=== TOTAL TOKEN USAGE ===')
    print(json.dumps(trace_summary(result['trace']),indent=2))
    print(f'\nSaved files in {state_path.parent}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
