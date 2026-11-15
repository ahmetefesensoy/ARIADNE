"""Mux only the original recorded game WAV. No mix, music, pad or time stretch."""
from pathlib import Path
import subprocess,json,hashlib
root=Path('outputs/raw-takes');out=root/'with-game-audio';out.mkdir(exist_ok=True)
for video in sorted(root.glob('*.mp4')):
 wav=video.with_suffix('.game.wav');target=out/video.name
 if not wav.exists() or target.exists():continue
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(video)]));duration=probe['format']['duration']
 subprocess.run(['ffmpeg','-v','error','-n','-i',str(video),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t',duration,str(target)],check=True)
 target.with_suffix('.json').write_text(json.dumps({'video':str(video),'original_game_audio':str(wav),'audio_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'editing':'None. Original game recording at its captured start; no padding/stretch/music/gain. Audio device latency uncalibrated; WAV may end before video.'},indent=2)+'\n')
