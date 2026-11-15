"""Remote optional lab assay; persists a simulated result after actual custody."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,time,yaml
import rclpy
from rclpy.node import Node
from redline_msgs.srv import AnalyzeSample
from redline_msgs.msg import InstrumentProduct,EvidenceRecord,Provenance
from std_msgs.msg import String
from redline_core.lab_assay import lab_ready,model_assay
from redline_core.science_operations import ProductStore,ScienceTarget,checked_id

class LabAssay(Node):
    def __init__(self,**kwargs):
        super().__init__('lab_assay',**kwargs)
        root=Path(self.declare_parameter('redline_root','').value)
        run=str(self.declare_parameter('run_id','').value)
        self.store=ProductStore(root/'data/products',run)
        self.recipe=yaml.safe_load((root/'config/lab_assays_BXW.yaml').read_text())
        self.recipe_hash=hashlib.sha256((root/'config/lab_assays_BXW.yaml').read_bytes()).hexdigest()
        self.duration=float(self.declare_parameter('presentation_duration_s',10.).value)
        if not math.isfinite(self.duration) or not 0<self.duration<=600:
            raise ValueError('presentation_duration_s must be finite and in (0, 600]')
        self.busy=None;self.ledger={}
        self.products=self.create_publisher(InstrumentProduct,'/redline/science/products',10)
        self.evidence=self.create_publisher(EvidenceRecord,'/redline/evidence',10)
        self.status=self.create_publisher(String,'/redline/science/lab_status',10)
        self.create_service(AnalyzeSample,'/redline/science/analyze_sample',self.start)
        self.create_timer(.2,self.tick)
    def start(self,req,res):
        try:
            checked_id(req.request_id);checked_id(req.sample_id)
            fingerprint=(req.sample_id,req.method,float(req.integration_s))
            marker=self.store.path/('lab-request-'+hashlib.sha256(req.request_id.encode()).hexdigest()+'.json')
            if marker.exists():
                old=json.loads(marker.read_text())
                if old['fingerprint']!=list(fingerprint):raise ValueError('request id reused with different payload')
                res.accepted=False;res.reason='duplicate request; consult persisted lab status';res.operation_id=req.request_id;return res
            if self.busy:raise ValueError('laboratory busy')
            if req.method!='WCL_SCENARIO':raise ValueError('only explicit model method WCL_SCENARIO supported')
            path=self.store.path/f'sample-{req.sample_id}.json'
            if not path.is_file() or path.stat().st_size>16000:raise ValueError('sample custody record missing')
            sample=json.loads(path.read_text());lab_ready(sample)
            measurement=model_assay(sample,self.recipe,req.request_id,float(req.integration_s))
            measurement['input_ids'] += ['recipe-sha256:'+self.recipe_hash,'custody-sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()]
            with marker.open('x') as f:json.dump({'fingerprint':fingerprint,'state':'accepted'},f)
            self.busy={'id':req.request_id,'sample':sample,'measurement':measurement,'started':time.monotonic(),'marker':marker}
            res.accepted=True;res.reason='MODEL assay accepted; result/product pending';res.operation_id=req.request_id
        except (ValueError,KeyError,TypeError,OSError) as e:res.accepted=False;res.reason=str(e)
        return res
    def tick(self):
        if not self.busy:return
        b=self.busy;progress=min(1.,(time.monotonic()-b['started'])/self.duration)
        info={'schema':'redline.lab.status.v1','state':'running','operation_id':b['id'],'progress':progress,'sample_id':b['sample']['sample_id'],'model_only':True}
        if progress>=1:
            try:
                s=b['sample'];measurement=b['measurement']
                # Custody must still match the sample accepted for this operation.
                current=json.loads((self.store.path/f"sample-{s['sample_id']}.json").read_text());lab_ready(current)
                if current!=s:raise ValueError('custody changed during analysis')
                target=ScienceTarget(s['target_id'],tuple(s['origin_point_m']),{},.12,0,tuple(measurement['input_ids']))
                payload=self.store.write(request_id=b['id'],instrument='WCL_SCENARIO',target=target,measured_utc=datetime.now(timezone.utc).isoformat(),
                    integration_s=measurement['integration_s'],instrument_point=s['analysis_point_m'],measurement=measurement)
                msg=InstrumentProduct();msg.header.frame_id='map';msg.header.stamp=self.get_clock().now().to_msg();msg.product_id=payload['product_id'];msg.instrument='WCL_SCENARIO';msg.target_id=s['target_id']
                msg.target_point.x,msg.target_point.y,msg.target_point.z=map(float,s['origin_point_m']);msg.instrument_pose.pose.position.x,msg.instrument_pose.pose.position.y,msg.instrument_pose.pose.position.z=map(float,s['analysis_point_m'])
                msg.instrument_pose.pose.orientation.w=1.;msg.integration_s=measurement['integration_s'];msg.provenance.status=Provenance.SIMULATED;msg.provenance.product_id=msg.product_id;msg.payload_uri=payload['payload_uri'];msg.summary_json=json.dumps(measurement)
                ev=EvidenceRecord();ev.header=msg.header;ev.evidence_id=payload['evidence_id'];ev.source='WCL_SCENARIO_MODEL';ev.provenance=msg.provenance;ev.pose=msg.instrument_pose;ev.input_ids=measurement['input_ids'];ev.payload_uri=msg.payload_uri;ev.summary_json=msg.summary_json
                self.evidence.publish(ev);self.products.publish(msg)
                info.update(state='complete',product_id=msg.product_id,reason='SIMULATED MODEL product persisted')
            except Exception as e:info.update(state='failed',reason=str(e))
            b['marker'].write_text(json.dumps(info));self.busy=None
        self.status.publish(String(data=json.dumps(info)))

def main():
    rclpy.init();node=LabAssay()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
