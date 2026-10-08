import numpy as np, soundfile as sf, librosa
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav',dtype='float64'); m=x.mean(1)
def peakf(a,b,lo,hi,n=5):
    s=m[int(a*sr):int(b*sr)]*np.hanning(int(b*sr)-int(a*sr)); Nf=1<<20
    X=np.abs(np.fft.rfft(s,Nf)); f=np.fft.rfftfreq(Nf,1/sr); sel=(f>lo)&(f<hi)
    Xs=X[sel]; fs=f[sel]; from scipy.signal import find_peaks
    p,_=find_peaks(Xs,distance=int(1.5/(f[1]))); p=p[np.argsort(Xs[p])[::-1][:n]]
    return [(round(fs[i],2), round(20*np.log10(Xs[i]/X.max()),1), librosa.hz_to_note(fs[i],cents=True)) for i in p]
for a,b in [(13.45,14.85),(8.3,9.2),(3.5,4.2),(6.2,7.05)]:
    print('drone',a,b,peakf(a,b,40,300,8))
for a,b in [(61.95,66.05),(49.75,50.75),(58.15,59.45),(54.9,56.3),(44.55,46.05),(22.75,23.85),(26.7,28.1),(31.85,32.7),(17.8,18.7)]:
    print('gap',a,b,peakf(a,b,60,1500,10))
F=np.load(O+'/feat.npz')
for name,env,hop in [('full onset',F['on_env'],441),('bed onset',F['bg_on'],1024),('low onset',F['on_low'],441)]:
    env=env-env.mean()
    ac=librosa.autocorrelate(env); ac/=ac[0]
    fr=hop/sr; lags=np.arange(len(ac))*fr
    sel=(lags>0.3)&(lags<2.0)
    k=np.argmax(ac[sel]); L=lags[sel][k]
    tempo,beats=librosa.beat.beat_track(onset_envelope=F[{'full onset':'on_env','bed onset':'bg_on','low onset':'on_low'}[name]],sr=sr,hop_length=hop)
    bt=librosa.frames_to_time(beats,sr=sr,hop_length=hop); ibi=np.diff(bt)
    # shuffled-baseline pulse clarity
    rng=np.random.default_rng(0); base=[]
    for _ in range(20):
        e2=rng.permutation(env); a2=librosa.autocorrelate(e2); a2/=a2[0]; base.append(a2[sel].max())
    print(f'{name}: ac peak {ac[sel][k]:.3f} at lag {L:.3f}s ({60/L:.1f} bpm); shuffled max {np.mean(base):.3f}; beat_track tempo {np.atleast_1d(tempo)[0]:.1f} bpm, n beats {len(bt)}, IBI cv {ibi.std()/ibi.mean():.2f}')
