"""Write the small portable evidence index for the observed local T3 runs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent


def artifact(path):
    path=ROOT/path
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':digest,'bytes':path.stat().st_size}


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))


def main():
    build=Path('test-results/t3-build-uEoow3Jk')
    reports=list((ROOT/build/'ros/build').glob('*/test_results/*/*.xml'))
    actual=sum(len(ET.parse(p).getroot().findall('.//testcase')) for p in reports)
    if actual!=49:raise ValueError(f'Unexpected ROS test count {actual}')
    extra=ET.parse(ROOT/'test-results/t3-terrain-surface.xml').getroot()
    if len(extra.findall('.//testcase'))!=18:raise ValueError('Unexpected terrain helper test count')
    for path in reports+[ROOT/'test-results/t3-terrain-surface.xml']:
        if ET.parse(path).getroot().findall('.//failure') or ET.parse(path).getroot().findall('.//error'):
            raise ValueError('Cannot record a failed test report as pass')
    imagery=read('data/engines/BXW/surface-v1/imagery.json')
    snapshot=artifact('docs/verification/source-metadata/T3_fetch_t3_imagery_v1.py')
    if snapshot['sha256']!=imagery['identity']['helper_sha256']:raise ValueError('Imagery executed helper snapshot mismatch')
    surface=read('data/engines/BXW/surface-v1/manifest.json')
    blender=read('data/engines/BXW/surface-blender-v1/verification.json')
    runtime=read('test-results/t3-runtime-b9oXFpQp/result.json')
    navigation=runtime['navigation'];navigation.pop('estimated_trajectory_xy',None)
    ue=read('test-results/t3-unreal-import.json')
    if not (runtime['passed'] and blender['passed'] and ue['passed']):raise ValueError('One required surface check failed')
    result={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'milestone':'T3','milestone_complete':False,'surface_package_ready':True,
        'pending':['Observed RViz click goal arrival acceptance',
                   'Full Unreal rendered scene / human terrain collision / LOD performance',
                   'Application T4 C++/ROS bridge integration'],
        'ros_build':{'workspace_snapshot':read(build/'ros-workspace.json'),
                     'actual_tests':actual,'ctest_wrappers':7,'colcon_reported_total':56,
                     'reports':[artifact(p.relative_to(ROOT)) for p in reports]},
        'terrain_helper_tests':{'count':18,'report':artifact('test-results/t3-terrain-surface.xml'),
                                 'warnings':'3 Rasterio is_tiled PendingDeprecationWarning'},
        'surface':{'manifest':artifact('data/engines/BXW/surface-v1/manifest.json'),
                   'meshes':len(surface['meshes']),'triangles':surface['budgets']['triangles'],
                   'qa':surface['qa'],'origin':surface['map_origin']},
        'imagery':{'manifest':artifact('data/engines/BXW/surface-v1/imagery.json'),
                   'executed_helper_snapshot':snapshot,'source':imagery['source'],
                   'source_metadata':imagery['source_metadata'],'atlases':imagery['atlases'],
                   'credit':imagery['credit'],'limits':imagery['limits']},
        'blender':blender,'unreal_representative_import':ue,
        'gazebo_visible_surface':{'observed':True,'method':'Computer Use: actual Gazebo GUI screenshot',
                                   'run':'test-results/t3-runtime-1iMx5ewX',
                                   'navigation_in_that_run':'RViz target not received; not a navigation pass'},
        'programmatic_navigation':navigation,
        'runtime_result':artifact('test-results/t3-runtime-b9oXFpQp/result.json'),
        'runtime_renderer':runtime['render_device_lines'],'owned_process_exit_codes':runtime['processes'],
        'outputs':[artifact(p) for p in [
            'data/engines/BXW/surface-blender-v1/BXW_surface_overview.png',
            'data/engines/BXW/surface-blender-v1/BXW_surface.glb',
            'data/engines/BXW/surface-blender-v1/BXW_surface.blend']],
        'scripts':[artifact(Path('scripts')/name) for name in [
            'export_t3_terrain.py','fetch_t3_imagery.py','package_t3_surface.py',
            'blender_t3_surface.py','verify_t3_unreal_import.py','t3_supervisor.py']],
        'limits':['Source CRS/pixel/geometry checks do not prove absolute DEM/ortho feature registration.',
                  'FBX smoothing-group warning remains for final normal/appearance review.',
                  'Robot dynamics and calibration are SCENARIO, not certified hardware behaviour.',
                  'No Git/GitHub changes or Tripo generation by this T3 work.']}
    target=ROOT/'docs/verification/T3_LOCAL_2026-11-14.json'
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'record':str(target),'surface_ready':True,'ros_tests':actual,'helper_tests':18,
                      'blender_meshes':len(blender['checks']),'ue_representative_meshes':len(ue['checks']),
                      'programmatic_navigation_passed':navigation['passed'],'milestone_complete':False},indent=2))


if __name__=='__main__':main()
