"""Encode a recorded REDLINE viewport shot and its game master WAV.

Uses actual per-frame wall timestamps (VFR), not a claimed fixed capture FPS.
No desktop/microphone capture or generated frames. Explicit alternate edited
audio requires its own checked provenance receipt; master.wav is the default.
Requires installed ffmpeg/ffprobe; run in WSL when no Windows binary is on PATH.
"""
from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import wave


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_info(path: Path, wait_s: float) -> dict:
    """UE writes the WAV asynchronously; require a stable, complete PCM file."""
    deadline = time.monotonic() + wait_s
    error = "WAV export has not completed"
    previous_size = -1
    while True:
        try:
            size = path.stat().st_size
            if size <= 44 or size > 256 * 1024 * 1024 or (wait_s>0 and size != previous_size):
                previous_size = size
                raise ValueError("WAV not stable yet")
            with wave.open(str(path), "rb") as sound:
                channels, width, rate, count = sound.getnchannels(), sound.getsampwidth(), sound.getframerate(), sound.getnframes()
                if sound.getcomptype() != "NONE" or channels < 1 or channels > 8 or width != 2 or not 8000 <= rate <= 192000:
                    raise ValueError("Expected the UE master 16-bit PCM WAV")
                data = sound.readframes(count)
                if len(data) != count * channels * width or count <= 0:
                    raise ValueError("Incomplete WAV payload")
            samples = array("h")
            samples.frombytes(data)
            if sys.byteorder != "little":
                samples.byteswap()
            peak = max(abs(min(samples)), abs(max(samples)))
            return {"sample_rate": rate, "channels": channels, "sample_width_bytes": width,
                    "sample_count": count, "duration_s": count / rate, "peak_int16": peak,
                    "silent": peak == 0, "sha256": sha256(path)}
        except (FileNotFoundError, ValueError, wave.Error, EOFError, OSError) as exc:
            error = str(exc)
        if time.monotonic() >= deadline:
            raise ValueError(error)
        time.sleep(.25)


def validate_manifest(folder: Path) -> tuple[dict, list[dict]]:
    path = folder / "manifest.json"
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Oversized shot manifest")
    manifest = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    if manifest.get("schema") != "redline.unreal.shot.v1" or not manifest.get("complete") or manifest.get("recording") or manifest.get("failure"):
        raise ValueError("Shot must be complete and free of capture errors")
    width, height = manifest["width"], manifest["height"]
    duration = float(manifest["duration_wall_s"])
    if not 0 < duration <= 125 or not 64 <= width <= 3840 or not 64 <= height <= 2160:
        raise ValueError("Shot dimensions/duration outside recorder bounds")
    frames = manifest["frames"]
    if not 2 <= len(frames) <= 3600 or manifest["saved_frames"] != len(frames):
        raise ValueError("Need 2–3600 actual recorded frames")
    frames = sorted(frames, key=lambda item: item["captured_wall_s"])
    previous = -1.
    for frame in frames:
        relative = frame["file"]
        stamp = float(frame["captured_wall_s"])
        if not re.fullmatch(r"frames/frame_[0-9]{6}\.png", relative) or not math.isfinite(stamp) or not previous < stamp <= duration:
            raise ValueError("Invalid or duplicate actual frame timestamp/path")
        image = folder / relative
        if not image.resolve().is_relative_to(folder) or image.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("Invalid frame file")
        with image.open("rb") as stream:
            header = stream.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR" or struct.unpack(">II", header[16:24]) != (width, height):
            raise ValueError("Frame PNG dimensions differ from recorded viewport")
        previous = stamp
    return manifest, frames


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shot", type=Path, help="Directory containing manifest.json, frames/, master.wav")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wait-audio-s", type=float, default=20.)
    parser.add_argument("--allow-silent", action="store_true")
    parser.add_argument("--audio-file", default="master.wav", help="Local WAV basename; edited audio requires --audio-receipt")
    parser.add_argument("--audio-receipt", type=Path)
    args = parser.parse_args()
    folder = args.shot.resolve()
    report = {"schema": "redline.unreal.shot_encoding.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "passed": False, "source": "Actual Unreal viewport PNG frames and recorded game master WAV", "shot": str(folder)}
    try:
        if not 0 <= args.wait_audio_s <= 30:
            raise ValueError("Audio wait must be in [0,30] seconds")
        ffmpeg, ffprobe = shutil.which(args.ffmpeg), shutil.which(args.ffprobe)
        if not ffmpeg or not ffprobe:
            raise ValueError("Installed ffmpeg and ffprobe required; no binary is downloaded")
        manifest, frames = validate_manifest(folder)
        report["capture_source"] = manifest.get("source")
        report["test_fixture"] = bool(manifest.get("test_fixture", False))
        if manifest.get("audio_file") != "master.wav":
            raise ValueError("Unexpected game master audio path")
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.wav", args.audio_file):
            raise ValueError("Audio must be a local safe WAV basename")
        if args.audio_file != "master.wav":
            if not args.audio_receipt:
                raise ValueError("Edited audio requires a provenance receipt")
            receipt_path = args.audio_receipt.resolve()
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if not receipt.get("passed") or receipt.get("output_sha256") != sha256(folder/args.audio_file):
                raise ValueError("Edited audio receipt does not match WAV")
            report["audio_edit"] = receipt
            report["audio_edit_receipt_sha256"] = sha256(receipt_path)
            report["source"] = "Actual Unreal viewport PNG frames with explicitly edited source audio; recorded master preserved"
        audio = wav_info(folder / args.audio_file, args.wait_audio_s)
        if audio["silent"] and not args.allow_silent:
            raise ValueError("Game master WAV is silent; no music/SFX can be claimed")
        first = frames[0]["captured_wall_s"]
        stop = float(manifest["duration_wall_s"])
        duration = stop - first
        if audio["duration_s"] < stop - .25:
            raise ValueError("Recorded master audio is shorter than the viewport shot")
        concat = ["ffconcat version 1.0"]
        for index, frame in enumerate(frames):
            end = frames[index+1]["captured_wall_s"] if index+1 < len(frames) else stop
            if index+1 == len(frames):
                # Place the final held-image packet just before the trim end,
                # so the MP4 video track includes the full real shot duration.
                end -= min(.001, (end-frame["captured_wall_s"])/2)
            concat += [f"file '{frame['file']}'", "option framerate 1000", f"duration {end-frame['captured_wall_s']:.9f}"]
        # ffconcat needs a final timestamp marker to honour the last duration.
        # This holds the last actually captured image until recording stopped;
        # it does not generate/interpolate a new source frame.
        concat += [f"file '{frames[-1]['file']}'", "option framerate 1000"]
        (folder / "frames.ffconcat").write_text("\n".join(concat)+"\n", encoding="utf-8")
        output = (args.output or folder / "clip.mp4").resolve()
        if output.exists():
            raise ValueError("Output exists; choose another file to preserve the prior recording")
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [ffmpeg, "-hide_banner", "-nostdin", "-n", "-f", "concat", "-safe", "0", "-i", str(folder/"frames.ffconcat"),
                   "-ss", f"{first:.9f}", "-i", str(folder/args.audio_file), "-map", "0:v:0", "-map", "1:a:0",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-bf", "0", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                   "-fps_mode", "vfr", "-c:a", "aac", "-b:a", "256k", "-t", f"{duration:.9f}", "-movflags", "+faststart", str(output)]
        completed = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=600)
        (folder / "encode.log").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise ValueError("ffmpeg encoding failed; see encode.log")
        probe = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True, timeout=30)
        metadata = json.loads(probe.stdout)
        if not any(s["codec_type"] == "video" for s in metadata["streams"]) or not any(s["codec_type"] == "audio" for s in metadata["streams"]):
            raise ValueError("Encoded clip lacks video or audio stream")
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        if abs(float(video["duration"])-duration)>.05:
            raise ValueError("Encoded video duration does not preserve actual shot duration")
        gaps = [b["captured_wall_s"]-a["captured_wall_s"] for a, b in zip(frames, frames[1:])]
        report.update(passed=True, output=str(output), output_sha256=sha256(output), audio=audio,
                      manifest_sha256=sha256(folder/"manifest.json"), actual_source_frames=len(frames),
                      requested_fps=manifest["requested_fps"], measured_mean_capture_fps=(len(frames)-1)/(frames[-1]["captured_wall_s"]-first),
                      maximum_actual_frame_gap_s=max(gaps), start_trim_s=first, duration_wall_s=duration,
                      frame_timing="Variable timestamps from real render-ready frames; last real image held to capture stop; no interpolation",
                      audio_alignment=manifest.get("audio_alignment"), encoder=ffmpeg, probe=metadata,
                      frame_sha256=[{"file": frame["file"], "sha256": sha256(folder/frame["file"])} for frame in frames])
        print(json.dumps({key: report[key] for key in ("passed", "output", "actual_source_frames", "measured_mean_capture_fps", "duration_wall_s")}))
        return 0
    except Exception as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if folder.is_dir():
            (folder / "encoding.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
