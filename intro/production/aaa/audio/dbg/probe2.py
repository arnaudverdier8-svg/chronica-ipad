import numpy as np, json, librosa, scipy.ndimage as ndi
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
F=np.load(O+'/feat.npz'); NF=int(F['NF'])
r=F['pf_rms_db']; L=F['pf_lufs_momentary']; bed=F['pf_music_bed_db']
print('first 12 frames rms', np.round(r[:12],1))
print('last 12 frames rms', np.round(r[-12:],1))
print('frames 1850-1984 every 6 rms', np.round(r[1850::6],1))
print('LUFS-M 1840.. every 6', np.round(L[1840::6],1))
words=json.load(open(O+'/../words.json'))['words']
# gap levels
ws=[(w['start'],w['end']) for w in words]
gaps=[(0,ws[0][0])]+[(ws[i][1],ws[i+1][0]) for i in range(len(ws)-1) if ws[i+1][0]-ws[i][1]>0.5]+[(ws[-1][1],NF/30)]
for a,b in gaps:
    fa,fb=int(np.ceil(a*30))+2,int(b*30)-1
    if fb>fa: print(f'gap {a:6.2f}-{b:6.2f} dur {b-a:.2f} rms {r[fa:fb].mean():6.1f} LUFS-M(min) {L[fa:fb].min():6.1f} bed {bed[fa:fb].mean():6.1f}')
Hs=np.load(O+'/dbg/cqt_sus.npy'); t=np.arange(Hs.shape[1])*512/44100
lg=np.log(Hs+1e-4*Hs.max())
d=np.maximum(0,np.diff(lg,axis=1,prepend=lg[:,:1]))
w=(Hs/Hs.max())**0.5
nov=(d*w).sum(0)
nov=ndi.uniform_filter1d(nov,5)
p=librosa.util.peak_pick(nov,pre_max=20,post_max=20,pre_avg=40,post_avg=40,delta=np.percentile(nov,90)*0.5,wait=30)
p=p[np.argsort(nov[p])[::-1]]
print('sustained-note onsets (top 40):')
for i in p[:40]:
    tt=t[i]; inw=any(a-0.05<=tt<=b+0.05 for a,b in ws)
    print(f'  t={tt:6.2f} f={int(tt*30):4d} s={nov[i]/nov[p].max():.2f} {"(in word)" if inw else ""}')
np.save(O+'/dbg/sus_nov.npy',nov)
