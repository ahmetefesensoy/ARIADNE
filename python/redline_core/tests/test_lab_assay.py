import pytest
from redline_core.lab_assay import lab_ready,model_assay

def sample():return dict(sample_id='smp-1',target_id='T1',state=7,container_id='tube-1',origin_point_m=[0,0,-3500],analysis_point_m=[30,0,-3500],evidence_ids=['ev-1'],provenance_status='SIMULATED')
def recipe():return dict(status='SCENARIO',method='WCL_SCENARIO',seed=7,ph_equilibrium=7.7,ph_sigma=.12,conductivity_ms_cm=1.2,mixing_tau_s=28,note='Authored MODEL; no Gale measurement')
def test_assay_reproducible_and_does_not_change_custody():
    s=sample();a=model_assay(s,recipe(),'req-1',120);assert a==model_assay(s,recipe(),'req-1',120)
    assert a['model_only'] and len(a['series']['ph'])==31 and all(0<=v<=14 for v in a['series']['ph'])
    assert s['analysis_point_m']!=s['origin_point_m'] and s['state']==7
    assert model_assay(s,recipe(),'req-2',120)!=a
@pytest.mark.parametrize('key,value',[('state',6),('container_id',''),('evidence_ids',[]),('analysis_point_m',[0,0,-3500]),('provenance_status','ARCHIVE')])
def test_unready_custody_rejected(key,value):
    s=sample();s[key]=value
    with pytest.raises(ValueError):lab_ready(s)
@pytest.mark.parametrize('duration',[0,20,601,float('nan')])
def test_unvalidated_integration_rejected(duration):
    with pytest.raises(ValueError):model_assay(sample(),recipe(),'req-1',duration)
