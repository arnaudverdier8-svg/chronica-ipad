import numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
Z=np.load(O+'/dbg/music_sus.npz'); S=Z['S']; t=Z['t']
words=json.load(open(O+'/../words.json'))['words']
Sd=20*np.log10(S/S.max()+1e-6)
fig,ax=plt.subplots(2,1,figsize=(30,14))
for i,(a,b) in enumerate([(0,33.5),(33,66.2)]):
    s,e=np.searchsorted(t,a),np.searchsorted(t,b)
    ax[i].imshow(Sd[36:,s:e],origin='lower',aspect='auto',extent=[t[s],t[e-1],12,96],vmin=-60,vmax=0,cmap='magma',interpolation='nearest')
    ax[i].set_yticks(range(12,96,12)); ax[i].set_yticklabels([f'C{k+1}' for k in range(1,8)])
    ax[i].set_xticks(np.arange(np.ceil(a),b,1)); ax[i].grid(alpha=.4,color='w')
    for w in words:
        if a<=w['start']<=b: ax[i].axvspan(w['start'],w['end'],ymin=.97,ymax=1,color='cyan',alpha=.8)
plt.tight_layout(); plt.savefig(O+'/dbg/sus.png',dpi=50)
