# Build a voice-suppressed, sustained-tone CQT ("music_sus") using pyin F0 comb masking inside word spans + 1.0 s horizontal median.
import numpy as np, soundfile as sf, librosa, json, scipy.ndimage as ndi
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav',dtype='float32'); m=x.mean(1)
F=np.load(O+'/feat.npz')
hop=512; bpo=36; nb=96*3
fmin=librosa.note_to_hz('C1')
C=np.abs(librosa.cqt(m,sr=sr,hop_length=hop,fmin=fmin,n_bins=nb,bins_per_octave=bpo))
t=np.arange(C.shape[1])*hop/sr
fb=fmin*2**(np.arange(nb)/bpo)
words=json.load(open(O+'/../words.json'))['words']
inword=np.zeros(len(t),bool)
for w in words: inword[(t>=w['start']-0.03)&(t<w['end']+0.06)]=True
f0=F['f0']; tp=F['tp']; vp=F['vprob']
idx=np.clip(np.searchsorted(tp,t),0,len(tp)-1)
f0t=f0[idx]; vpt=vp[idx]
# also take f0 from neighbours (+-2 pyin frames) to cover glides
mask=np.ones_like(C)
lfb=np.log2(fb)
for j in range(len(t)):
    if not inword[j]: continue
    cands=[]
    for dj in (-3,0,3):
        k=min(max(idx[j]+dj,0),len(tp)-1)
        if np.isfinite(f0[k]) and vp[k]>0.1: cands.append(f0[k])
    if not cands:
        # unvoiced/creak inside a word: suppress below 400 Hz weakly (creaky voice ~70 Hz) - leave as is
        continue
    for f in cands:
        hk=f*np.arange(1,40); hk=hk[hk<1500]
        d=np.abs(lfb[:,None]-np.log2(hk)[None,:]).min(1)*12  # semitones
        mask[d<0.6,j]=0.0
Cm=C*mask
S=ndi.median_filter(Cm,size=(1,87))  # ~1.0 s
np.savez_compressed(O+'/dbg/music_sus.npz',S=S.astype(np.float32),C=C.astype(np.float32),mask=mask.astype(np.uint8),t=t,fb=fb)
print('ok',S.shape)
