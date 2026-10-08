"""Stage 2: event detection, timeline JSON, per-frame sidecars.
Inputs: feat.npz (s1_features.py), dbg/music_sus.npz (dbg/musiccqt.py), ../words.json
Outputs: audio_timeline.json, audio_frames.npy (+ columns in JSON), audio_frames.csv, analysis.pkl (for plotting/report)"""
import json, pickle, numpy as np, librosa, scipy.ndimage as ndi, scipy.signal as sps

O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
F = np.load(f'{O}/feat.npz')
Z = np.load(f'{O}/dbg/music_sus.npz')
words = json.load(open(f'{O}/../words.json'))['words']
SR = 44100; FPS = 30; SPF = 1470
N = int(F['N']); NF = int(F['NF']); PAD = int(F['pad'])
DUR = N / SR
fr = lambda t: int(np.floor(t * FPS + 1e-9))  # frame whose display interval [f/30,(f+1)/30) contains t
tv = np.arange(NF) / FPS
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def norm01(v, pct=99.5):
    v = np.asarray(v, float); lo = np.min(v); hi = np.percentile(v, pct)
    return np.clip((v - lo) / (hi - lo + 1e-12), 0, 1)

# ------------------------------------------------------------------ narration structure
for w in words:
    w['f0'] = fr(w['start']); w['f1'] = fr(w['end'])
phr = []
cur = [words[0]]
for a, b in zip(words[:-1], words[1:]):
    gap = b['start'] - a['end']
    if gap >= 0.45 or a['w'][-1] in ',.?!':
        phr.append(cur); cur = [b]
    else:
        cur.append(b)
phr.append(cur)
phrases = []
for i, p in enumerate(phr):
    phrases.append(dict(id=f'P{i+1:02d}', text=' '.join(w['w'] for w in p), start=p[0]['start'], end=p[-1]['end'],
                        f_start=fr(p[0]['start']), f_end=fr(p[-1]['end']), n_words=len(p)))
# story beats (sentences grouped by meaning)
beat_def = [('B1', 'Golden age: one realm, one table, one oath, one crown', 'P01', 'P04'),
            ('B2', 'The oath: they raised their cups and swore it would never end', 'P05', 'P06'),
            ('B3', 'The king dies; every lord covets the empty chair / crown', 'P07', 'P10'),
            ('B4', 'Hundred years of war; ruin, forest, forgetting, darkness', 'P11', 'P15'),
            ('B5', 'Now: every ruler believes the world can be whole again; one banner, one village, one blank page', 'P16', 'P19'),
            ('B6', 'The question: what will the chronicles say of you?', 'P20', 'P21')]
pid = {p['id']: p for p in phrases}
beats = [dict(id=b, desc=d, start=pid[s]['start'], end=pid[e]['end'], f_start=pid[s]['f_start'], f_end=pid[e]['f_end'],
              phrases=[p['id'] for p in phrases if pid[s]['start'] <= p['start'] <= pid[e]['start']]) for b, d, s, e in beat_def]
# music-only gaps > 0.5 s (incl. head and tail)
gaps = []
edges = [(0.0, words[0]['start'])] + [(a['end'], b['start']) for a, b in zip(words[:-1], words[1:])] + [(words[-1]['end'], DUR)]
for a, b in edges:
    if b - a > 0.5:
        gaps.append(dict(start=a, end=b, dur=b - a, f_start=fr(a), f_end=fr(b)))

# ------------------------------------------------------------------ per-frame arrays
rms_db = F['pf_rms_db']; peak_db = F['pf_peak_db']; lufs = F['pf_lufs_momentary']
onset = norm01(F['pf_onset_strength']); flux = norm01(F['pf_spectral_flux'])
onset_low = norm01(F['pf_onset_low200']); flux_sub = norm01(F['pf_flux_sub80'])
narr = F['pf_narration'] > 0.5
# music level estimate: voice-suppressed sustained CQT power, calibrated to mix RMS in music-only gaps
S = Z['S']; tS = Z['t']; fb = Z['fb']
sus_pow = (S ** 2).sum(0)
sus_db_fine = 10 * np.log10(sus_pow + 1e-12)
idx = np.clip((tS * FPS).astype(int), 0, NF - 1)
acc = np.zeros(NF); cnt = np.zeros(NF); np.add.at(acc, idx, sus_pow); np.add.at(cnt, idx, 1)
sus_db = 10 * np.log10(acc / np.maximum(cnt, 1) + 1e-12)
gapmask = np.zeros(NF, bool)
for g in gaps:
    gapmask[g['f_start'] + 3:g['f_end'] - 2] = True
gapmask[fr(DUR) - 3:] = False
gapmask[:5] = False
offset = np.median(rms_db[gapmask] - sus_db[gapmask])
# --- music bed level: measured in music-only gaps, minimum-statistics estimate under narration
import soundfile as sf
_x, _ = sf.read(f'{O}/audio_f32.wav', dtype='float32'); _m = _x.mean(1)
_h = 441; _n = len(_m) // _h
_e = 20 * np.log10(np.sqrt((_m[:_n * _h].reshape(_n, _h) ** 2).mean(1)) + 1e-9)
_q = ndi.uniform_filter1d(ndi.percentile_filter(_e, 10, size=80, mode='nearest'), 30)
_tq = np.arange(_n) * 0.01
minstat = np.interp(tv + 1 / 60, _tq, _q)
cal = np.median(ndi.uniform_filter1d(rms_db, 5)[gapmask] - minstat[gapmask])
gap_core = np.zeros(NF, bool)
for g in gaps:
    gap_core[g['f_start'] + 2:g['f_end'] - 1] = True
gap_core[:5] = False
music_db = np.where(gap_core, ndi.uniform_filter1d(rms_db, 5), minstat + cal)
music_db[-2:] = music_db[-3]
music_db = ndi.uniform_filter1d(music_db, 7)
music_conf = np.where(gap_core, 1.0, 0.5)
music_db_slow = ndi.uniform_filter1d(music_db, 45)    # 1.5 s
# music note-onset novelty from sustained CQT (step edges preserved by the median filter)
lg = np.log(S + 1e-4 * S.max())
dd = np.maximum(0, np.diff(lg, axis=1, prepend=lg[:, :1])) * (S / S.max()) ** 0.5
nov_fine = ndi.uniform_filter1d(dd.sum(0), 5)
note_on = np.full(NF, -np.inf); np.maximum.at(note_on, idx, nov_fine); note_on = norm01(note_on)
# chroma of music (voice-suppressed)
nb = S.shape[0]
chroma_f = np.zeros((12, S.shape[1]))
for k in range(nb):
    chroma_f[(k // 3) % 12] += S[k]
cf = np.zeros((12, NF)); np.add.at(cf.T, idx, chroma_f.T); cf /= np.maximum(cnt, 1)
# ------------------------------------------------------------------ onsets (10 ms grid)
tf = F['tf']; env = F['on_env']
wspan = [(w['start'], w['end'], w['w']) for w in words]
def word_at(t, pad=0.05):
    for a, b, ww in wspan:
        if a - pad <= t <= b + pad: return ww
    return None
pk = librosa.util.peak_pick(env, pre_max=5, post_max=5, pre_avg=15, post_avg=15, delta=np.percentile(env, 75), wait=8)
onsets = []
emax = env[pk].max()
for i in pk:
    t = tf[i]; w = word_at(t)
    onsets.append(dict(time=round(float(t), 3), frame=fr(t), strength=round(float(min(env[i] / emax, 1)), 3), word=w,
                       src='voice+music' if w else 'music'))
onsets.sort(key=lambda o: -o['strength'])
# low-frequency transients (<200 Hz)
el = F['on_low']
pkl_ = librosa.util.peak_pick(el, pre_max=5, post_max=5, pre_avg=20, post_avg=20, delta=np.percentile(el, 90), wait=10)
elmax = el[pkl_].max()
low_tr = []
for i in pkl_:
    t = tf[i]; w = word_at(t, 0.03)
    low_tr.append(dict(time=round(float(t), 3), frame=fr(t), strength=round(float(min(el[i] / elmax, 1)), 3), word=w,
                       src='voice (narrator F0/plosive)' if w else 'music'))
low_tr.sort(key=lambda o: -o['strength'])
# music-note onsets (sustained-tone entries)
pkn = librosa.util.peak_pick(nov_fine, pre_max=20, post_max=20, pre_avg=40, post_avg=40, delta=np.percentile(nov_fine, 90) * 0.5, wait=25)
nmax = np.percentile(nov_fine[pkn], 99) if len(pkn) else 1
note_onsets = []
for i in pkn:
    t = tS[i]; w = word_at(t, 0.0)
    note_onsets.append(dict(time=round(float(t), 3), frame=fr(t), strength=round(float(min(nov_fine[i] / nmax, 1)), 3), word=w))
note_onsets.sort(key=lambda o: -o['strength'])

# ------------------------------------------------------------------ tempo / pulse
tempo_info = {}
for name, e, hop in [('full_mix_onset', F['on_env'], 441), ('music_bed_onset', F['bg_on'], 1024), ('low_band_onset', F['on_low'], 441)]:
    e0 = e - e.mean(); ac = librosa.autocorrelate(e0); ac /= ac[0]
    lags = np.arange(len(ac)) * hop / SR; sel = (lags > 0.3) & (lags < 2.0)
    k = np.argmax(ac[sel]); L = lags[sel][k]
    rng = np.random.default_rng(0)
    base = np.mean([(lambda a2: (a2 / a2[0])[sel].max())(librosa.autocorrelate(rng.permutation(e0))) for _ in range(20)])
    tmp, bts = librosa.beat.beat_track(onset_envelope=e, sr=SR, hop_length=hop)
    bt = librosa.frames_to_time(bts, sr=SR, hop_length=hop); ibi = np.diff(bt)
    tempo_info[name] = dict(ac_peak=round(float(ac[sel][k]), 3), ac_peak_lag_s=round(float(L), 3), ac_peak_bpm=round(60 / L, 1),
                            shuffled_baseline=round(float(base), 3), beat_track_bpm=round(float(np.atleast_1d(tmp)[0]), 1),
                            ibi_cv=round(float(ibi.std() / ibi.mean()), 3))
# syllable rate of narration for comparison
nsyl_rate = len(words) / sum(p['end'] - p['start'] for p in phrases)

# ------------------------------------------------------------------ silences / dips
sil = []
below = rms_db < -40
i = 0
while i < NF:
    if below[i]:
        j = i
        while j < NF and below[j]: j += 1
        if j - i >= 3:
            sil.append(dict(f_start=i, f_end=j - 1, start=round(i / FPS, 3), end=round(j / FPS, 3), dur=round((j - i) / FPS, 3),
                            min_db=round(float(rms_db[i:j].min()), 1), mean_db=round(float(rms_db[i:j].mean()), 1)))
        i = j
    else:
        i += 1
# relative dips of the music bed: music_db more than 8 dB under its 6 s running median
med6 = ndi.median_filter(music_db, 181, mode='nearest')
dipmask = music_db < med6 - 8
dips = []
i = 0
while i < NF:
    if dipmask[i]:
        j = i
        while j < NF and dipmask[j]: j += 1
        if j - i >= 6:
            k = i + np.argmin(music_db[i:j])
            dips.append(dict(f_start=i, f_end=j - 1, start=round(i / FPS, 3), end=round(j / FPS, 3), f_min=int(k), t_min=round(k / FPS, 3),
                             depth_db=round(float(med6[k] - music_db[k]), 1), music_db_min=round(float(music_db[k]), 1)))
        i = j
    else:
        i += 1

# ------------------------------------------------------------------ crescendos (music bed)
sm = ndi.uniform_filter1d(music_db, 31)  # ~1 s
cres = []
# local minima/maxima on 1 s smoothed curve with 2 s neighbourhood
mins = sps.argrelextrema(sm, np.less_equal, order=30)[0]
maxs = sps.argrelextrema(sm, np.greater_equal, order=30)[0]
for mx in maxs:
    prev = mins[mins < mx]
    if not len(prev): continue
    mn = prev[-1]
    rise = sm[mx] - sm[mn]; dur = (mx - mn) / FPS
    if rise >= 4 and dur >= 1.0:
        cres.append(dict(f_start=int(mn), f_peak=int(mx), start=round(mn / FPS, 3), peak=round(mx / FPS, 3), dur=round(dur, 2),
                         rise_db=round(float(rise), 1), slope_db_per_s=round(float(rise / dur), 2), peak_level_db=round(float(sm[mx]), 1)))
# dedupe (same min)
ded = {}
for c in cres:
    if c['f_start'] not in ded or ded[c['f_start']]['rise_db'] < c['rise_db']: ded[c['f_start']] = c
cres = sorted(ded.values(), key=lambda c: c['f_start'])
# macro arc: gap-level trend
for g in gaps:
    a, b = g['f_start'] + 3, max(g['f_start'] + 4, g['f_end'] - 2)
    g['mix_rms_db'] = round(float(rms_db[a:b].mean()), 1)
    g['music_db_est'] = round(float(music_db[a:b].mean()), 1)

# ------------------------------------------------------------------ chords per window (voice-suppressed chroma)
tmpl = {}
for r in range(12):
    for q, iv in [('', (0, 4, 7)), ('m', (0, 3, 7)), ('5', (0, 7)), ('sus2', (0, 2, 7)), ('maj7', (0, 4, 7, 11)), ('m7', (0, 3, 7, 10)), ('6', (0, 4, 7, 9)), ('add9', (0, 2, 4, 7))]:
        v = np.zeros(12); v[[(r + i) % 12 for i in iv]] = 1; v[r] += 0.5
        tmpl[NAMES[r] + q] = v / np.linalg.norm(v)
def chord_of(c):
    c = c / (np.linalg.norm(c) + 1e-12)
    best = max(tmpl, key=lambda k: tmpl[k] @ c)
    return best, float(tmpl[best] @ c)
def bass_of(a_t, b_t):
    s, e = np.searchsorted(tS, a_t), np.searchsorted(tS, b_t)
    v = S[:, s:e].mean(1)
    lowv = v[: 3 * 24 + 6]  # C1..~F3
    if lowv.max() < 0.05 * v.max(): return None
    k = np.argmax(lowv)
    semi = int(round(k / 3))
    return NAMES[semi % 12] + str(semi // 12 + 1)
chords = []
win = 15  # 0.5 s
for f0_ in range(0, NF - win + 1, win):
    c = cf[:, f0_:f0_ + win].mean(1)
    lab, sc = chord_of(c)
    chords.append(dict(f=f0_, t=round(f0_ / FPS, 2), chord=lab, score=round(sc, 2), bass=bass_of(f0_ / FPS, (f0_ + win) / FPS)))
# gap chords (cleanest)
for g in gaps:
    a, b = g['f_start'] + 3, max(g['f_start'] + 6, g['f_end'] - 2)
    lab, sc = chord_of(cf[:, a:b].mean(1)); g['chord_est'] = lab; g['chord_score'] = round(sc, 2)
    v = cf[:, a:b].mean(1); g['top_pcs'] = [NAMES[i] for i in np.argsort(v)[::-1][:4]]
# harmonic change points: chroma novelty (cosine distance between successive 1 s windows)
cfn = cf / (np.linalg.norm(cf, axis=0, keepdims=True) + 1e-9)
L_ = 30
hnov = np.zeros(NF)
for f in range(L_, NF - L_):
    a = cfn[:, f - L_:f].mean(1); b = cfn[:, f:f + L_].mean(1)
    hnov[f] = 1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
hnov = ndi.uniform_filter1d(hnov, 5)

# ------------------------------------------------------------------ section novelty (Foote) on music features
bands_oct = np.stack([np.log(S[i * 36:(i + 1) * 36].sum(0) + 1e-6) for i in range(8)])
feat = np.vstack([cfn, (lambda B: np.vstack([np.bincount(idx, weights=row, minlength=NF) / np.maximum(cnt, 1) for row in B]))(bands_oct) / 5.0,
                  (music_db - music_db.mean())[None] / 6.0])
feat = ndi.uniform_filter1d(feat, 15, axis=1)
D = 6  # downsample to 5 Hz
fd = feat[:, ::D]
fdn = (fd - fd.mean(1, keepdims=True)) / (fd.std(1, keepdims=True) + 1e-9)
fdn = fdn / (np.linalg.norm(fdn, axis=0, keepdims=True) + 1e-9)
SSM = fdn.T @ fdn
def foote(SSM, half):
    k = np.arange(-half, half)
    g = np.exp(-0.5 * ((k + 0.5) / (half / 2)) ** 2)
    K = np.outer(g, g) * np.outer(np.sign(k + 0.5), np.sign(k + 0.5))
    n = SSM.shape[0]; out = np.zeros(n)
    P_ = np.pad(SSM, half, mode='edge')
    for i in range(n):
        out[i] = (P_[i:i + 2 * half, i:i + 2 * half] * K).sum()
    return np.maximum(out, 0)
nov_s = foote(SSM, 20)   # +-4 s kernel
nov_l = foote(SSM, 40)   # +-8 s kernel
nov = norm01(nov_s / nov_s.max() + nov_l / nov_l.max(), 100)
nov_f = np.interp(np.arange(NF), np.arange(len(nov)) * D, nov)
pkb = sps.find_peaks(nov_f, distance=90, prominence=0.08)[0]
bounds = [dict(frame=int(p), time=round(p / FPS, 3), strength=round(float(nov_f[p]), 3)) for p in pkb]

# ------------------------------------------------------------------ fade / ending
# step-drop at end of narration and decay of the tail
seg = rms_db[fr(61.0):fr(62.3)]
drop_f = fr(61.0) + int(np.argmin(np.diff(ndi.uniform_filter1d(seg, 3))))
tail_a, tail_b = fr(62.0), fr(DUR) - 2
tl = lufs[tail_a:tail_b]
slope = np.polyfit(np.arange(len(tl)) / FPS, tl, 1)[0]
# last 100 ms micro-fade
import soundfile as sf
x, _ = sf.read(f'{O}/audio_f32.wav', dtype='float32'); mm = x.mean(1)
w5 = 220
e5 = np.array([np.sqrt(np.mean(mm[i:i + w5] ** 2)) for i in range(N - 44100, N - w5 + 1, w5)])
e5db = 20 * np.log10(e5 + 1e-12); t5 = (np.arange(len(e5)) * w5 + N - 44100) / SR
ref = np.median(e5db[:150])
micro_start = float(t5[np.nonzero(e5db > ref - 6)[0][-1]])
fade = dict(narration_end=words[-1]['end'], music_drop_frame=int(drop_f), music_drop_time=round(drop_f / FPS, 3),
            level_before_drop_db=round(float(np.mean(rms_db[fr(58.2):fr(59.4)])), 1), tail_start_level_lufs=round(float(np.mean(lufs[fr(62.0):fr(62.5)])), 1),
            tail_end_level_lufs=round(float(np.mean(lufs[fr(65.5):fr(66.0)])), 1), tail_decay_db_per_s=round(float(slope), 2),
            micro_fade_start=round(micro_start, 3), audio_end=round(DUR, 6),
            final_rms_db_last_second=round(float(20 * np.log10(np.sqrt(np.mean(mm[-44100:] ** 2)))), 1))

# ------------------------------------------------------------------ drone exit (66-76 Hz narrowband) & in-gap swells
from scipy.signal import butter, sosfiltfilt
_y = sosfiltfilt(butter(4, [66, 76], btype='band', fs=SR, output='sos'), mm)
_d = 20 * np.log10(np.sqrt(np.array([np.mean(_y[i:i + 2205] ** 2) for i in range(0, N - 2205, 2205)])) + 1e-9)  # 50 ms
_td = np.arange(len(_d)) * 0.05
_ref = np.median(_d[(_td > 13.45) & (_td < 14.85)])
_after = np.nonzero((_td > 16.5) & (_td < 19.0) & (ndi.uniform_filter1d(_d, 4) < _ref - 15))[0]
drone = dict(ref_level_db=round(float(_ref), 1), exit_time=round(float(_td[_after[0]]), 3) if len(_after) else None)
drone['exit_frame'] = fr(drone['exit_time']) if drone['exit_time'] else None
swells = []
for g in gaps:
    if g['dur'] < 0.7 or g['end'] > DUR - 0.5: continue
    a, b = g['f_start'] + 2, g['f_end']
    seg = rms_db[a:b]
    if len(seg) < 8: continue
    kmin = int(np.argmin(ndi.uniform_filter1d(seg, 3)))
    lvl_end = float(np.mean(seg[-4:])); lvl_min = float(ndi.uniform_filter1d(seg, 3)[kmin])
    if lvl_end - lvl_min >= 4 and kmin < len(seg) - 4:
        swells.append(dict(f_start=a + kmin, start=round((a + kmin) / FPS, 3), f_end=b, end=round(b / FPS, 3),
                           rise_db=round(lvl_end - lvl_min, 1), into_phrase=next(p['id'] for p in phrases if p['f_start'] >= b - 1)))
# ------------------------------------------------------------------ word-level emphasis
for w in words:
    a, b = w['f0'], max(w['f0'] + 1, w['f1'] + 1)
    w['peak_db'] = round(float(rms_db[a:b].max()), 1)
    sel = (F['tp'] >= w['start']) & (F['tp'] <= w['end'])
    ff = F['f0'][sel]; ff = ff[np.isfinite(ff)]
    w['f0_hz'] = round(float(np.median(ff)), 1) if len(ff) else None
    w['dur'] = round(w['end'] - w['start'], 2)
for p in phrases:
    ws = [w for w in words if p['start'] <= w['start'] <= p['end']]
    pdb = np.array([w['peak_db'] for w in ws]); pdur = np.array([w['dur'] for w in ws])
    f0s = [w['f0_hz'] for w in ws if w['f0_hz']]
    p['peak_db'] = round(float(pdb.max()), 1)
    p['median_f0_hz'] = round(float(np.median(f0s)), 1) if f0s else None
    # emphasis: loud + long + pitch accent
    score = (pdb - pdb.mean()) / 3 + (pdur - pdur.mean()) / 0.15
    if len(ws) > 1:
        k = int(np.argmax(score)); p['stressed_word'] = ws[k]['w']; p['stressed_word_time'] = ws[k]['start']; p['stressed_word_frame'] = ws[k]['f0']
    else:
        p['stressed_word'] = ws[0]['w']; p['stressed_word_time'] = ws[0]['start']; p['stressed_word_frame'] = ws[0]['f0']

# ------------------------------------------------------------------ save intermediate
cols = ['rms_db', 'peak_db', 'lufs_momentary', 'onset_strength', 'spectral_flux', 'onset_low200', 'flux_sub80', 'music_level_db',
        'music_level_db_slow', 'music_level_conf', 'music_note_onset', 'harmonic_novelty', 'section_novelty', 'narration', 'voiced_prob', 'centroid_hz',
        'perc_ratio', 'band_sub_20_60', 'band_bass_60_250', 'band_lowmid_250_500', 'band_mid_500_2k', 'band_pres_2k_6k', 'band_air_6k_16k']
arr = np.stack([rms_db, peak_db, lufs, onset, flux, onset_low, flux_sub, music_db, music_db_slow, music_conf, note_on, norm01(hnov), nov_f,
                narr.astype(float), F['pf_voiced_prob'], F['pf_centroid_hz'], F['pf_perc_ratio'],
                F['pf_band_sub_20_60'], F['pf_band_bass_60_250'], F['pf_band_lowmid_250_500'], F['pf_band_mid_500_2k'],
                F['pf_band_pres_2k_6k'], F['pf_band_air_6k_16k']], 1).astype(np.float32)
np.save(f'{O}/audio_frames.npy', arr)
with open(f'{O}/audio_frames.csv', 'w') as fh:
    fh.write('frame,time_s,' + ','.join(cols) + '\n')
    for i in range(NF):
        fh.write(f'{i},{i / FPS:.4f},' + ','.join(f'{v:.4f}' for v in arr[i]) + '\n')
pickle.dump(dict(N=N, NF=NF, PAD=PAD, DUR=DUR, words=words, phrases=phrases, beats=beats, gaps=gaps, onsets=onsets, low_tr=low_tr,
                 note_onsets=note_onsets, tempo=tempo_info, syl_rate=nsyl_rate, sil=sil, dips=dips, cres=cres, chords=chords,
                 hnov=hnov, bounds=bounds, drone=drone, swells=swells, nov=nov_f, fade=fade, cols=cols, arr=arr, offset=offset, integrated=float(F['integrated']),
                 cf=cf), open(f'{O}/analysis.pkl', 'wb'))
print('saved; music level offset', round(offset, 2))
