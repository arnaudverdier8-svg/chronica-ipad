import numpy as np, soundfile as sf, librosa, json, scipy.ndimage as ndi
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav',dtype='float32'); m=x.mean(1)
hop=512
C=np.abs(librosa.cqt(m,sr=sr,hop_length=hop,fmin=librosa.note_to_hz('C1'),n_bins=96*3,bins_per_octave=36))
t=np.arange(C.shape[1])*hop/sr
# sustained part: horizontal median over ~0.8 s
Hs=ndi.median_filter(C,size=(1,69))
np.save(O+'/dbg/cqt_sus.npy',Hs.astype(np.float32))
# fold to semitones (center bin of each 3)
Hsemi=Hs.reshape(96,3,-1).max(1)
names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nm(k): return names[k%12]+str(k//12+1)
words=json.load(open(O+'/../words.json'))['words']
# drone check: strongest sustained semitone bins in windows
for a,b in [(0,3.5),(3.5,4.2),(6.2,7.1),(8.3,9.2),(13.4,14.9),(14.9,16.6),(16.6,18.7),(18.7,22.7),(22.7,23.9),(23.9,26.6),(26.6,28.2),(28.2,31.8),(31.8,32.7),(32.7,37.2),(37.2,41),(41,44.5),(44.5,46.1),(46.1,49.7),(49.7,50.8),(50.8,54.9),(54.9,56.3),(56.3,58.1),(58.1,59.5),(59.5,61.85),(61.9,64),(64,66.1)]:
    s,e=np.searchsorted(t,a),np.searchsorted(t,b)
    v=Hsemi[:,s:e].mean(1); vdb=20*np.log10(v/Hsemi.max()+1e-9)
    top=np.argsort(v)[::-1][:8]
    chroma=np.zeros(12)
    for k in range(96): chroma[k%12]+=v[k]**2
    chroma/=chroma.max()
    pcs=' '.join(f'{names[i]}:{chroma[i]:.2f}' for i in np.argsort(chroma)[::-1][:5])
    # lowest strong sustained pitch (> -30 dB re window max)
    thr=vdb.max()-25; low=[nm(k) for k in range(96) if vdb[k]>thr][:3]
    print(f'{a:5.1f}-{b:5.1f}  top: '+' '.join(f'{nm(k)}({vdb[k]:.0f})' for k in top)+f' | low:{low} | pcs {pcs}')
