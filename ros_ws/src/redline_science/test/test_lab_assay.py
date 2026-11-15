import json,time
from pathlib import Path
import pytest,rclpy,yaml
from rclpy.parameter import Parameter
from rclpy.executors import SingleThreadedExecutor
from redline_msgs.srv import AnalyzeSample
from redline_msgs.msg import InstrumentProduct,EvidenceRecord
from std_msgs.msg import String
from redline_science.lab_assay import LabAssay

@pytest.mark.parametrize('duration',[0.,-1.,float('nan'),float('inf'),601.])
def test_lab_rejects_invalid_presentation_duration(tmp_path,duration):
    rclpy.init();(tmp_path/'config').mkdir()
    (tmp_path/'config/lab_assays_BXW.yaml').write_text('status: SCENARIO\n')
    try:
        with pytest.raises(ValueError,match='presentation_duration_s'):
            LabAssay(parameter_overrides=[Parameter('redline_root',value=str(tmp_path)),Parameter('run_id',value='invalid-duration'),Parameter('presentation_duration_s',value=duration)])
    finally:rclpy.try_shutdown()

def test_remote_lab_custody_result_and_duplicate_gates(tmp_path):
    rclpy.init();(tmp_path/'config').mkdir()
    (tmp_path/'config/lab_assays_BXW.yaml').write_text(yaml.safe_dump(dict(status='SCENARIO',method='WCL_SCENARIO',seed=7,ph_equilibrium=7.7,ph_sigma=.12,conductivity_ms_cm=1.2,mixing_tau_s=28,note='MODEL; not Gale measurement')))
    n=LabAssay(parameter_overrides=[Parameter('redline_root',value=str(tmp_path)),Parameter('run_id',value='test-lab'),Parameter('presentation_duration_s',value=.4)])
    probe=rclpy.create_node('lab_probe');ex=SingleThreadedExecutor();ex.add_node(n);ex.add_node(probe)
    products=[];evidence=[];statuses=[]
    probe.create_subscription(InstrumentProduct,'/redline/science/products',products.append,10)
    probe.create_subscription(EvidenceRecord,'/redline/evidence',evidence.append,10)
    probe.create_subscription(String,'/redline/science/lab_status',lambda m:statuses.append(json.loads(m.data)),10)
    client=probe.create_client(AnalyzeSample,'/redline/science/analyze_sample')
    def until(check,seconds=5):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            ex.spin_once(timeout_sec=.01)
            if check():return True
        return False
    def send(req):
        f=client.call_async(req);assert until(f.done);return f.result()
    try:
        assert until(client.service_is_ready)
        req=AnalyzeSample.Request(request_id='request-1',sample_id='smp-1',method='WCL_SCENARIO',integration_s=120.)
        assert not send(req).accepted and not products
        sample=dict(sample_id='smp-1',target_id='T1',state=7,container_id='tube-1',origin_point_m=[0,0,-3500],analysis_point_m=[30,0,-3500],evidence_ids=['ev-field'],provenance_status='SIMULATED')
        path=n.store.path/'sample-smp-1.json';path.write_text(json.dumps(sample));assert send(req).accepted
        assert not send(req).accepted
        assert until(lambda:len(products)==1 and len(evidence)==1)
        payload=json.loads(Path(products[0].payload_uri).read_text());assert payload['provenance_status']=='SIMULATED'
        assert payload['measurement']['model_only'] and len(payload['measurement']['series']['ph'])==31
        assert payload['instrument_point_m']!=payload['target_point_m'] and json.loads(path.read_text())==sample
        assert evidence[0].provenance.product_id==products[0].product_id
        req.integration_s=180.;assert not send(req).accepted
        req.request_id='request-2';assert send(req).accepted
        sample['state']=6;path.write_text(json.dumps(sample))
        assert until(lambda:any(s['state']=='failed' for s in statuses)) and len(products)==1
    finally:client.destroy();ex.shutdown();n.destroy_node();probe.destroy_node();rclpy.try_shutdown()
