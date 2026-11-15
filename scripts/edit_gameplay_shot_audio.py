"""Make an explicitly edited music/SFX mix for a real viewport clip.

Original master is retained at its recorded speed and padded with silence,
never stretched. Select existing music take 01 or 02. Optional events must
come from an authored/observed event sidecar, with their provenance stated.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import wave


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("shot",type=Path)
    p.add_argument("--take",required=True,choices=("01","02"))
    p.add_argument("--events",type=Path,help="JSON {source, events:[{file,start_s,gain,observed|authored}]} for original source WAVs")
    p.add_argument("--music-gain",type=float,default=.16)
    p.add_argument("--master-gain",type=float,default=1.)
    p.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--ffmpeg",default="ffmpeg")
    args=p.parse_args();folder=args.shot.resolve();root=args.repo.resolve()
    report={"schema":"redline.edited_gameplay_audio.v1","passed":False,"created_at_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"Edited source music and recorded game output; short master padded with silence, never time-stretched; not an uninterrupted live sound claim", "sources":[]}
    try:
        ffmpeg=shutil.which(args.ffmpeg)
        if not ffmpeg:raise ValueError("Installed ffmpeg required")
        if not all(math.isfinite(x) and 0<=x<=2 for x in (args.music_gain,args.master_gain)):raise ValueError("Gain outside [0,2]")
        manifest=json.loads((folder/"manifest.json").read_text());duration=float(manifest["duration_wall_s"])
        if manifest["schema"]!="redline.unreal.shot.v1" or not manifest["complete"] or not 1<=duration<=125:raise ValueError("Completed viewport shot required")
        master=folder/"master.wav"
        with wave.open(str(master),"rb") as wav:
            master_duration=wav.getnframes()/wav.getframerate()
        music=root/f"assets/audio/incoming/redline_sessiz_yorunge/redline_sessiz_yorunge_take_{args.take}.mp3"
        items=[(master,0.,args.master_gain,"recorded game master; missing end padded with silence"),(music,0.,args.music_gain,f"original music take {args.take}; explicit video edit")]
        if args.events:
            events=json.loads(args.events.read_text(encoding="utf-8"))
            if not isinstance(events.get("source"),str) or not events["source"]:raise ValueError("Events require a provenance description")
            if not isinstance(events.get("events"),list) or len(events["events"])>100:raise ValueError("Events list invalid")
            report["event_sidecar"]={"sha256":sha(args.events),"source":events["source"]}
            for event in events["events"]:
                path=(root/event["file"]).resolve();at=float(event["start_s"]);gain=float(event["gain"])
                if not path.is_relative_to(root/"assets") or path.suffix.lower()!=".wav" or not 0<=at<duration or not math.isfinite(gain) or not 0<=gain<=2:
                    raise ValueError("Invalid original SFX event")
                items.append((path,at,gain,"source SFX event: "+str(event.get("provenance","authored video edit"))))
        output=folder/"edited_gameplay.wav"
        if output.exists():raise ValueError("Edited WAV already exists; preserve it or select another shot")
        command=[ffmpeg,"-hide_banner","-nostdin","-n"];filters=[];labels=[]
        for index,(path,at,gain,role) in enumerate(items):
            command += ["-i",str(path)]
            report["sources"].append({"file":str(path.relative_to(root)) if path.is_relative_to(root) else path.name,"sha256":sha(path),"start_wall_s":at,"gain":gain,"role":role})
            fade=",afade=t=in:d=1,afade=t=out:st="+str(max(0.,duration-1))+":d=1" if path==music else ""
            filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{duration-at:.9f},asetpts=PTS-STARTPTS,volume={gain}{fade},adelay={round(at*1000)}:all=1[a{index}]")
            labels.append(f"[a{index}]")
        filters.append("".join(labels)+f"amix=inputs={len(items)}:duration=longest:normalize=0,alimiter=limit=0.95:latency=1,apad,atrim=0:{duration:.9f}[out]")
        command += ["-filter_complex",";".join(filters),"-map","[out]","-ar","48000","-ac","2","-c:a","pcm_s16le",str(output)]
        run=subprocess.run(command,capture_output=True,text=True,timeout=120)
        (folder/"edited_gameplay_mix.log").write_text(run.stderr,encoding="utf-8")
        if run.returncode:raise ValueError("Source mix failed; see edited_gameplay_mix.log")
        with wave.open(str(output),"rb") as wav:actual=wav.getnframes()/wav.getframerate()
        if abs(actual-duration)>.001:raise ValueError("Edited duration differs from viewport wall duration")
        report.update(passed=True,output_file=output.name,output_sha256=sha(output),actual_duration_s=actual,
                      source_master_duration_s=master_duration,master_missing_end_s=max(0.,duration-master_duration),
                      manifest_sha256=sha(folder/"manifest.json"),take=args.take,
                      timing="Recorded master begins at recorder audio start and retains original sample timing; latency and missing end are uncalibrated. No voice/SFX synthesized to fill a gap. Video timestamps unchanged.")
        print(json.dumps({"passed":True,"output":str(output),"duration_s":actual,"take":args.take,"master_missing_end_s":report["master_missing_end_s"]}));return 0
    except Exception as error:report["error"]=str(error);print(str(error));return 1
    finally:
        (folder/"edited_gameplay_audio.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


if __name__=="__main__":raise SystemExit(main())
