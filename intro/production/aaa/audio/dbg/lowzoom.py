import numpy as np, soundfile as sf, json, librosa, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav'); mid=x.mean(1); side=(x[:,0]-x[:,1])/2
words=json.load(open(O+'/../words.json'))['words']
fig,ax=plt.subplots(4,1,figsize=(30,14),sharex=True)
for k,(sig,lab) in enumerate([(mid,'mid'),(side,'side')]):
    S=np.abs(librosa.stft(sig,n_fft=8192,hop_length=441)); f=librosa.fft_frequencies(sr=sr,n_fft=8192); sel=f<260
    D=librosa.amplitude_to_db(S[sel],ref=np.abs(S).max())
    ax[k].imshow(D,origin='lower',aspect='auto',extent=[0,S.shape[1]*0.01,0,f[sel][-1]],vmin=-80,vmax=-10,cmap='magma'); ax[k].set_ylabel(lab+' Hz')
for k,(lo,hi) in enumerate([(20,55),(55,120)]):
    for sig,lab,c in [(mid,'mid','C0'),(side,'side','C1')]:
        y=sosfiltfilt(butter(4,[lo,hi],btype='band',fs=sr,output='sos'),sig); n=len(y)//441
        e=20*np.log10(np.sqrt((y[:n*441].reshape(n,441)**2).mean(1))+1e-9)
        ax[2+k].plot(np.arange(n)*0.01,e,c,lw=.7,label=f'{lab} {lo}-{hi}')
    ax[2+k].legend(loc='upper left'); ax[2+k].set_ylim(-95,-25); ax[2+k].grid(alpha=.3)
for w in words:
    for A in ax[2:]: A.axvspan(w['start'],w['end'],color='cyan',alpha=.12)
    ax[0].text(w['start'],240,w['w'],color='w',fontsize=8)
ax[-1].set_xlim(40,62); ax[-1].set_xticks(np.arange(40,62.1,0.5))
plt.tight_layout(); plt.savefig(O+'/dbg/lowzoom.png',dpi=48)
