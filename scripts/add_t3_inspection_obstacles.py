#!/usr/bin/env python3
"""Add two explicitly SCENARIO static test boxes to the existing bxw server.

Not Martian observations or authored assets. Ground heights are sampled from
the verified terrain collision triangles, solely for fixture placement.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--showcase', action='store_true', help='Add a twelve-box SCENARIO field, not archive rocks')
    args = parser.parse_args()
    module = args.workspace / 'src/redline_gazebo/scripts/prepare_world.py'
    spec = importlib.util.spec_from_file_location('world', module)
    world = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(world)
    manifest = json.loads(args.terrain.read_text())
    fixtures = [('SCENARIO_inspection_east', 153., -305.), ('SCENARIO_inspection_west', 136., -306.)]
    if args.showcase:
        positions = [(137., -300.), (153., -302.), (138., -310.), (152., -313.),
                     (142., -321.), (160., -321.), (160., -307.), (133., -315.),
                     (147., -330.), (155., -335.), (130., -300.), (165., -300.)]
        fixtures = [('SCENARIO_showcase_' + str(index), x, y) for index, (x, y) in enumerate(positions)]
    for tile in manifest['meshes']:
        collision = (args.terrain.parent / tile.get('collision_relative_path', tile['relative_path'])).resolve()
        tile['collision_uri'] = collision.as_uri()
        bounds = tile['bounds_map_m']
        if any(bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]
               for _, x, y in fixtures):
            with collision.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != tile.get('collision_sha256', tile['sha256']):
                raise ValueError('Fixture terrain source hash mismatch')
    record = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'SCENARIO', 'scope': 'static navigation test boxes, not real Martian rocks',
              'world': 'bxw', 'fixtures': []}
    for name, x, y in fixtures:
        height = world.terrain_height(manifest, x, y)
        sdf = ET.Element('sdf', version='1.9')
        model = ET.SubElement(sdf, 'model', name=name)
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = f'{x} {y} {height + 1.5} 0 0 0'
        link = ET.SubElement(model, 'link', name='fixture')
        for kind in ('visual', 'collision'):
            shape = ET.SubElement(link, kind, name=kind)
            box = ET.SubElement(ET.SubElement(shape, 'geometry'), 'box')
            ET.SubElement(box, 'size').text = '1 1 3.5'
        payload = ET.tostring(sdf, encoding='unicode')
        result = subprocess.run(['gz', 'service', '-s', '/world/bxw/create',
            '--reqtype', 'gz.msgs.EntityFactory', '--reptype', 'gz.msgs.Boolean',
            '--timeout', '5000', '--req', 'sdf: ' + json.dumps(payload)],
            capture_output=True, text=True, timeout=8)
        accepted = result.returncode == 0 and 'data: true' in result.stdout
        record['fixtures'].append({'name': name, 'map_xy_m': [x, y],
            'ground_z_m': height, 'center_z_m': height + 1.5, 'size_m': [1., 1., 3.5], 'created': accepted,
            'response': result.stdout + result.stderr})
        if not accepted:
            args.out.write_text(json.dumps(record, indent=2) + '\n')
            raise RuntimeError('Fixture creation failed: ' + name)
    args.out.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
