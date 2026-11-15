"""Collect dated REDLINE narrative evidence without starting Unreal or ROS.

This records observed reports and current file hashes. A missing/stale report,
an asset import and a gameplay acceptance are different states. It deliberately
does not convert a collection of partial checks into a completed milestone.
No account metadata, signed download URL, log body or secret value is copied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re


SCHEMA = 'redline.narrative-preview.verification.v1'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def local_path(value):
    """Accept receipts from either Windows or WSL without guessing a new cache."""
    value = str(value).replace('\\', '/')
    if os.name != 'nt' and re.match(r'^[A-Za-z]:/', value):
        value = '/mnt/'+value[0].lower()+value[2:]
    elif os.name == 'nt' and re.match(r'^/mnt/[a-z]/', value):
        value = value[5].upper()+':/'+value[7:]
    return Path(value)


def label(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def artifact(path, root):
    record = {'path': label(path, root), 'exists': path.is_file()}
    if record['exists']:
        stat = path.stat()
        record.update(sha256=digest(path), bytes=stat.st_size,
                      modified_at_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat())
    return record


def read_report(path, root):
    receipt = artifact(path, root)
    if not receipt['exists']:
        return receipt, None
    try:
        return receipt, json_read(path)
    except (ValueError, OSError) as error:
        receipt['read_error'] = type(error).__name__
        return receipt, None


def match_sources(records, root):
    results = []
    for expected in records:
        path = root/str(expected['path']).replace('\\', '/')
        current = artifact(path, root)
        results.append({'path': current['path'], 'exists': current['exists'],
                        'expected_sha256': expected['sha256'].lower(),
                        'current_sha256': current.get('sha256'),
                        'matches': current.get('sha256') == expected['sha256'].lower()})
    return {'all_match': bool(results) and all(r['matches'] for r in results), 'files': results}


def build_evidence(root, override):
    receipt, report = read_report(root/'test-results/t4-build-source.json', root)
    result = {'receipt': receipt, 'status': 'MISSING'}
    if not report:
        return result, local_path(override) if override else None
    source = root/'unreal/Redline'
    cache = local_path(override or report['workspace'])
    expected = report.get('files', [])
    source_check = match_sources(expected, source)
    cache_check = match_sources(expected, cache)
    # The editor regenerates its local Android File Server credential after
    # launch. Never print it or mistake that sole runtime field for new code.
    mismatches=[r['path'].replace('\\','/') for r in cache_check['files'] if not r['matches']]
    runtime_token_only=False
    if mismatches==['Config/DefaultEngine.ini'] and source_check['all_match']:
        source_config=(source/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
        cached_config=(cache/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
        strip=lambda value:re.sub(r'(?m)^SecurityToken=.*\n?', '', value).rstrip()
        runtime_token_only=strip(source_config)==strip(cached_config)
    excluded = {'binaries', 'intermediate', 'saved', 'deriveddatacache', 'content'}
    current_names = {p.relative_to(source).as_posix() for p in source.rglob('*')
                     if p.is_file() and not any(v.lower() in excluded for v in p.relative_to(source).parts[:-1])}
    expected_names = {str(r['path']).replace('\\', '/') for r in expected}
    exact = current_names == expected_names
    built = report.get('build_exit_code') == 0 and report.get('source_snapshot_verified') is True
    current = built and source_check['all_match'] and cache_check['all_match'] and exact
    status = ('CURRENT_VERIFIED_BUILD' if current else 'CURRENT_BUILD_RUNTIME_TOKEN_REGENERATED' if built and source_check['all_match'] and exact and runtime_token_only else 'BUILD_NOT_FINISHED'
              if report.get('build_exit_code') is None else 'STALE_OR_FAILED_BUILD')
    result.update(status=status,
                  recorded_at_utc=report.get('created_at_utc'), exit_code=report.get('build_exit_code'),
                  source=label(source, root), cache=str(cache), recorded_snapshot_verified=report.get('source_snapshot_verified'),
                  current_input_file_set_matches=exact, added_files=sorted(current_names-expected_names),
                  removed_files=sorted(expected_names-current_names), source_inputs=source_check, cache_inputs=cache_check,
                  only_runtime_generated_credential_differs=runtime_token_only)
    return result, cache


def content_evidence(root, cache):
    source = root/'unreal/Redline/Content'
    result = {'scope': 'Current native content bytes only; equality is not visual or collision acceptance',
              'status': 'MISSING', 'groups': []}
    if cache is None:
        return result
    for group in ('Prologue', 'EVAFixtures'):
        first, second = source/group, cache/'Content'/group
        source_files = {p.relative_to(first).as_posix(): p for p in first.rglob('*') if p.is_file()} if first.exists() else {}
        cache_files = {p.relative_to(second).as_posix(): p for p in second.rglob('*') if p.is_file()} if second.exists() else {}
        rows = []
        for name in sorted(source_files.keys() | cache_files.keys()):
            a, b = source_files.get(name), cache_files.get(name)
            ah, bh = digest(a) if a else None, digest(b) if b else None
            rows.append({'file': name, 'runtime_file': Path(name).suffix.lower() in
                         ('.uasset', '.umap', '.uexp', '.ubulk', '.uptnl', '.json'),
                         'source_sha256': ah, 'cache_sha256': bh,
                         'equal': a is not None and b is not None and ah == bh,
                         'source_bytes': a.stat().st_size if a else None,
                         'cache_bytes': b.stat().st_size if b else None})
        runtime = [r for r in rows if r['runtime_file']]
        result['groups'].append({'group': group, 'files': rows, 'file_count': len(rows),
                                  'all_equal': bool(rows) and all(r['equal'] for r in rows),
                                  'all_runtime_equal': bool(runtime) and all(r['equal'] for r in runtime)})
    result['status'] = ('CURRENT_MATCH' if all(g['all_equal'] for g in result['groups']) else
                        'CURRENT_RUNTIME_MATCH_METADATA_DIFFERS' if all(g['all_runtime_equal'] for g in result['groups'])
                        else 'MISSING_OR_DIFFERENT_RUNTIME_CONTENT')
    return result


def automation_evidence(root, build):
    receipt, report = read_report(root/'test-results/firstperson-tests-index.json', root)
    result = {'receipt': receipt, 'status': 'MISSING',
              'scope': 'Native automation; key holding, audio routing and room traversal require live checks'}
    if not report:
        return result
    tests = [{'name': t.get('fullTestPath'), 'state': t.get('state'), 'warnings': t.get('warnings', 0),
              'errors': t.get('errors', 0)} for t in report.get('tests', [])]
    bad = [t for t in tests if t['state'] not in ('Success', 'SuccessWithWarnings') or t['errors']]
    result.update(status='RECORDED_PASS' if tests and not bad else 'RECORDED_FAILURE_OR_INCOMPLETE',
                  report_created_on=report.get('reportCreatedOn'), tests=tests, test_count=len(tests),
                  succeeded=report.get('succeeded'), succeeded_with_warnings=report.get('succeededWithWarnings'),
                  failed=report.get('failed'), not_run=report.get('notRun'),
                  current_build_verified=build.get('status') == 'CURRENT_VERIFIED_BUILD',
                  binding_limit='Report has no binary digest binding. Current build hashes are recorded separately; passing results remain dated observations.')
    return result


def scene_evidence(root, cache, name, scope):
    receipt, report = read_report(root/'test-results'/name, root)
    result = {'receipt': receipt, 'scope': scope, 'status': 'MISSING'}
    if not report:
        return result
    result.update(status='RECORDED_PASS' if report.get('passed') is True else 'RECORDED_FAILURE_OR_INCOMPLETE',
                  recorded_at_utc=report.get('created_at_utc'), reported_passed=report.get('passed'),
                  recorded_scope=report.get('scope'), source_inputs=match_sources(report.get('sources', []), root))
    if name == 'command-rooms-verification.json':
        result['checks'] = [{'name': c.get('name'), 'passed': c.get('passed')} for c in report.get('checks', [])]
        result['voices'] = [{'id': v['id'], 'passed': v.get('passed'), 'sha256': v.get('sha256'),
                             'duration_s': v.get('pcm', {}).get('duration_s')} for v in report.get('voices', [])]
        expected = report.get('runtime_script_sha256')
        path = cache/'Content/Prologue/script.json' if cache else None
        current = digest(path) if path and path.is_file() else None
        result['runtime_script'] = {'recorded_sha256': expected, 'current_cache_sha256': current,
                                     'matches': expected is not None and expected == current}
    else:
        for key in ('map', 'narration_method', 'narrative_duration_s', 'mission_intros', 'player_start_map_xyz_m', 'airlock'):
            result[key] = report.get(key)
        result['imported_tripo_assets'] = [{'id': a.get('id'), 'unit_error_cm': a.get('unit_error_cm'),
                                            'triangles': a.get('triangles'), 'source_sha256': a.get('source_sha256')}
                                           for a in report.get('tripo_assets', [])]
    return result


def sprint_evidence(root):
    directory = root/'test-results/sprint-ros-LjcbbqV7'
    receipt, report = read_report(directory/'verification.json', root)
    result = {'receipt': receipt, 'status': 'MISSING', 'scope': 'Installed ROS sprint metering and launch, isolated DDS'}
    if report:
        for key in ('workspace', 'source_tree_sha256', 'ros_source_snapshot_verified', 'frozen_core',
                    'frozen_core_verified', 'colcon_build', 'tests', 'installed_sprint_launch_probe'):
            result[key] = report.get(key)
        result['status'] = 'RECORDED_PASS' if report.get('passed') is True else 'RECORDED_FAILURE_OR_INCOMPLETE'
        _, manifest = read_report(directory/'ros-workspace.json', root)
        if manifest:
            result['current_ros_source_inputs'] = match_sources(manifest.get('files', []), root/'ros_ws/src')
    _, metering = read_report(root/'test-results/sprint-metering-verification.json', root)
    if metering:
        result['core_tests'] = metering.get('core_tests')
        result['current_metering_sources'] = match_sources(metering.get('files', []), root)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--build-root', help='Explicit cache path; default from the recorded build')
    parser.add_argument('--output', type=Path, default=Path('docs/verification/NARRATIVE_PREVIEW.json'))
    args = parser.parse_args()
    root = args.repo.resolve()
    build, cache = build_evidence(root, args.build_root)
    result = {
        'schema': SCHEMA, 'created_at_utc': utc_now(), 'status': 'SCENARIO',
        'overall_status': 'PARTIAL_PREVIEW', 'milestone_complete': False,
        'scope': 'Dated local evidence collection for the narrative preview, not T6 or complete game acceptance',
        'collector': artifact(Path(__file__).resolve(), root),
        'unreal_build': build,
        'native_automation': automation_evidence(root, build),
        'scene_import': scene_evidence(root, cache, 'prologue-import.json', 'Import, source and scale checks'),
        'saved_room_inspection': scene_evidence(root, cache, 'command-rooms-verification.json', 'Saved asset/map inspection only'),
        'sprint_ros': sprint_evidence(root),
        'source_cache_content': content_evidence(root, cache),
        'unverified': [
            'This collector does not observe or confirm live gameplay, current audio device output or user listening quality.',
            'First-person automation toggles cameras; physical key hold, mouse look and initial control pitch need live input evidence.',
            'Indoor capsule passage, doorway closure around the player and full room-to-surface traversal need runtime collision checks.',
            'MotionWindow estimates endpoint displacement over its time window; tight turns/backtracking can undercount traveled speed.',
            'Sprint physiology is an explicit SCENARIO extrapolation of the walking formula, not validated running physiology.',
            'Facial lip sync, final station gameplay, robot escort and full T6 S1 alarm/line-shrink acceptance remain separate work.',
        ],
        'authority': {'robot_physics_control': 'ROS/Gazebo', 'human_character': 'Unreal',
                      'mission_phase_and_pet': 'ROS; narrative cameras/skip do not advance them'},
    }
    output = args.output if args.output.is_absolute() else root/args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'report': label(output, root), 'overall_status': result['overall_status'],
                      'build': build['status'], 'automation': result['native_automation']['status'],
                      'scene_import': result['scene_import']['status'],
                      'room_inspection': result['saved_room_inspection']['status'],
                      'content': result['source_cache_content']['status']}))


if __name__ == '__main__':
    main()
