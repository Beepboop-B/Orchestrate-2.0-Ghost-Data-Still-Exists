"""Identity-free account linking via the deletion worker's primary-profile DELETE_RECORD events.
Signals (all from participant-facing data, all at/before audit_at):
  1. timing: primary delete happens shortly BEFORE reported_at (0.70-1.30h for batch cases, ~0h for precise ones)
  2. status consistency: reported_status -> worker reported_result
        COMPLETE -> SUCCESS ; NOT_STARTED -> FAILED ; PARTIALLY_COMPLETE -> PARTIAL or SUCCESS
  3. global one-to-one constraint propagation across ALL requests (a case with exactly one candidate
     claims it; claimed accounts are removed from every other case). Sound and deterministic.
Run: python account_link.py [dataset_dir]
"""
import csv, json, sys, os, collections
from datetime import datetime as dt
D = sys.argv[1] if len(sys.argv) > 1 else 'dataset'
f = lambda s: dt.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
H = lambda a, b: (f(a) - f(b)).total_seconds() / 3600
OK = {'COMPLETE': {'SUCCESS'}, 'NOT_STARTED': {'FAILED'}, 'PARTIALLY_COMPLETE': {'PARTIAL', 'SUCCESS'}}
def load(n): return list(csv.DictReader(open(os.path.join(D, n), encoding='utf-8')))

def link_accounts(requests, activity, claimed=frozenset(), lo=-0.25, hi=1.30):
    prim = [a for a in activity if a['event_type'] == 'DELETE_RECORD' and a['target_system'] == 'account_service'
            and a['resource_id'] not in claimed]
    C = {q['case_id']: {a['resource_id'] for a in prim
                        if lo <= H(q['reported_at'], a['event_time']) <= hi
                        and a['reported_result'] in OK.get(q['reported_status'], set())
                        and f(a['event_time']) <= f(q['audit_at'])} for q in requests}
    assigned, ch = {}, True
    while ch:                                   # arc-consistency style propagation
        ch = False; taken = set(assigned.values())
        for cid, s in C.items():
            if cid in assigned: continue
            C[cid] = s = s - taken
            if len(s) == 1: assigned[cid] = next(iter(s)); ch = True; taken |= s
    return assigned, C

if __name__ == '__main__':
    samp, full, act = load('sample_deletion_requests.csv'), load('deletion_requests.csv'), load('system_activity.csv')
    exp = {r['case_id']: json.loads(r['steps_json']) for r in load('sample_output.csv')}
    assigned, C = link_accounts(samp + full, act)
    ok = bad = amb = miss = 0; amb_in = 0
    for q in samp:
        cid = q['case_id']; truth = {s['resource_id'] for s in exp[cid] if s['system_id'] == 'account_service'}
        if cid in assigned:
            if assigned[cid] in truth: ok += 1
            else: bad += 1; print('WRONG', cid, assigned[cid], truth)
        elif C[cid]:
            amb += 1; amb_in += bool(C[cid] & truth)
        else: miss += 1
    print(f'samples: correct {ok}, wrong {bad}, ambiguous {amb} (truth inside remaining set for {amb_in}), no candidate {miss}')
    print('total assigned over all', len(samp)+len(full), 'requests:', len(assigned))
