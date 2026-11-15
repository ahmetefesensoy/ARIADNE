"""Summarize actual recorded scout attitude, never replace presentation poses."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def summary(records):
    if len(records) < 2:
        raise ValueError("At least two actual scout poses required")
    tilts=[];rates=[];roll=[];pitch=[];last=None
    for record in records:
        q=record["quaternion_xyzw"];x,y,z,w=q
        if len(q)!=4 or not all(math.isfinite(v) for v in q) or abs(sum(v*v for v in q)-1)>.001:
            raise ValueError("Invalid physical quaternion")
        tilts.append(math.degrees(math.acos(max(-1,min(1,1-2*(x*x+y*y))))))
        roll.append(math.degrees(math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))))
        pitch.append(math.degrees(math.asin(max(-1,min(1,2*(w*y-z*x))))))
        if last:
            dt=record["physics_s"]-last["physics_s"]
            if 0 < dt <= .5:
                dot=abs(sum(a*b for a,b in zip(q,last["quaternion_xyzw"])))
                rates.append(math.degrees(2*math.acos(max(0,min(1,dot))))/dt)
        last=record
    def p(values,percent):return sorted(values)[min(len(values)-1,int((len(values)-1)*percent))] if values else None
    return {"samples":len(records),"physics_s":records[-1]["physics_s"]-records[0]["physics_s"],
            "tilt_deg":{"max":max(tilts),"p95":p(tilts,.95),"median":p(tilts,.5)},
            "absolute_roll_max_deg":max(map(abs,roll)),"absolute_pitch_max_deg":max(map(abs,pitch)),
            "attitude_rate_deg_s":{"max":max(rates) if rates else None,"p95":p(rates,.95)},
            "max_horizontal_speed_m_s":max(math.hypot(*r.get("world_velocity_m_s",[0,0])[:2]) for r in records)}


def bridge_records(path):
    phase="PARKED";records=[]
    for line in path.open(encoding="utf-8-sig"):
        row=json.loads(line);packet=row.get("packet",row);topic=packet.get("topic");message=packet.get("msg",{})
        if topic=="/redline/campaign/state":
            phase=json.loads(message["data"]).get("scout",{}).get("phase",phase)
        if topic!="/scout_1/odom" or phase in ("PARKED","COMPLETE","STOPPED"):
            continue
        q=message["pose"]["pose"]["orientation"];v=message["twist"]["twist"]["linear"];stamp=message["header"]["stamp"]
        records.append({"physics_s":stamp["sec"]+stamp["nanosec"]*1e-9,
                        "quaternion_xyzw":[q[k] for k in "xyzw"],"world_velocity_m_s":[v[k] for k in "xyz"],"phase":phase})
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("source",type=Path);parser.add_argument("--out",type=Path,required=True);args=parser.parse_args()
    records=bridge_records(args.source) if args.source.suffix==".jsonl" else json.loads(args.source.read_text())
    report={"schema":"redline.scout.stability.v1","source":str(args.source),"source_sha256":hashlib.sha256(args.source.read_bytes()).hexdigest(),
            "scope":"Actual Gazebo attitude; no filtered or levelled Unreal orientation","metrics":summary(records)}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report))


if __name__=="__main__":main()
