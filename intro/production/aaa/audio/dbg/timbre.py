import numpy as np, soundfile as sf, pickle, librosa
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav'); m=x.mean(1); side=(x[:,0]-x[:,1])/2; mid=(x[:,0]+x[:,1])/2
A=pickle.load(open(O+'/analysis.pkl','rb')); arr=A['arr']; cols=A['cols']; C=lambda n: arr[:,cols.index(n)]
def track(a,b,f_lo,f_hi):
    seg=m[int(a*sr):int(b*sr)]; n=4096; hop=441
    fr=[]; 
    for i in range(0,len(seg)-n,hop):
        X=np.abs(np.fft.rfft(seg[i:i+n]*np.hanning(n),n*8)); f=np.fft.rfftfreq(n*8,1/sr)
        s=(f>f_lo)&(f<f_hi); k=np.argmax(X[s]); fr.append(f[s][k])
    fr=np.array(fr); c=1200*np.log2(fr/np.median(fr))
    # modulation spectrum of pitch
    cc=c-np.convolve(c,np.ones(15)/15,'same')
    sp=np.abs(np.fft.rfft(cc*np.hanning(len(cc)))); fm=np.fft.rfftfreq(len(cc),hop/sr)
    sel=(fm>3)&(fm<9)
    return np.median(fr), c.std(), np.percentile(np.abs(cc),95), fm[sel][np.argmax(sp[sel])]
for a,b,lo,hi,lab in [(49.8,50.7,225,240,'Bb3 sustained (gap)'),(49.8,50.7,460,472,'Bb4 partial'),(58.2,59.4,228,238,'Bb3 (climax gap)'),(58.2,59.4,345,354,'F4 (climax gap)'),(62.0,66.0,780,795,'G5 tail'),(62.0,66.0,650,670,'E5 tail'),(13.5,14.8,66,76,'drone low partial'),(13.5,14.8,143,150,'drone D3'),(44.6,46.0,520,528,'C5 gap'),(22.8,23.8,345,355,'F4 gap')]:
    med,sd,p95,rate=track(a,b,lo,hi); print(f'{lab:24s} f={med:7.2f}Hz pitch sd {sd:5.1f} c, |dev|95 {p95:5.1f} c, mod peak {rate:.1f} Hz')
# stereo width per gap & percussive ratio, centroid
for g in A['gaps']:
    a,b=int((g['start']+0.1)*sr),int((g['end']-0.05)*sr)
    w=20*np.log10(np.std(side[a:b])/np.std(mid[a:b]))
    fa,fb=g['f_start']+3,max(g['f_start']+4,g['f_end']-2)
    print(f"gap {g['start']:6.2f}-{g['end']:6.2f} side/mid {w:6.1f} dB  perc {C('perc_ratio')[fa:fb].mean():.2f} centroid {C('centroid_hz')[fa:fb].mean():6.0f}  sub {C('band_sub_20_60')[fa:fb].mean():6.1f} bass {C('band_bass_60_250')[fa:fb].mean():6.1f} lowmid {C('band_lowmid_250_500')[fa:fb].mean():6.1f} mid {C('band_mid_500_2k')[fa:fb].mean():6.1f} pres {C('band_pres_2k_6k')[fa:fb].mean():6.1f} air {C('band_air_6k_16k')[fa:fb].mean():6.1f}")
nar=C('narration')>0.5
print('narration frames perc', C('perc_ratio')[nar].mean(), 'centroid', C('centroid_hz')[nar].mean())
f0=np.load(O+'/feat.npz')['f0']; vp=np.load(O+'/feat.npz')['vprob']; tp=np.load(O+'/feat.npz')['tp']
inw=np.zeros(len(tp),bool)
for w in A['words']: inw[(tp>=w['start'])&(tp<=w['end'])]=True
ff=f0[inw&np.isfinite(f0)]; print('narrator F0 median',np.median(ff),'p10',np.percentile(ff,10),'p90',np.percentile(ff,90))
