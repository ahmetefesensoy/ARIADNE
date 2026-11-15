"""Read-only Blender mesh probes for generated REDLINE interiors.

Usage:
  blender --background --python scripts/inspect_interior_topology.py -- <repo>
  blender --background --python scripts/inspect_interior_topology.py -- <repo> \
      --asset command --fit-cm command=600,360,280 --yaw command=90

No Blender object, mesh, material or saved scene is changed. Optional --fit-cm
constructs a temporary analysis BVH in the proposed Unreal dimensions (metres),
including Blender-to-Unreal Y handedness and the specified actor yaw. Reports
are written to test-results only. Rays inspect rendered triangles; they cannot
prove capsule movement, a pressure seal, material appearance or camera comfort.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


NAMES = ('command', 'lab', 'corridor', 'airlock', 'lounge')
CARDINAL = {'+X': (1, 0, 0), '-X': (-1, 0, 0),
            '+Y': (0, 1, 0), '-Y': (0, -1, 0)}


def named_values(values, count):
    result = {}
    for raw in values:
        name, value = raw.split('=', 1)
        if name not in NAMES: raise ValueError('Unknown interior '+name)
        numbers = [float(item) for item in value.split(',')]
        if len(numbers) != count or not all(math.isfinite(x) for x in numbers):
            raise ValueError('Invalid analysis fit/yaw: '+raw)
        if count > 1 and not all(x > 0 for x in numbers):
            raise ValueError('Fit dimensions must be positive: '+raw)
        result[name] = numbers
    return result


def bounds(points):
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return low, high


def vector(value):
    return [float(v) for v in value] if value is not None else None


def ray(tree, origin, direction, length):
    point, normal, index, distance = tree.ray_cast(Vector(origin), Vector(direction), length)
    return {'hit': point is not None, 'point_m': vector(point), 'normal': vector(normal),
            'distance_m': float(distance) if distance is not None else None,
            'triangle': int(index) if index is not None else None}


def segment(tree, start, end):
    a, b = Vector(start), Vector(end)
    delta = b-a
    length = delta.length
    if length <= 1e-6: return {'clear': True, 'length_m': length, 'hit': None}
    hit = ray(tree, a, delta/length, max(0, length-.002))
    return {'clear': not hit['hit'], 'length_m': length,
            'hit': hit if hit['hit'] else None}


def height_clusters(samples, tolerance):
    groups = []
    for item in sorted((s for s in samples if s['hit']), key=lambda s: s['point_m'][2]):
        height = item['point_m'][2]
        if not groups or abs(height-groups[-1]['mean_z_m']) > tolerance:
            groups.append({'mean_z_m': height, 'samples': []})
        group = groups[-1]
        group['samples'].append(item)
        group['mean_z_m'] = sum(s['point_m'][2] for s in group['samples'])/len(group['samples'])
    return [{'mean_z_m': g['mean_z_m'], 'sample_count': len(g['samples']),
             'xy_m': [s['point_m'][:2] for s in g['samples']]} for g in groups]


def inspect(repo, name, fit_cm=None, yaw_deg=0, torso_height=1.0, body_height=1.85, radius=.32):
    source = repo/f'data/engines/prologue-tripo-v1/prologue_{name}/derived.blend'
    if not source.exists(): return {'asset': name, 'state': 'NOT_READY', 'passed': False,
                                    'source': str(source.relative_to(repo)).replace('\\', '/')}
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render]
    if not objects: raise RuntimeError('No render mesh in '+str(source))
    points, triangles = [], []
    for obj in objects:
        offset = len(points)
        points.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        obj.data.calc_loop_triangles()
        triangles.extend(tuple(offset+index for index in tri.vertices) for tri in obj.data.loop_triangles)
    low, high = bounds(points)
    original_bounds = {'low_m': vector(low), 'high_m': vector(high), 'dimensions_m': vector(high-low)}
    frame = 'Blender source axes +X,+Y,+Z; not yet scene-fit'
    if fit_cm:
        # Fit a copied point list; never scale or rotate scene objects. First
        # reflect Y exactly as UE import does, then rotate yaw, then fit bounds.
        rotation = Matrix.Rotation(math.radians(yaw_deg), 3, 'Z')
        reflected = [rotation @ Vector((p.x, -p.y, p.z)) for p in points]
        fit_low, fit_high = bounds(reflected)
        size = fit_high-fit_low
        scale = Vector(tuple((fit_cm[i]/100)/size[i] for i in range(3)))
        centre = (fit_low+fit_high)/2
        points = [Vector(((p.x-centre.x)*scale.x, (p.y-centre.y)*scale.y,
                          (p.z-fit_low.z)*scale.z)) for p in reflected]
        low, high = bounds(points)
        frame = 'proposed Unreal world axes (metres), Y reflected then actor yaw then explicit dimensions fit'
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True, epsilon=0)
    size = high-low
    centre = (high+low)/2
    seed_z = low.z+size.z*.55
    length = max(size)*3+4
    floor_samples = []
    # Central 60% grid samples separate a planning table/bench top from the
    # lower consistent floor cluster. A central tabletop is never called floor
    # merely because it is the first downward triangle.
    for gx in range(5):
        for gy in range(5):
            origin = Vector((centre.x+(gx-2)*size.x*.15, centre.y+(gy-2)*size.y*.15, seed_z))
            item = ray(tree, origin, (0, 0, -1), length)
            item['seed_m'] = vector(origin)
            floor_samples.append(item)
    tolerance = max(.018, size.z*.008)
    clusters = height_clusters(floor_samples, tolerance)
    supporting = [g for g in clusters if g['sample_count'] >= 4]
    chosen = supporting[0] if supporting else None
    result = {'asset': name, 'state': 'INSPECTED', 'passed': False,
              'source': str(source.relative_to(repo)).replace('\\', '/'), 'source_sha256': digest,
              'frame': frame, 'analysis_fit_dimensions_cm': fit_cm, 'analysis_actor_yaw_deg': yaw_deg if fit_cm else None,
              'source_bounds': original_bounds,
              'bounds': {'low_m': vector(low), 'high_m': vector(high), 'dimensions_m': vector(size)},
              'mesh_count': len(objects), 'triangle_count': len(triangles),
              'floor_seed_z_m': seed_z, 'floor_samples': floor_samples,
              'floor_clusters': clusters, 'floor_cluster_tolerance_m': tolerance,
              'floor_anchor_m': chosen['mean_z_m'] if chosen else None,
              'floor_selection_rule': 'lowest height cluster with at least four of 25 central-grid hits; tables reported as separate higher clusters',
              'warnings': [], 'limits': 'Sampled triangle rays are necessary geometry evidence, not a capsule sweep or runtime acceptance.'}
    midheight_origin = Vector((centre.x, centre.y, seed_z))
    result['cardinal_at_midheight'] = {key: ray(tree, midheight_origin, direction, length)
                                      for key, direction in CARDINAL.items()}
    result['open_axes_at_midheight'] = [key for key, item in result['cardinal_at_midheight'].items() if not item['hit']]
    result['centre_vertical'] = {'floor': ray(tree, midheight_origin, (0, 0, -1), length),
                                 'ceiling': ray(tree, midheight_origin, (0, 0, 1), length)}
    if chosen is None:
        result['warnings'].append('No lower consistent floor cluster; do not place pawn from central ray alone.')
        return result
    floor = chosen['mean_z_m']
    torso_z = floor+torso_height
    eye_z = floor+body_height*.92
    centre_torso = Vector((centre.x, centre.y, torso_z))
    if torso_z >= high.z-.05:
        result['warnings'].append('Requested human torso height is above available source/fit bounds.')
    result['human_assumptions_m'] = {'torso_height': torso_height, 'body_height': body_height, 'capsule_radius': radius}
    result['cardinal_at_torso'] = {key: ray(tree, centre_torso, direction, length)
                                   for key, direction in CARDINAL.items()}
    result['open_cardinal_axes'] = [key for key, item in result['cardinal_at_torso'].items() if not item['hit']]
    result['ceiling_over_floor_grid'] = []
    supported_points = []
    for sample in floor_samples:
        if not sample['hit'] or abs(sample['point_m'][2]-floor) > tolerance: continue
        x, y, z = sample['point_m']
        ceiling = ray(tree, (x, y, z+.05), (0, 0, 1), length)
        headroom = ceiling['point_m'][2]-z if ceiling['hit'] else None
        # Missing roof is reported as open sky, not a sealed/complete room.
        result['ceiling_over_floor_grid'].append({'xy_m': [x, y], 'ceiling': ceiling,
                                                 'clearance_m': headroom,
                                                 'open_sky': not ceiling['hit'],
                                                 'human_height_clear': headroom is None or headroom >= body_height+.05})
        supported_points.append((x, y, z))
    result['central_lanes'] = {}
    for axis in ('X', 'Y'):
        along, across = (0, 1) if axis == 'X' else (1, 0)
        lanes = []
        for fraction in (-.22, 0., .22):
            lateral = centre[across]+size[across]*fraction
            samples = []
            for step in range(9):
                p = Vector((centre.x, centre.y, torso_z))
                p[along] = low[along]+size[along]*(.12+.76*step/8)
                p[across] = lateral
                below = ray(tree, p, (0, 0, -1), length)
                foot_z = below['point_m'][2] if below['hit'] else None
                clear_ceiling = ray(tree, (p.x, p.y, floor+.04), (0, 0, 1), length)
                headroom = clear_ceiling['point_m'][2]-floor if clear_ceiling['hit'] else None
                samples.append({'point_m': vector(p), 'below': below,
                                'floor_matches_anchor': foot_z is not None and abs(foot_z-floor) <= max(.07, tolerance*2),
                                'headroom_m': headroom,
                                'headroom_sufficient': headroom is None or headroom >= body_height+.05})
            tracks = []
            for offset in (-radius, 0., radius):
                start = Vector(samples[0]['point_m']); end = Vector(samples[-1]['point_m'])
                start[across] += offset; end[across] += offset
                tracks.append({'lateral_offset_m': offset, 'torso_segment': segment(tree, start, end),
                               'head_segment': segment(tree, (start.x, start.y, eye_z), (end.x, end.y, eye_z))})
            lane_clear = (all(p['floor_matches_anchor'] and p['headroom_sufficient'] for p in samples) and
                          all(t['torso_segment']['clear'] and t['head_segment']['clear'] for t in tracks))
            lanes.append({'lateral_fraction': fraction, 'samples': samples, 'three_lateral_tracks': tracks,
                          'sampled_lane_clear': lane_clear})
        result['central_lanes'][axis] = lanes
    result['sampled_walk_axis_candidates'] = [axis for axis, lanes in result['central_lanes'].items()
                                              if any(lane['sampled_lane_clear'] for lane in lanes)]
    if not result['open_cardinal_axes']:
        result['warnings'].append('All centre torso cardinal rays hit geometry: closed doors/walls/furniture may block the intended opening.')
    if not result['sampled_walk_axis_candidates']:
        result['warnings'].append('No sampled central lane has both consistent floor, human headroom and clear torso/head tracks.')
    corridor_expected = name in ('corridor', 'airlock')
    through_axes = [axis for axis in ('X', 'Y') if '+'+axis in result['open_cardinal_axes'] and '-'+axis in result['open_cardinal_axes']]
    result['open_opposite_axis_pairs'] = through_axes
    if corridor_expected and not through_axes:
        result['warnings'].append('A through corridor/airlock needs two opposite open ends; generated mesh has not demonstrated that.')
    result['passed'] = (bool(result['open_cardinal_axes']) and bool(result['sampled_walk_axis_candidates']) and
                        (not corridor_expected or bool(through_axes)) and torso_z < high.z-.05)
    result['verdict'] = ('SAMPLED_GEOMETRY_CLEAR; runtime capsule/camera checks still required' if result['passed'] else
                         'REVIEW_REQUIRED; do not claim a traversable generated interior')
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Source .blend changed during read-only inspection')
    return result


def main():
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--asset', action='append', choices=NAMES)
    parser.add_argument('--fit-cm', action='append', default=[], metavar='ASSET=X,Y,Z')
    parser.add_argument('--yaw', action='append', default=[], metavar='ASSET=DEGREES')
    parser.add_argument('--torso-height-m', type=float, default=1.0)
    parser.add_argument('--body-height-m', type=float, default=1.85)
    parser.add_argument('--radius-m', type=float, default=.32)
    parsed = parser.parse_args(args)
    if not all(math.isfinite(v) and v > 0 for v in (parsed.torso_height_m, parsed.body_height_m, parsed.radius_m)):
        raise ValueError('Human dimensions must be finite and positive')
    fit = named_values(parsed.fit_cm, 3)
    yaw = named_values(parsed.yaw, 1)
    report = {'schema': 'redline.interior-topology.v1', 'status': 'SCENARIO',
              'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'read_only_assets': True, 'blender_version': bpy.app.version_string, 'assets': [], 'passed': False}
    for name in parsed.asset or ('command', 'lab', 'corridor'):
        item = inspect(parsed.repo.resolve(), name, fit.get(name), yaw.get(name, [0])[0],
                       parsed.torso_height_m, parsed.body_height_m, parsed.radius_m)
        report['assets'].append(item)
        print('REDLINE_INTERIOR_TOPOLOGY '+json.dumps({k: item.get(k) for k in
              ('asset', 'state', 'passed', 'floor_anchor_m', 'open_cardinal_axes', 'sampled_walk_axis_candidates', 'warnings')}), flush=True)
    report['passed'] = bool(report['assets']) and all(item['passed'] for item in report['assets'])
    output = parsed.repo.resolve()/'test-results/interior-topology.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('REDLINE_INTERIOR_TOPOLOGY_REPORT '+str(output), flush=True)


if __name__ == '__main__': main()
