import numpy as np, soundfile as sf, librosa, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, json
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x,sr=sf.read(O+'/audio_f32.wav',dtype='float32'); m=x.mean(1)
words=json.load(open(O+'/../words.json'))['words']
hop=512
C=np.abs(librosa.cqt(m,sr=sr,hop_length=hop,fmin=librosa.note_to_hz('C1'),n_bins=96,bins_per_octave=12))
Cd=librosa.amplitude_to_db(C,ref=C.max())
np.save(O+'/dbg/cqt_db.npy',Cd.astype(np.float32))
t=np.arange(C.shape[1])*hop/sr
for i,(a,b) in enumerate([(0,17),(16,34),(33,50),(49,66.2)]):
    fig,ax=plt.subplots(1,1,figsize=(24,9))
    s,e=np.searchsorted(t,a),np.searchsorted(t,b)
    ax.imshow(Cd[:,s:e],origin='lower',aspect='auto',extent=[t[s],t[e-1],0,96],vmin=-70,vmax=0,cmap='magma',interpolation='nearest')
    ax.set_yticks(range(0,96,12)); ax.set_yticklabels([f'C{k+1}' for k in range(8)])
    ax.set_yticks(range(0,96,1),minor=True)
    ax.set_xticks(np.arange(np.ceil(a),b,1)); ax.set_xticks(np.arange(np.ceil(a),b,0.25),minor=True)
    ax.grid(axis='both',which='major',alpha=.4,color='w')
    for w in words:
        if a<=w['start']<=b:
            ax.axvspan(w['start'],w['end'],ymin=.97,ymax=1,color='cyan',alpha=.8)
            ax.text(w['start'],91,w['w'],fontsize=8,color='w',rotation=60)
    plt.tight_layout(); plt.savefig(f'{O}/dbg/cqt_{i}.png',dpi=60)
