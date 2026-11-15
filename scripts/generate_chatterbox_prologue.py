"""Generate REDLINE voice candidates using the bundled fictional default voice."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

task_dir = Path(os.environ.get('REDLINE_VOICE_HOME', str(Path.home() / '.cache/redline/voice/chatterbox-v1')))
os.environ['HF_HOME'] = str(task_dir / 'hf')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import numpy as np
import soundfile as sf
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

repo_dir = Path(__file__).resolve().parents[1]
evidence_dir = repo_dir / 'assets/narrative/prologue_v1/chatterbox/runtime'
input_path = repo_dir / 'assets/narrative/prologue_v1/script.json'
asset_dir = input_path.parent / 'chatterbox'
script = json.loads(input_path.read_text(encoding='utf-8-sig'))
voice_shots = script['shots'] + script.get('mission_intros',[])
phase = sys.argv[1] if len(sys.argv) > 1 else 'proof'
assert phase in {'proof', 'all'}
device = os.environ.get('REDLINE_VOICE_DEVICE', 'cuda')
torch.set_num_threads(8)
torch.manual_seed(271828)
started = time.monotonic()
model = ChatterboxMultilingualTTS.from_local(task_dir / 'model', device=device, t3_model='v3')
print(f'MODEL_LOADED device={device} elapsed_s={time.monotonic()-started:.2f}', flush=True)

def digest(path):
    with path.open('rb') as src:
        return hashlib.file_digest(src, 'sha256').hexdigest()

def stats(data, sr):
    return {'duration_s': round(len(data) / sr, 4), 'sample_rate_hz': sr,
            'sample_count': len(data), 'finite': bool(np.isfinite(data).all()),
            'peak': float(np.abs(data).max()), 'rms': float(np.sqrt(np.mean(data.astype(np.float64)**2))),
            'clipping_samples': int(np.count_nonzero(np.abs(data) >= 0.999)),
            'quiet_sample_ratio': float(np.mean(np.abs(data) < 0.0001))}

def render(text, path):
    clip_started = time.monotonic()
    wave = model.generate(text, language_id='tr', exaggeration=0.35, cfg_weight=0.5, temperature=0.75)
    raw = wave.detach().cpu().numpy().reshape(-1).astype(np.float32)
    raw_stats = stats(raw, model.sr)
    assert raw_stats['finite'] and raw_stats['rms'] > 0.001, raw_stats
    # Model output is floating point, so peaks slightly above 1 are retained
    # samples, not already clipped PCM. Attenuate before PCM conversion.
    assert raw_stats['peak'] < 5, raw_stats
    assert 0.5 < raw_stats['duration_s'] < 40, raw_stats
    # Keep speech samples unchanged apart from a bounded peak attenuation and silence padding.
    gain = min(1.0, 0.89 / max(raw_stats['peak'], 1e-9))
    padded = np.pad(raw * gain, (round(0.15 * model.sr), round(0.25 * model.sr)))
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, padded, model.sr, subtype='PCM_16')
    decoded, sr = sf.read(path, dtype='float32')
    record = {'text': text, 'path': str(path.relative_to(repo_dir)), 'sha256': digest(path),
              'elapsed_s': round(time.monotonic()-clip_started, 3), 'raw_stats': raw_stats,
              'gain': gain, 'output_stats': stats(decoded, sr)}
    assert record['output_stats']['clipping_samples'] == 0
    print('CLIP ' + json.dumps(record, ensure_ascii=False), flush=True)
    return record

base = {'schema': 'redline.synthetic-voice.v1', 'status': 'SCENARIO', 'synthetic_audio': True,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'language': 'tr',
        'tool': 'Chatterbox Multilingual V3', 'tool_license': 'MIT',
        'tool_source': 'https://github.com/resemble-ai/chatterbox',
        'source_revision': (evidence_dir/'source-revision.txt').read_text().strip(),
        'model': json.loads((evidence_dir/'model-manifest.json').read_text()),
        'voice': 'Bundled conds.pt default voice; no user recording or artist voice reference supplied',
        'reference_audio_supplied': False, 'artist_imitation_requested': False, 'credits_spent': 0,
        'input_script_sha256': digest(input_path), 'torch': torch.__version__,
        'cuda_runtime': torch.version.cuda, 'device': device,
        'parameters': {'language_id':'tr','exaggeration':0.35,'cfg_weight':0.5,'temperature':0.75,'seed':271828},
        'dependency_override': 'Official source pins torch/torchaudio2.6.0 on Python3.12; matching official cu128 2.11.0 wheels used for RTX5080 Blackwell support.',
        'quality_scope': 'Finite audio, duration, RMS, peak and clipping checked. Naturalness/pronunciation require listening review.',
        'original_voice_hashes': {shot['voice']: digest(input_path.parent/shot['voice']) for shot in voice_shots if (input_path.parent/shot['voice']).exists()}}

if phase == 'proof':
    base['clips'] = [render("Mars'ta bir vardiya daha.", evidence_dir/'first-sentence.wav')]
    (evidence_dir/'proof.json').write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
else:
    base['clips'] = []
    for shot in voice_shots:
        record = render(shot['subtitle'], asset_dir/shot['voice'])
        record['shot_id'] = shot['id']
        record['planned_shot_duration_s'] = shot['duration_s']
        record['fits_planned_shot'] = record['output_stats']['duration_s'] <= shot['duration_s']
        base['clips'].append(record)
        (asset_dir/'provenance.json').write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
    (evidence_dir/'generation-result.json').write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
print('GENERATION_COMPLETE', flush=True)
