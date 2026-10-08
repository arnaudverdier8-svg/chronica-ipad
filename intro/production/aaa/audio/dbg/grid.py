import numpy as np, soundfile as sf, json, scipy.ndimage as ndi, scipy.signal as sps, librosa
from scipy.signal import butter, sosfiltfilt
x,sr=sf.read('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio/audio_f32.wav'); side=(x[:,0]-x[:,1])/2; mid=x.mean(1)
h=441
def bandenv(sig,lo,hi):
    y=sosfiltfilt(butter(4,[lo,hi],btype='band',fs=sr,output='sos'),sig); n=len(y)//h
    return 10*np.log10((y[:n*h].reshape(n,h)**2).mean(1)+1e-12)
e=ndi.uniform_filter1d(bandenv(side,22,120),5); n=len(e); t=np.arange(n)*0.01
d=np.maximum(0,np.diff(e,prepend=e[0])); d=ndi.uniform_filter1d(d,3)   # low-band onset (dB/10ms)
Z=np.load('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio/feat_side.npz'); son=Z['on'][:n]
def fold_strength(sig,t,P,a,b):
    s=(t>=a)&(t<b); w=sig[s]-np.median(sig[s]); w=np.maximum(w,0)
    ph=2*np.pi*t[s]/P; z=(w*np.exp(1j*ph)).sum()/ (w.sum()+1e-12)
    return np.abs(z), (np.angle(z)/(2*np.pi)*P)%P
rng=np.random.default_rng(0)
for lab,sig in [('side low-band onset',d),('side broadband onset',son)]:
    for a,b in [(0.3,61.8),(0.3,17.8),(18,42.5),(42.5,61.8)]:
        Ps=np.arange(0.4,3.0,0.002)
        R=np.array([fold_strength(sig,t,P,a,b)[0] for P in Ps])
        k=np.argmax(R[(Ps>1.5)]); Pb=Ps[Ps>1.5][k]
        # null: circularly shifted segments
        s=(t>=a)&(t<b)
        null=[]
        for _ in range(30):
            sh=np.roll(sig[s],rng.integers(50,s.sum()-50)); tt=t[s]
            # shuffle in 0.5s blocks to destroy periodicity
            blocks=np.array_split(sh,max(2,len(sh)//50)); rng.shuffle(blocks); sh=np.concatenate(blocks)
            null.append(max(fold_strength(np.concatenate([np.zeros(s.argmax()),sh,np.zeros(n-s.argmax()-len(sh))]),t,P,a,b)[0] for P in Ps[(Ps>1.5)][::10]))
        top3=Ps[np.argsort(R)[::-1][:5]]
        print(f'{lab:22s} {a:5.1f}-{b:5.1f}: best P(>1.5s)={Pb:.3f}s R={R[Ps>1.5][k]:.3f} phase={fold_strength(sig,t,Pb,a,b)[1]:.3f}s | null95={np.percentile(null,95):.3f} | top P overall {np.round(top3,3)}')
