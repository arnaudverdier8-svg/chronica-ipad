import numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
Z=np.load(O+'/feat_side.npz'); C=Z['Cdb']; t=Z['tc']
words=json.load(open(O+'/../words.json'))['words']
fig,ax=plt.subplots(3,1,figsize=(30,18))
for i,(a,b) in enumerate([(0,22.5),(22,44.5),(44,66.2)]):
    s,e=np.searchsorted(t,a),np.searchsorted(t,b)
    ax[i].imshow(C[:,s:e],origin='lower',aspect='auto',extent=[t[s],t[e-1],0,96],vmin=-65,vmax=-5,cmap='magma',interpolation='nearest')
    ax[i].set_yticks(range(0,96,12)); ax[i].set_yticklabels([f'C{k+1}' for k in range(8)])
    ax[i].set_xticks(np.arange(np.ceil(a),b,1)); ax[i].grid(alpha=.35,color='w')
    for w in words:
        if a<=w['start']<=b: ax[i].axvspan(w['start'],w['end'],ymin=.97,ymax=1,color='cyan',alpha=.8)
plt.tight_layout(); plt.savefig(O+'/dbg/side_cqt.png',dpi=48)
