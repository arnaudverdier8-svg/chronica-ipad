import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, json
O='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
F=np.load(f'{O}/feat.npz')
words=json.load(open(O+'/../words.json'))['words']
mel=F['mel_db']; bg=F['bg_mel']; tf=F['tf']; t2=F['t2']
NF=int(F['NF']); tv=np.arange(NF)/30
for part,(a,b) in enumerate([(0,23),(22,45),(44,66.2)]):
    fig,ax=plt.subplots(5,1,figsize=(26,16),sharex=True)
    ax[0].imshow(mel,origin='lower',aspect='auto',extent=[0,tf[-1],0,128],vmin=mel.max()-80,vmax=mel.max(),cmap='magma')
    ax[0].set_ylabel('mel bin (20Hz..16k)')
    ax[1].imshow(bg,origin='lower',aspect='auto',extent=[0,t2[-1],0,128],vmin=bg.max()-80,vmax=bg.max(),cmap='magma')
    ax[1].set_ylabel('music bed est')
    ax[2].plot(tv,F['pf_rms_db'],lw=.7,label='rms'); ax[2].plot(tv,F['pf_lufs_momentary'],lw=1,label='LUFS-M'); ax[2].plot(tv,F['pf_music_bed_db'],lw=1,label='bed'); ax[2].plot(tv,F['pf_band_sub_20_60'],lw=.7,label='sub'); ax[2].plot(tv,F['pf_band_bass_60_250'],lw=.7,label='bass'); ax[2].legend(loc='upper left'); ax[2].grid(alpha=.3)
    ax[3].plot(tv,F['pf_onset_strength']/F['pf_onset_strength'].max(),lw=.7,label='onset'); ax[3].plot(tv,F['pf_onset_low200']/F['pf_onset_low200'].max(),lw=.7,label='low onset'); ax[3].plot(tv,F['pf_music_bed_onset']/F['pf_music_bed_onset'].max(),lw=.7,label='bed onset'); ax[3].legend(loc='upper left'); ax[3].grid(alpha=.3)
    ax[4].plot(F['tp'],F['f0'],'.',ms=2); ax[4].set_ylabel('f0')
    for w in words:
        if a<=w['start']<=b:
            for A in ax: A.axvspan(w['start'],w['end'],color='cyan',alpha=.08)
            ax[4].text(w['start'],380,w['w'],fontsize=8,rotation=60)
    ax[4].set_ylim(50,420)
    ax[-1].set_xlim(a,b); ax[-1].set_xticks(np.arange(np.ceil(a),b,0.5),minor=True); ax[-1].set_xticks(np.arange(np.ceil(a),b,1))
    for A in ax: A.grid(which='both',axis='x',alpha=.25)
    plt.tight_layout(); plt.savefig(f'{O}/dbg/explore_{part}.png',dpi=55)
