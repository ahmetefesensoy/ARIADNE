"""Rebuild an explicitly edited intro mix from original voice/music/SFX.

Actual Unreal shot log timestamps place sources. Original master WAV and
visual manifest stay untouched. This edited mix is not a live audio capture.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import wave


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(text):
    return datetime.strptime(text, "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=timezone.utc)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("shot", type=Path)
    p.add_argument("--log", required=True, type=Path)
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--ffmpeg", default="ffmpeg")
    args = p.parse_args()
    folder, root, log = args.shot.resolve(), args.repo.resolve(), args.log.resolve()
    report = {"schema": "redline.edited_intro_audio.v1", "passed": False,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Explicitly edited voice, music and Foley using original files and observed Unreal shot-start log; not live recorded master audio",
              "sources": [], "original_master_unchanged": True, "visual_frames_unchanged": True}
    try:
        ffmpeg = shutil.which(args.ffmpeg)
        if not ffmpeg:
            raise ValueError("Installed ffmpeg required")
        manifest = json.loads((folder/"manifest.json").read_text())
        start = datetime.fromisoformat(manifest["started_at_utc"].replace("Z", "+00:00"))
        duration = float(manifest["duration_wall_s"])
        if not manifest["complete"] or manifest["name"] != "01_acilis" or not 1<=duration<=125:
            raise ValueError("Expected the completed actual intro viewport recording")
        text = log.read_text(encoding="utf-8", errors="replace")
        events = []
        for match in re.finditer(r"\[([0-9.\-:]+)\]\[[^\]]*\]LogRedlinePrologue: Display: Prologue shot=(landing|rest|data|airlock|ready)\b", text):
            relative = (stamp(match[1])-start).total_seconds()
            if -.1<=relative<duration:
                events.append((match[2], max(0., relative)))
        if [event[0] for event in events] != ["landing", "rest", "data", "airlock", "ready"]:
            raise ValueError("Observed intro log does not contain all five shot starts")
        report.update(manifest_sha256=digest(folder/"manifest.json"), original_master_sha256=digest(folder/"master.wav"),
                      source_log_sha256=digest(log), duration_wall_s=duration, observed_shot_starts=[{"id": key, "start_s": at} for key, at in events])
        assets = root/"assets/narrative/prologue_v1"
        sources = []
        def add(path, at, end, gain, role, fade=0.):
            if at>=duration or end<=at:
                return
            sources.append((path, at, min(end,duration), gain, role, fade))
        for index, (key, at) in enumerate(events):
            end = events[index+1][1] if index+1<len(events) else duration
            add(assets/"chatterbox"/(key+".wav"),at,end,.85,"original Turkish narration")
            if key=="landing":
                add(assets/"landing_thrust.wav",at,end,.45,"original landing Foley")
            elif key=="rest":
                add(assets/"vardiya_arasi_jazz.wav",at,end,.45,"original procedural record-player jazz",.8)
            elif key=="airlock":
                add(assets/"airlock_pressure.wav",at,end,.45,"original airlock Foley")
            elif key=="ready":
                add(assets/"ready_chime.wav",at,end,.45,"original ready chime")
        # Intro uses take 01. Take 02 belongs to the separate return/crisis clip;
        # do not pretend that its music phase occurred in this viewport shot.
        take = root/"assets/audio/incoming/redline_sessiz_yorunge/redline_sessiz_yorunge_take_01.mp3"
        add(take,0.,duration,.10,"original exploration music take 01",1.)
        output = folder/"edited_intro.wav"
        if output.exists():
            raise ValueError("Edited WAV already exists; preserving previous edit")
        command = [ffmpeg,"-hide_banner","-nostdin","-n"]
        filters, labels = [], []
        for index,(path,at,end,gain,role,fade) in enumerate(sources):
            command += ["-i",str(path)]
            report["sources"].append({"path":path.relative_to(root).as_posix(),"sha256":digest(path),"start_wall_s":at,"stop_by_wall_s":end,"gain":gain,"role":role,"fade_in_s":fade})
            label=f"a{index}"; labels.append(f"[{label}]")
            fade_filter=f",afade=t=in:d={fade:.6f}" if fade else ""
            filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{end-at:.9f},asetpts=PTS-STARTPTS,volume={gain}{fade_filter},adelay={round(at*1000)}:all=1[{label}]")
        filters.append("".join(labels)+f"amix=inputs={len(labels)}:duration=longest:normalize=0,alimiter=limit=0.95:latency=1,apad,atrim=0:{duration:.9f}[out]")
        command += ["-filter_complex",";".join(filters),"-map","[out]","-ar","48000","-ac","2","-c:a","pcm_s16le",str(output)]
        result = subprocess.run(command,capture_output=True,text=True,timeout=120)
        (folder/"edited_intro_mix.log").write_text(result.stderr,encoding="utf-8")
        if result.returncode:
            raise ValueError("ffmpeg source mix failed; see edited_intro_mix.log")
        with wave.open(str(output),"rb") as wav:
            actual = wav.getnframes()/wav.getframerate()
        if abs(actual-duration)>.001:
            raise ValueError("Edited WAV duration differs from captured wall duration")
        report.update(passed=True,output_file=output.name,output_sha256=digest(output),actual_duration_s=actual,
                      editing="No stretching of audio or game frames. Sources start at observed wall shot times, stop at next shot; 0.95 peak limiter. Intro take01 retained; take02 reserved for return clip.")
        print(json.dumps({"passed":True,"output":str(output),"duration_s":actual,"shot_starts":report["observed_shot_starts"]}))
        return 0
    except Exception as error:
        report["error"]=str(error)
        print(str(error))
        return 1
    finally:
        (folder/"edited_intro_audio.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    raise SystemExit(main())
