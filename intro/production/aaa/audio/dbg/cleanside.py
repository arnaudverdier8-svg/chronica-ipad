import numpy as np, soundfile as sf, json, librosa, scipy.ndimage as ndi
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav',dtype='float32'); mid=(x[:,0]+x[:,1])/2; side=(x[:,0]-x[:,1])/2
words=json.load(open(O+'/../words.json'))['words']
wst=np.array([w['start'] for w in words])
H=441; NFFT=2048
Sm=np.abs(librosa.stft(mid,n_fft=NFFT,hop_length=H)); Ss=np.abs(librosa.stft(side,n_fft=NFFT,hop_length=H))
tf=np.arange(Sm.shape[1])*H/sr; freqs=librosa.fft_frequencies(sr=sr,n_fft=NFFT)
# smooth mid in time a little (leak includes short reverb)
Smx=ndi.maximum_filter1d(Sm,5,axis=1)
res={}
for gdb in [-30,-24,-18]:
    g=10**(gdb/20)
    Sc=np.maximum(Ss-g*Smx,0.05*Ss)
    mel=librosa.power_to_db(librosa.feature.melspectrogram(S=Sc**2,sr=sr,n_mels=96,fmin=20,fmax=16000))
    on=librosa.onset.onset_strength(S=mel,sr=sr,hop_length=H,lag=3,max_size=3)
    pk=librosa.util.peak_pick(on,pre_max=10,post_max=10,pre_avg=30,post_avg=30,delta=np.percentile(on,85),wait=15)
    pk=pk[np.argsort(on[pk])[::-1]][:40]
    near=np.mean([np.min(np.abs(wst-tf[i]))<0.06 for i in pk])
    # chance: fraction of random times within 0.06 of a word start
    rt=np.random.default_rng(0).uniform(0.3,61.8,5000); chance=np.mean([np.min(np.abs(wst-r))<0.06 for r in rt])
    print(f'g={gdb} dB: top40 onsets near word starts {near:.2f} (chance {chance:.2f})')
    res[gdb]=(on,pk,Sc)
on,pk,Sc=res[-24]
def wat(t):
    for w in words:
        if w['start']-0.05<=t<=w['end']+0.05: return w['w']
    return '-'
print(' '.join(f'{tf[i]:.2f}({on[i]/on[pk[0]]:.2f},{wat(tf[i])})' for i in pk[:40]))
np.savez_compressed(O+'/dbg/cleanside.npz',on=on,tf=tf,Sc_mel=librosa.power_to_db(librosa.feature.melspectrogram(S=Sc**2,sr=sr,n_mels=128,fmin=20,fmax=16000)).astype(np.float32))
