"""Original procedural jazz sketch + airlock Foley. No external or paid music API.

The musical phrase is authored here; these are synthetic instrument timbres,
not a recording of a musician or flight-hardware audio.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import wave
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io.wavfile import write

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'assets/narrative/prologue_v1'
SR = 24000
RNG = np.random.default_rng(20261115)


def save(name, data):
    peak = np.max(np.abs(data))
    if peak > .85: data = data * (.85 / peak)
    write(DEST/name, SR, np.asarray(np.clip(data,-1,1)*32767,dtype='<i2'))
    return {'file':name,'duration_s':len(data)/SR,'peak':float(np.max(np.abs(data))),
            'rms':float(np.sqrt(np.mean(data**2))),
            'sha256':hashlib.sha256((DEST/name).read_bytes()).hexdigest()}


def note(midi, seconds, kind):
    t = np.arange(round(seconds*SR))/SR
    f = 440*2**((midi-69)/12)
    attack = 1-np.exp(-t*160)
    if kind == 'piano':
        return attack*np.exp(-t*1.8)*(np.sin(2*np.pi*f*t+.65*np.sin(2*np.pi*f*2*t)*np.exp(-t*4))+.16*np.sin(2*np.pi*f*3*t)*np.exp(-t*3))
    return attack*np.exp(-t*3.5)*(np.sin(2*np.pi*f*t)+.28*np.sin(2*np.pi*f*2*t)+.1*np.sin(2*np.pi*f*3*t))


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    beat = 60/80
    length = 16*4*beat
    mix = np.zeros((round(length*SR),2),dtype=np.float64)
    def add(signal, start, gain, pan=0):
        i = round(start*SR)
        if i >= len(mix): return
        size = min(len(signal),len(mix)-i)
        mix[i:i+size,0] += signal[:size]*gain*np.sqrt((1-pan)/2)
        mix[i:i+size,1] += signal[:size]*gain*np.sqrt((1+pan)/2)
    # ii-V-I turnaround; original voicings/rhythm, no borrowed melody.
    progression = [([53,60,64,69],[38,41,45,48]),([53,59,64,69],[43,47,50,53]),
                   ([52,59,62,67],[36,40,43,47]),([55,61,64,70],[45,49,52,55]),
                   ([53,60,64,69],[38,41,45,48]),([53,59,64,69],[43,47,50,53]),
                   ([52,57,62,67],[36,40,43,47]),([55,61,64,70],[45,49,52,55])]
    high = butter(2,[3000,9000],btype='bandpass',fs=SR,output='sos')
    for bar in range(16):
        chord,bass = progression[bar%8]
        start = bar*4*beat
        for step in range(4):
            add(note(bass[step],beat*.92,'bass'),start+step*beat,.11,-.2)
        for hit,gain in [(0,.036),(1.65,.024),(3.0,.03)]:
            for j,pitch in enumerate(chord):
                add(note(pitch,2.8,'piano'),start+hit*beat+j*.008,gain,.22)
        for step in range(8):
            offset = (step//2+(.66 if step%2 else 0))*beat
            t = np.arange(int(.19*SR))/SR
            brush = sosfilt(high,RNG.normal(0,1,len(t)))*np.exp(-t*28)
            add(brush,start+offset,.012 if step%2 else .018,.45)
        for b in (1,3):
            t = np.arange(int(.17*SR))/SR
            snare = RNG.normal(0,1,len(t))*np.exp(-t*25)*(1-np.exp(-t*500))
            add(snare,start+b*beat,.012,-.35)
    # Warm, quiet vinyl texture and a short endpoint crossfade.
    mix = np.tanh(mix*1.5)*.7
    mix += RNG.normal(0,.00016,mix.shape)
    n = int(.12*SR)
    ramp = np.linspace(0,1,n)[:,None]
    mixed_end = mix[-n:]*(1-ramp)+mix[:n]*ramp
    mix[-n:] = mixed_end
    mix[-1] = mix[0]
    files = [save('vardiya_arasi_jazz.wav',mix)]
    t = np.arange(SR*5)/SR
    hiss = sosfilt(butter(2,[180,6000],btype='bandpass',fs=SR,output='sos'),RNG.normal(0,1,len(t)))
    envelope = np.sin(np.pi*np.minimum(t/4.5,1))**2
    files.append(save('airlock_pressure.wav',hiss*envelope*.06))
    t = np.arange(SR*2)/SR
    door = (np.sin(2*np.pi*(95*t+15*t*t))*.04+RNG.normal(0,.008,len(t)))*np.sin(np.pi*t/2)**2
    files.append(save('airlock_door.wav',door))
    t = np.arange(int(SR*.7))/SR
    chime = (np.sin(2*np.pi*660*t)+.55*np.sin(2*np.pi*880*t))*np.exp(-t*7)*.11
    files.append(save('ready_chime.wav',chime))
    t = np.arange(SR*16)/SR
    low = sosfilt(butter(2,850,btype='lowpass',fs=SR,output='sos'),RNG.normal(0,1,len(t)))
    fade = np.minimum(t/1.2,1)*np.clip((16-t)/2,0,1)
    thrust = (low*.15+np.sin(2*np.pi*(48*t+.18*t*t))*.045)*fade
    files.append(save('landing_thrust.wav',thrust))
    voices = []
    for name in ('landing','rest','data','airlock','ready'):
        with wave.open(str(DEST/(name+'.wav')),'rb') as w:
            voices.append({'file':name+'.wav','duration_s':w.getnframes()/w.getframerate()})
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'SCENARIO',
            'method':'locally authored deterministic procedural synthesis; no generative music service',
            'jazz_composition':'Vardiya Arası, original instrumental sketch; synthetic piano/bass/brushed percussion',
            'credits_spent':0,'files':files,'voice_durations':voices,
            'jazz_endpoint_delta':float(np.max(np.abs(mix[-1]-mix[0]))),
            'listening_review':'not an acoustic/acting or final loop-mix acceptance'}
    (DEST/'audio_provenance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':main()
