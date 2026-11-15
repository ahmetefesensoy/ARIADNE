"""Measure the delivered rover without changing source assets or physics."""
from datetime import datetime,timezone
import hashlib,json,math
from pathlib import Path

root=Path(__file__).resolve().parent.parent
folder=root/'assets/incoming/rover_1'
asset=json.loads((folder/'asset.json').read_text())
records=[]
for part in asset['parts']:
    if not part['source_name'].startswith('wheel_'):continue
    path=folder/'gazebo/parts'/(part['name'].replace('_LOD0','_Gazebo')+'.obj')
    vertices=[]
    with path.open() as stream:
        for line in stream:
            if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:4])))
    low=[min(v[i] for v in vertices) for i in range(3)]
    high=[max(v[i] for v in vertices) for i in range(3)]
    diameter=2*max(math.hypot(v[0],v[2]) for v in vertices)
    records.append({'part':part['source_name'],'pivot_map_master_m':part['pivot_m'],
        'mesh':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'dimensions_m':[b-a for a,b in zip(low,high)],
        'radius_about_joint_y_m':diameter/2,'diameter_about_joint_y_m':diameter,
        'uniform_scale_to_0_5m_wheel':.5/diameter})
report={'created_at_utc':datetime.now(timezone.utc).isoformat(),
    'asset_sha256':hashlib.sha256((folder/'asset.json').read_bytes()).hexdigest(),
    'source':'delivered NASA-derived visual, not flight CAD',
    'master_axes':asset['master']['axes'],'master_dimensions_m':asset['master']['dimensions_m'],
    'reference':{'wheel_diameter_m':.5,'wheel_width_m':.4,'rover_mass_kg':899,
        'nominal_body_length_excluding_arm_m':3.0,
        'sources':['https://robotics.jpl.nasa.gov/media/documents/fmwi-rankin-2022-0225-final.pdf',
                   'https://mars.nasa.gov/internal_resources/822/']},
    'wheels':records,'sources_modified':False,
    'limits':['Mesh radial extent includes art grousers and may differ from nominal rolling radius.',
              'Model total length includes posed appendages; never normalize it to body-only length.',
              'Wheel mesh audit is not inertia, suspension, friction or drive calibration.',
              'Current simplified test robot has not been replaced by this audit.']}
target=root/'docs/verification/ROVER_SCALE_AUDIT.json'
target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
