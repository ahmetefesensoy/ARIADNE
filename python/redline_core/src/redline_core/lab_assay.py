"""Explicit authored wet-chemistry game model; no oxide-to-pH inference."""
import math,hashlib,random
from redline_core.science_operations import checked_id,finite_point

def lab_ready(sample):
    checked_id(sample['sample_id']);checked_id(sample['target_id'])
    if sample.get('state')!=7 or not sample.get('container_id') or not sample.get('evidence_ids'):
        raise ValueError('recorded sample with container and custody evidence required')
    origin=finite_point(sample['origin_point_m']);analysis=finite_point(sample['analysis_point_m'])
    if math.dist(origin,analysis)<1:raise ValueError('sample has not reached a separate laboratory analysis location')
    if sample.get('provenance_status')!='SIMULATED':raise ValueError('model laboratory requires explicit SIMULATED sample')
    return origin,analysis

def model_assay(sample,recipe,request_id,integration_s):
    lab_ready(sample);checked_id(request_id)
    if recipe.get('status')!='SCENARIO' or recipe.get('method')!='WCL_SCENARIO':raise ValueError('explicit SCENARIO recipe required')
    if not math.isfinite(integration_s) or not 60<=integration_s<=600:raise ValueError('integration must be 60–600 scenario seconds')
    eq=float(recipe['ph_equilibrium']);sigma=float(recipe['ph_sigma']);ec=float(recipe['conductivity_ms_cm']);tau=float(recipe['mixing_tau_s'])
    if not (0<=eq<=14 and 0<sigma<=1 and 0<=ec<=20 and 1<=tau<=200):raise ValueError('invalid authored recipe')
    rng=random.Random(int(hashlib.sha256(f"{recipe['seed']}:{request_id}:{sample['sample_id']}".encode()).hexdigest()[:16],16))
    times=[i*integration_s/30 for i in range(31)]
    ph=[max(0,min(14,7+(eq-7)*(1-math.exp(-t/tau))+rng.gauss(0,sigma))) for t in times]
    conductivity=[max(0,ec*(1-math.exp(-t/tau))+rng.gauss(0,.02)) for t in times]
    return {'schema':'redline.science.summary.v1','request_id':request_id,'labels':['pH'],'values':[ph[-1]],'sigma':[sigma],
        'unit':'pH','series':{'time_s':times,'ph':ph,'conductivity_ms_cm':conductivity},'sample_id':sample['sample_id'],
        'noise_calibration':'UNCALIBRATED_SCENARIO','seed':recipe['seed'],'input_ids':["lab_assays_BXW.yaml",*sample['evidence_ids']],
        'integration_s':integration_s,'limitation':recipe['note'],'model_only':True}
