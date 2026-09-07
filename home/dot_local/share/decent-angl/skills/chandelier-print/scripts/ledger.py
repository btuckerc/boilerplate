"""Persistent chandelier print accounting. This helper never controls a printer."""
import argparse
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

DEFAULT_PROJECT = Path.home() / 'src/chandelier-reconstruction-20260907'
ACTIVE = {'sending', 'printing', 'paused'}
TERMINAL = {'finished', 'failed', 'cancelled'}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def age(stamp):
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(stamp)).total_seconds()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inventory(state):
    totals = {p: 0 for p in state['parts']}
    for job in state['jobs'].values():
        if job['run'] == state['run']:
            for part, count in job.get('good', {}).items():
                totals[part] += count
    return totals


def remaining(state):
    have = inventory(state)
    return {p: max(0, spec['required'] - have[p]) for p, spec in state['parts'].items()}


def uninspected(job):
    return {p: n - job.get('good', {}).get(p, 0) - job.get('bad', {}).get(p, 0)
            for p, n in job['parts'].items()
            if n > job.get('good', {}).get(p, 0) + job.get('bad', {}).get(p, 0)}


def next_step(state):
    active = [j['id'] for j in state['jobs'].values() if j['status'] in ACTIVE]
    if active:
        return {'action': 'check_active_job', 'jobs': active,
                'instruction': 'Inspect live Bambu status. Do not send another job.'}
    if not state.get('enabled', True):
        return {'action': 'automation_paused', 'instruction': 'Print continuation is paused. An explicit user next/continue can resume it.'}
    waiting = [j['id'] for j in state['jobs'].values()
               if j['run'] == state['run'] and j['status'] in TERMINAL and uninspected(j)]
    if waiting:
        return {'action': 'inspect_parts', 'jobs': waiting,
                'instruction': 'Record physically usable and failed counts; printer completion alone is not acceptance.'}
    missing = remaining(state)
    if not any(missing.values()):
        return {'action': 'kit_complete', 'instruction': 'All 34 production parts are accepted. Stop the print follow-up.'}
    for plate_id in state['production_order']:
        plate = state['plates'][plate_id]
        needed = {p: min(n, missing[p]) for p, n in plate['parts'].items() if missing[p]}
        if needed:
            candidates = [k for k, v in state['plates'].items() if v['parts'] == needed]
            return {'action': 'prepare_and_print' if candidates else 'prepare_partial_plate',
                    'plate': candidates[-1] if candidates else None,
                    'based_on': plate_id, 'parts': needed,
                    'bed_clear_record': state['printer'].get('bed_clear'),
                    'instruction': 'Check live idle printer and fresh clear bed, inspect slice/settings, reserve, then send through Computer Use.'}
    raise ValueError('Missing parts have no production plate.')


def counts(value, state):
    require(isinstance(value, dict), 'Parts must be a quantity mapping.')
    require(all(p in state['parts'] and type(n) is int and n >= 0 for p, n in value.items()),
            'Unknown part, negative count, or non-integer count.')
    return {p: n for p, n in value.items() if n}


def checked_file(project, relative, digest=None):
    path = (project / relative).resolve()
    require(path.is_relative_to(project.resolve()) and path.is_file(), 'Prepared file must exist inside this project.')
    require(path.suffix.lower() == '.3mf', 'Prepared plate must be a 3MF.')
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest:
        require(actual == digest, 'Prepared file changed. Reinspect the slice and register the reviewed file before sending.')
    return actual


def apply_event(state, event, project, stamp=None):
    stamp = stamp or now()
    require(event.get('id') and event.get('evidence', '').strip(), 'Every update needs a stable id and evidence.')
    previous = next((e for e in state['events'] if e['id'] == event['id']), None)
    if previous:
        require(previous['event'] == event, 'Event id already used for different content.')
        return False
    kind = event.get('type')
    jobs = state['jobs']
    printer = state['printer']
    if kind == 'observe':
        require(event['state'] in {'idle', 'printing', 'paused', 'finished', 'error', 'unknown'}, 'Invalid printer state.')
        job_id = event.get('job')
        if job_id:
            require(job_id in jobs, 'Unknown job. Reconcile identity before updating.')
            status = event.get('job_status')
            if status:
                require(status in ACTIVE | TERMINAL, 'Invalid job status.')
                require(jobs[job_id]['status'] not in TERMINAL or status == jobs[job_id]['status'],
                        'Terminal job cannot return to printing. Register a new job for a reprint.')
                jobs[job_id]['status'] = status
                jobs[job_id]['observed_at'] = stamp
                jobs[job_id]['evidence'] = event['evidence']
        printer['observation'] = {'at': stamp, 'state': event['state'], 'job': job_id,
                                  'name': event.get('name'), 'details': event.get('details', {}),
                                  'evidence': event['evidence']}
        if event['state'] != 'idle':
            printer['bed_clear'] = None
    elif kind == 'inspect':
        job = jobs[event['job']]
        require(job['status'] in TERMINAL, 'Wait for job termination before accepting removed pieces.')
        good = counts(event.get('good', {}), state)
        bad = counts(event.get('bad', {}), state)
        require(set(good) | set(bad) <= set(job['parts']), 'These parts are not in this job.')
        require(all(good.get(p, 0) + bad.get(p, 0) <= n for p, n in job['parts'].items()), 'Inspection exceeds printed quantity.')
        # Absolute totals for this job, so corrections and repeated observations never add duplicates.
        job.update(good=good, bad=bad, inspected_at=stamp, inspection_evidence=event['evidence'])
    elif kind == 'bed_clear':
        require(not any(j['status'] in ACTIVE for j in jobs.values()), 'A job is still active or send outcome is unresolved.')
        obs = printer.get('observation', {})
        require(obs.get('state') == 'idle' and 0 <= age(obs['at']) <= 600, 'Observe the idle printer live first.')
        printer['bed_clear'] = {'at': stamp, 'evidence': event['evidence']}
    elif kind == 'add_plate':
        plate_id = event['plate']
        require(plate_id not in state['plates'], 'Use a new plate id for a new reviewed file revision.')
        parts = counts(event['parts'], state)
        require(parts, 'Empty plate.')
        require(all(n <= remaining(state)[p] for p, n in parts.items()), 'Plate exceeds the missing quantity.')
        digest = checked_file(project, event['file'])
        state['plates'][plate_id] = {'parts': parts, 'file': event['file'], 'sha256': digest,
                                     'reviewed_at': stamp, 'evidence': event['evidence']}
    elif kind == 'reserve':
        require(event['job'] not in jobs, 'Job id already exists.')
        plan = next_step(state)
        require(plan['action'] in {'prepare_and_print', 'prepare_partial_plate'}, 'A prior job needs reconciliation or inspection, or the kit is complete.')
        require(event['plate'] in state['plates'], 'Unknown prepared plate.')
        plate = state['plates'][event['plate']]
        require(plate['parts'] == plan['parts'], 'Plate does not match the next missing quantities.')
        obs = printer.get('observation', {})
        require(obs.get('state') == 'idle' and 0 <= age(obs['at']) <= 600, 'A fresh live idle observation is required before sending.')
        clear = printer.get('bed_clear')
        require(clear and 0 <= age(clear['at']) <= 1800, 'Fresh clear-bed evidence is needed and is consumed by each send.')
        checked_file(project, plate['file'], plate['sha256'])
        jobs[event['job']] = {'id': event['job'], 'run': state['run'], 'plate': event['plate'],
                              'parts': copy.deepcopy(plate['parts']), 'status': 'sending',
                              'reserved_at': stamp, 'file_sha256': plate['sha256'],
                              'good': {}, 'bad': {}, 'evidence': event['evidence']}
        printer['bed_clear'] = None
    elif kind == 'void_send':
        job = jobs[event['job']]
        require(job['status'] == 'sending', 'Only an unstarted reservation can be voided.')
        obs = printer.get('observation', {})
        require(obs.get('state') == 'idle' and 0 <= age(obs['at']) <= 600, 'Inspect the live printer before concluding the send never started.')
        job.update(status='not_sent', evidence=event['evidence'], resolved_at=stamp)
        printer['bed_clear'] = None
    elif kind == 'control':
        require(type(event['enabled']) is bool, 'enabled must be a boolean.')
        state['enabled'] = event['enabled']
    elif kind == 'reset':
        state['runs'].append({'id': state['run'], 'closed_at': stamp, 'reason': event['evidence']})
        state['run'] = event['new_run']
        state['enabled'] = False
        require(not any(r['id'] == state['run'] for r in state['runs']), 'New run id must be unique.')
        printer['bed_clear'] = None
        # Keep live/uncertain jobs across runs. Their physical activity still blocks another send.
    elif kind == 'note':
        state['notes'].append({'at': stamp, 'text': event['evidence']})
    else:
        raise ValueError('Unknown event type: ' + str(kind))
    state['events'].append({'id': event['id'], 'at': stamp, 'event': event})
    state['revision'] += 1
    state['updated_at'] = stamp
    return True


def report(state):
    have = inventory(state)
    return {'run': state['run'], 'enabled': state.get('enabled', True), 'revision': state['revision'], 'updated_at': state['updated_at'],
            'accepted': {p: {'usable': have[p], 'required': spec['required']} for p, spec in state['parts'].items()},
            'printer': state['printer'], 'jobs': state['jobs'], 'calibration': state['calibration'],
            'next': next_step(state)}


def write_checkpoint(project, state):
    value = report(state)
    lines = ['# Chandelier print progress', '', 'Generated from print_tracking/ledger.json. Observations are timestamped, not live.', '',
             f"Run: {state['run']} | Revision: {state['revision']} | Updated: {state['updated_at']}", '',
             '| Part | Accepted usable | Required |', '|---|---:|---:|']
    for p, spec in state['parts'].items():
        lines.append(f"| {spec['label']} | {value['accepted'][p]['usable']} | {spec['required']} |")
    lines += ['', 'Next action: ' + value['next']['action'], '', value['next']['instruction'], '',
              'Printer observation:', '```json', json.dumps(state['printer'], indent=2), '```', '',
              'Jobs:', '```json', json.dumps(state['jobs'], indent=2), '```', '',
              'Coupon fit: ' + state['calibration']['evidence'], '',
              'Use $chandelier-print next to continue operating Bambu Studio. Use $chandelier-print reset to archive this run and reset production counts.', '']
    (project / 'print_tracking/STATUS.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=DEFAULT_PROJECT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('next')
    apply = sub.add_parser('apply')
    apply.add_argument('event_file', type=Path)
    reset = sub.add_parser('reset')
    reset.add_argument('--event-id', required=True)
    reset.add_argument('--evidence', required=True)
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    path = root / 'print_tracking/ledger.json'
    require(path.is_file(), f'No ledger at {path}. Restore the project checkpoint; do not assume zero prior prints.')
    with open(path.parent / '.ledger.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(path.read_text())
        require(state['schema'] == 1, 'Unsupported ledger schema.')
        if args.command in {'apply', 'reset'}:
            if args.command == 'apply':
                event = json.loads(args.event_file.read_text())
                require(event.get('type') != 'reset', 'Use the reset command so an archive is created.')
            else:
                old = next((e for e in state['events'] if e['id'] == args.event_id), None)
                event = old['event'] if old else {'id': args.event_id, 'type': 'reset', 'evidence': args.evidence,
                                                  'new_run': 'run-' + uuid.uuid4().hex[:12]}
                require(event['type'] == 'reset' and event['evidence'] == args.evidence, 'Reset event id was reused for different content.')
            updated = copy.deepcopy(state)
            if apply_event(updated, event, root):
                archive = path.parent / 'history' / f"revision-{state['revision']:06d}.json"
                if not archive.exists():
                    atomic_json(archive, state)
                atomic_json(path, updated)
                state = updated
            write_checkpoint(root, state)
        print(json.dumps(next_step(state) if args.command == 'next' else report(state), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print('Ledger stopped: ' + str(exc), file=sys.stderr)
        sys.exit(2)
