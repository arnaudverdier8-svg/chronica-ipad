"""Stage 2: event detection + per-frame sidecars.
Inputs : feat.npz (s1_features.py, full mix), feat_side.npz (s1b_side.py, side channel = voice-free music view), ../words.json
Outputs: audio_frames.npy, audio_frames.csv, analysis.pkl, audio_master_1984f_*.wav
Frame convention: frame = floor(t*30); frame f is displayed during [f/30, (f+1)/30)."""
import json, pickle, numpy as np, librosa, scipy.ndimage as ndi, scipy.signal as sps, soundfile as sf
from scipy.signal import butter, sosfiltfilt

O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
F = np.load(f'{O}/feat.npz'); G = np.load(f'{O}/feat_side.npz')
words = json.load(open(f'{O}/../words.json'))['words']
SR, FPS, SPF = 44100, 30, 1470
N = int(F['N']); NF = int(F['NF']); PAD = int(F['pad']); DUR = N / SR
fr = lambda t: int(np.floor(t * FPS + 1e-9))
tv = np.arange(NF) / FPS
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
r3 = lambda v: round(float(v), 3)
def norm01(v, pct=100):
    v = np.asarray(v, float); lo = np.min(v); hi = np.percentile(v, pct)
    return np.clip((v - lo) / (hi - lo + 1e-12), 0, 1)
x, _ = sf.read(f'{O}/audio_f32.wav', dtype='float32')
mid = x.mean(1); side = (x[:, 0] - x[:, 1]) / 2

# ============================================================ master audio padded to whole frames
master = np.vstack([x, np.zeros((PAD, 2), np.float32)])
assert len(master) == NF * SPF
sf.write(f'{O}/audio_master_1984f_f32.wav', master, SR, subtype='FLOAT')
sf.write(f'{O}/audio_master_1984f_s16.wav', master, SR, subtype='PCM_16')
tp_db = 20 * np.log10(np.abs(sps.resample_poly(x, 4, 1, axis=0)).max())  # true peak (4x oversampled)

# ============================================================ narration structure
for w in words:
    w['f_start'] = fr(w['start']); w['f_end'] = fr(w['end'])
groups, cur = [], [words[0]]
for a, b in zip(words[:-1], words[1:]):
    if b['start'] - a['end'] >= 0.45 or a['w'][-1] in ',.?!':
        groups.append(cur); cur = [b]
    else:
        cur.append(b)
groups.append(cur)
phrases = [dict(id=f'P{i + 1:02d}', text=' '.join(w['w'] for w in g), start=g[0]['start'], end=g[-1]['end'],
                f_start=fr(g[0]['start']), f_end=fr(g[-1]['end']), n_words=len(g)) for i, g in enumerate(groups)]
pid = {p['id']: p for p in phrases}
beat_def = [('B1', 'Golden age litany: one realm, one table, one oath, one crown', 'P01', 'P04'),
            ('B2', 'The oath: they raised their cups and swore it would never end', 'P05', 'P06'),
            ('B3', 'The king dies without heir; every lord eyes the empty chair and the crown', 'P07', 'P10'),
            ('B4', 'A hundred years of war: cities fall, roads swallowed, borders forgotten, the world grows dark', 'P11', 'P15'),
            ('B5', 'Now: every ruler believes the world can be made whole; one banner, one village, one blank page', 'P16', 'P19'),
            ('B6', 'The question: when this age is remembered, what will the chronicles say of you?', 'P20', 'P21')]
beats = [dict(id=b, desc=d, start=pid[s]['start'], end=pid[e]['end'], f_start=pid[s]['f_start'], f_end=pid[e]['f_end'],
              phrases=[p['id'] for p in phrases if pid[s]['start'] <= p['start'] <= pid[e]['start']]) for b, d, s, e in beat_def]
beats.append(dict(id='B7', desc='Music-only tail (title / logo)', start=words[-1]['end'], end=round(DUR, 6), f_start=fr(words[-1]['end']), f_end=NF - 1, phrases=[]))
gaps = []
for a, b in [(0.0, words[0]['start'])] + [(p['end'], q['start']) for p, q in zip(words[:-1], words[1:])] + [(words[-1]['end'], DUR)]:
    if b - a > 0.5:
        gaps.append(dict(start=r3(a), end=r3(b), dur=r3(b - a), f_start=fr(a), f_end=fr(b)))

# ============================================================ per-frame arrays (mix)
rms_db = F['pf_rms_db']; lufs = F['pf_lufs_momentary']
onset = norm01(F['pf_onset_strength']); flux = norm01(F['pf_spectral_flux'])
narr = F['pf_narration'] > 0.5
# ============================================================ music level from the side channel (voice-leak corrected)
side_p = (np.concatenate([side, np.zeros(PAD, np.float32)]).reshape(NF, SPF) ** 2).mean(1)
mid_p = (np.concatenate([mid, np.zeros(PAD, np.float32)]).reshape(NF, SPF) ** 2).mean(1)
LEAK = 10 ** (-27 / 10)  # side/mid power ratio measured inside words where music is quietest (28.2-31.8 s)
mus_p = np.maximum(side_p - LEAK * mid_p, 0.5 * side_p)  # correction capped at -3 dB
gap_core = np.zeros(NF, bool)
for g in gaps:
    gap_core[g['f_start'] + 2:g['f_end'] - 1] = True
gap_core[:6] = False; gap_core[NF - 3:] = False
cal = np.median(rms_db[gap_core] - 10 * np.log10(mus_p[gap_core] + 1e-14))
music_db = ndi.uniform_filter1d(10 * np.log10(mus_p + 1e-14) + cal, 5)
music_db_1s = ndi.uniform_filter1d(music_db, 31)
music_on = norm01(G['pf_side_onset'])

# ============================================================ onsets of the full mix (10 ms grid)
tf = F['tf']; env = F['on_env']
def word_at(t, pad=0.05):
    for w in words:
        if w['start'] - pad <= t <= w['end'] + pad: return w['w']
    return None
pk = librosa.util.peak_pick(env, pre_max=5, post_max=5, pre_avg=15, post_avg=15, delta=np.percentile(env, 75), wait=8)
emax = env[pk].max()
onsets = sorted([dict(time=r3(tf[i]), frame=fr(tf[i]), strength=r3(env[i] / emax), word=word_at(tf[i]),
                      source='narration attack (+music)' if word_at(tf[i]) else 'music') for i in pk], key=lambda o: -o['strength'])

# ============================================================ low-frequency transients
el = F['on_low']  # (a) full mix <200 Hz: dominated by the narrator (F0 ~73-134 Hz)
pkl = librosa.util.peak_pick(el, pre_max=5, post_max=5, pre_avg=20, post_avg=20, delta=np.percentile(el, 90), wait=10)
low_mix = sorted([dict(time=r3(tf[i]), frame=fr(tf[i]), strength=r3(el[i] / el[pkl].max()), word=word_at(tf[i], 0.03),
                       source='narrator' if word_at(tf[i], 0.03) else 'music') for i in pkl], key=lambda o: -o['strength'])
# (b) side channel 22-120 Hz step rises = music bass entries / swells (voice-free)
ys = sosfiltfilt(butter(4, [22, 120], btype='band', fs=SR, output='sos'), side)
h = 441; n10 = len(ys) // h; t10 = np.arange(n10) * 0.01
eb = ndi.uniform_filter1d(10 * np.log10((ys[:n10 * h].reshape(n10, h) ** 2).mean(1) + 1e-12), 5)
rise = eb - np.array([eb[max(0, i - 15):i + 1].min() for i in range(n10)])
pkb, _ = sps.find_peaks(rise, height=9, distance=40)
bass = []
for i in pkb:
    after = float(eb[i:i + 30].mean())
    if after > np.median(eb) - 6:
        bass.append(dict(time=r3(t10[i]), frame=fr(t10[i]), rise_db=round(float(rise[i]), 1), level_after_db=round(after, 1), word=word_at(t10[i], 0.0)))
bmax = max(b['rise_db'] for b in bass if b['time'] > 1)
for b in bass:
    b['strength'] = r3(min(1, b['rise_db'] / bmax) * np.clip((b['level_after_db'] + 60) / 20, 0.2, 1))
grid_ev = [b for b in bass if 42.5 <= b['time'] <= 58.0 and b['rise_db'] >= 13]
gt = np.array([b['time'] for b in grid_ev])
pulse = None
if len(gt) >= 4:
    kk = np.round((gt - gt[0]) / 2.1)
    P_, t0_ = np.polyfit(kk, gt, 1)
    resid = gt - (t0_ + P_ * kk)
    pulse = dict(section='42.78-57.55 s (bass returns until the final recession)', events=[r3(v) for v in gt], bar_index=[int(k) for k in kk], period_s=r3(P_), bpm_if_4_beats_per_bar=round(240 / P_, 1),
                 phase_t0=r3(t0_), max_residual_ms=round(float(np.abs(resid).max() * 1000), 0),
                 extrapolated=[r3(t0_ + P_ * k) for k in range(int(kk.max()) + 1, int(kk.max()) + 3)])

# ============================================================ tempo / pulse statistics
tempo = {}
for name, e, hop in [('full_mix_onset', F['on_env'], 441), ('side_music_onset', G['on'], 441), ('side_low_onset', G['on_low'], 441)]:
    e0 = e - e.mean(); ac = librosa.autocorrelate(e0); ac /= ac[0]
    lags = np.arange(len(ac)) * hop / SR; sel = (lags > 0.3) & (lags < 2.5)
    k = np.argmax(ac[sel]); L = lags[sel][k]
    rng = np.random.default_rng(0)
    base = np.mean([(lambda a2: (a2 / a2[0])[sel].max())(librosa.autocorrelate(rng.permutation(e0))) for _ in range(20)])
    tmp, bts = librosa.beat.beat_track(onset_envelope=e, sr=SR, hop_length=hop)
    bt = librosa.frames_to_time(bts, sr=SR, hop_length=hop); ibi = np.diff(bt)
    tempo[name] = dict(autocorr_peak=r3(ac[sel][k]), autocorr_peak_lag_s=r3(L), autocorr_peak_bpm=round(60 / L, 1),
                       shuffled_baseline=r3(base), librosa_beat_track_bpm=round(float(np.atleast_1d(tmp)[0]), 1), beat_ibi_cv=r3(ibi.std() / ibi.mean()))
words_per_s = len(words) / sum(p['end'] - p['start'] for p in phrases)

# ============================================================ silences / dips
def runs(mask, minlen):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]: j += 1
            if j - i >= minlen: out.append((i, j))
            i = j
        else:
            i += 1
    return out
silences = [dict(f_start=a, f_end=b - 1, start=r3(a / FPS), end=r3(b / FPS), dur=r3((b - a) / FPS), min_db=round(float(rms_db[a:b].min()), 1),
                 mean_db=round(float(rms_db[a:b].mean()), 1)) for a, b in runs(rms_db < -40, 3)]
med6 = ndi.median_filter(music_db, 181, mode='nearest')
dips = []
for a, b in runs(music_db < med6 - 8, 6):
    k = a + int(np.argmin(music_db[a:b]))
    dips.append(dict(f_start=a, f_end=b - 1, start=r3(a / FPS), end=r3(b / FPS), f_min=k, t_min=r3(k / FPS),
                     depth_db=round(float(med6[k] - music_db[k]), 1), music_db_min=round(float(music_db[k]), 1)))

# ============================================================ crescendos (music level, 1 s smoothing)
sm = music_db_1s
mins = sps.argrelextrema(sm, np.less_equal, order=30)[0]; maxs = sps.argrelextrema(sm, np.greater_equal, order=30)[0]
cres = {}
for mx in maxs:
    prev = mins[mins < mx]
    if not len(prev): continue
    mn = prev[-1]; rise_ = sm[mx] - sm[mn]; dur = (mx - mn) / FPS
    if rise_ >= 4 and dur >= 1.0 and mn > 10:
        c = dict(f_start=int(mn), f_peak=int(mx), start=r3(mn / FPS), peak=r3(mx / FPS), dur=round(dur, 2), rise_db=round(float(rise_), 1),
                 slope_db_per_s=round(float(rise_ / dur), 2), peak_music_db=round(float(sm[mx]), 1))
        if mn not in cres or cres[mn]['rise_db'] < c['rise_db']: cres[mn] = c
cres = sorted(cres.values(), key=lambda c: c['f_start'])
for g in gaps:
    a, b = g['f_start'] + 3, max(g['f_start'] + 4, g['f_end'] - 2)
    g['mix_rms_db'] = round(float(rms_db[a:b].mean()), 1); g['music_db'] = round(float(music_db[a:b].mean()), 1)
swells = []
for g in gaps:
    if g['dur'] < 0.7 or g['end'] > DUR - 0.5: continue
    a, b = g['f_start'] + 2, g['f_end'] + 3   # include 0.1 s into the next phrase (music level is voice-free)
    seg = music_db[a:b]; kmin = int(np.argmin(seg)); end_lvl = float(seg[-4:].mean())
    if end_lvl - seg[kmin] >= 4 and kmin < len(seg) - 4:
        swells.append(dict(start=r3((a + kmin) / FPS), f_start=a + kmin, end=r3(b / FPS), f_end=b, rise_db=round(end_lvl - float(seg[kmin]), 1),
                           into_phrase=next(p['id'] for p in phrases if p['f_start'] >= g['f_end'] - 1)))
valley = min((g for g in gaps if 20 < g['start'] < 40), key=lambda g: g['mix_rms_db'])
climax = max((g for g in gaps if g['end'] < DUR - 1), key=lambda g: g['mix_rms_db'])
kpk = int(np.argmax(np.where((tv > 40) & (tv < 61.7), music_db_1s, -999)))
macro = dict(start=valley['start'], f_start=valley['f_start'], valley_level_db=valley['mix_rms_db'], peak_gap=[climax['start'], climax['end']],
             peak_gap_frames=[climax['f_start'], climax['f_end']], peak_gap_level_db=climax['mix_rms_db'], rise_db=round(climax['mix_rms_db'] - valley['mix_rms_db'], 1),
             peak_music_1s_time=r3(kpk / FPS), peak_music_1s_frame=kpk, peak_music_1s_db=round(float(music_db_1s[kpk]), 1))

# ============================================================ harmony (side-channel chroma)
cf = G['cf']; cfn = cf / (np.linalg.norm(cf, axis=0, keepdims=True) + 1e-9)
tmpl = {}
for r in range(12):
    for q, iv in [('', (0, 4, 7)), ('m', (0, 3, 7)), ('5', (0, 7)), ('sus2', (0, 2, 7)), ('maj7', (0, 4, 7, 11)), ('m7', (0, 3, 7, 10)),
                  ('6', (0, 4, 7, 9)), ('add9', (0, 2, 4, 7)), ('m(add9)', (0, 2, 3, 7))]:
        v = np.zeros(12); v[[(r + i) % 12 for i in iv]] = 1; v[r] += 0.5; tmpl[NAMES[r] + q] = v / np.linalg.norm(v)
def chord_of(c):
    c = c / (np.linalg.norm(c) + 1e-12); best = max(tmpl, key=lambda k: tmpl[k] @ c); return best, float(tmpl[best] @ c)
for g in gaps:
    a, b = g['f_start'] + 3, max(g['f_start'] + 6, g['f_end'] - 2)
    v = cf[:, a:b].mean(1); lab, sc = chord_of(v)
    g['chord_est'] = lab; g['chord_fit'] = round(sc, 2); g['top_pitch_classes'] = [NAMES[i] for i in np.argsort(v)[::-1][:4]]
chords = []
for f0_ in range(0, NF - 15 + 1, 15):
    lab, sc = chord_of(cf[:, f0_:f0_ + 15].mean(1)); chords.append(dict(frame=f0_, time=round(f0_ / FPS, 2), chord=lab, fit=round(sc, 2)))
key_prof = cf[:, 5:fr(61.8)].sum(1)
ks_major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]); ks_minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
keys = sorted([(round(float(np.corrcoef(np.roll(p, r), key_prof)[0, 1]), 3), NAMES[r] + (' major' if p is ks_major else ' minor')) for r in range(12) for p in (ks_major, ks_minor)], reverse=True)[:3]
L_ = 30
hnov = np.zeros(NF)
for f in range(L_, NF - L_):
    a = cfn[:, f - L_:f].mean(1); b = cfn[:, f:f + L_].mean(1)
    hnov[f] = 1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
hnov = ndi.uniform_filter1d(hnov, 5)
hpk, _ = sps.find_peaks(hnov, distance=45, prominence=0.04)
harm_changes = sorted([dict(frame=int(p), time=r3(p / FPS), strength=r3(hnov[p] / hnov[hpk].max())) for p in hpk], key=lambda d: -d['strength'])

# ============================================================ section novelty (Foote) on side-channel music features
bandsS = np.stack([G['pf_side_band_' + k] for k in ['sub_20_60', 'bass_60_250', 'lowmid_250_500', 'mid_500_2k', 'pres_2k_6k', 'air_6k_16k']])
feat = np.vstack([cfn, (bandsS - bandsS.mean(1, keepdims=True)) / 8.0, (music_db - music_db.mean())[None] / 6.0])
feat = ndi.uniform_filter1d(feat, 15, axis=1)
D = 6; fd = feat[:, ::D]
fdn = (fd - fd.mean(1, keepdims=True)) / (fd.std(1, keepdims=True) + 1e-9)
fdn = fdn / (np.linalg.norm(fdn, axis=0, keepdims=True) + 1e-9)
SSM = fdn.T @ fdn
def foote(S_, half):
    k = np.arange(-half, half); g = np.exp(-0.5 * ((k + 0.5) / (half / 2)) ** 2)
    K = np.outer(g, g) * np.outer(np.sign(k + 0.5), np.sign(k + 0.5)); P_ = np.pad(S_, half, mode='edge')
    return np.maximum(np.array([(P_[i:i + 2 * half, i:i + 2 * half] * K).sum() for i in range(S_.shape[0])]), 0)
nv = foote(SSM, 20); nv2 = foote(SSM, 40)
nov = nv / nv.max() + nv2 / nv2.max(); nov /= nov.max()
nov_f = np.interp(np.arange(NF), np.arange(len(nov)) * D, nov)
pkn, _ = sps.find_peaks(nov_f, distance=90, prominence=0.06)
novelty_peaks = [dict(frame=int(p), time=r3(p / FPS), strength=r3(nov_f[p])) for p in pkn]

# ============================================================ drone exit / music start / ending
yd = sosfiltfilt(butter(4, [66, 76], btype='band', fs=SR, output='sos'), side)
ed = ndi.uniform_filter1d(10 * np.log10((yd[:n10 * h].reshape(n10, h) ** 2).mean(1) + 1e-12), 10)
ref = np.median(ed[(t10 > 13.5) & (t10 < 14.8)])
def first_below(db, a, b):
    s = np.nonzero((t10 > a) & (t10 < b) & (ed < ref - db))[0]; return r3(t10[s[0]]) if len(s) else None
drone = dict(pitch='D (open fifth D2-A2-D3-A3; lowest partial ~71 Hz = flat D2)', ref_level_db=round(float(ref), 1),
             fade_begin=first_below(6, 16.0, 19.5), minus15db=first_below(15, 16.0, 19.5), minus25db=first_below(25, 16.0, 19.5))
for k in ('fade_begin', 'minus15db', 'minus25db'):
    drone[k + '_frame'] = fr(drone[k]) if drone[k] else None
music_start = dict(first_sample_above_m60dBFS=r3(np.nonzero(np.abs(mid) > 1e-3)[0][0] / SR),
                   drone_within_6dB_of_full=r3(t10[np.nonzero((t10 < 2) & (ed > ref - 6))[0][0]]))
clim_lvl = float(np.median(music_db[climax['f_start'] + 3:climax['f_end'] - 1]))
fs_ = max(f for f in range(fr(57.0), fr(61.8)) if music_db[f] >= clim_lvl - 3)
fe_ = next(f for f in range(fs_, NF) if music_db[f] <= clim_lvl - 17)
base_low = np.median(eb[(t10 > 58.2) & (t10 < 59.4)])
bass_gone = t10[np.nonzero((t10 > 59.4) & (ndi.uniform_filter1d(eb, 10) < base_low - 20))[0][0]]
tl = lufs[fr(62.0):NF - 3]; slope = np.polyfit(np.arange(len(tl)) / FPS, tl, 1)[0]
w5 = 220; e5 = 20 * np.log10(np.array([np.sqrt(np.mean(mid[i:i + w5] ** 2)) for i in range(N - 44100, N - w5 + 1, w5)]) + 1e-12)
t5 = (np.arange(len(e5)) * w5 + N - 44100) / SR
micro = float(t5[np.nonzero(e5 > np.median(e5[:150]) - 6)[0][-1]])
fade = dict(narration_end=words[-1]['end'], narration_end_frame=fr(words[-1]['end']), music_fade_start=r3(fs_ / FPS), music_fade_start_frame=fs_,
            music_fade_end=r3(fe_ / FPS), music_fade_end_frame=fe_, music_fade_depth_db=round(clim_lvl - float(np.mean(music_db[fe_:fe_ + 15])), 1),
            bass_gone_time=r3(bass_gone), bass_gone_frame=fr(bass_gone),
            music_before_drop_db=climax['mix_rms_db'], tail_music_db=round(float(np.mean(music_db[fr(62.2):fr(65.8)])), 1),
            tail_lufs_start=round(float(np.mean(lufs[fr(62.0):fr(62.5)])), 1), tail_lufs_end=round(float(np.mean(lufs[fr(65.5):fr(66.0)])), 1),
            tail_decay_db_per_s=round(float(slope), 2), last_second_rms_db=round(float(20 * np.log10(np.sqrt(np.mean(mid[-SR:] ** 2)))), 1),
            micro_fade_start=r3(micro), micro_fade_frame=fr(micro), audio_end=round(DUR, 6), last_audio_frame=fr(DUR - 1e-6))

# ============================================================ word / phrase emphasis
f0 = F['f0']; tp = F['tp']
inw_p = np.zeros(len(tp), bool)
for w in words:
    a, b = w['f_start'], max(w['f_start'] + 1, w['f_end'] + 1)
    w['peak_db'] = round(float(rms_db[a:b].max()), 1)
    sel = (tp >= w['start']) & (tp <= w['end']); inw_p |= sel
    ff = f0[sel]; ff = ff[np.isfinite(ff)]
    w['f0_hz'] = round(float(np.median(ff)), 1) if len(ff) else None
    w['dur'] = round(w['end'] - w['start'], 2)
FUNC = {'there', 'was', 'a', 'when', 'the', 'and', 'it', 'who', 'had', 'at', 'that', 'his', 'to', 'were', 'by', 'what', 'their', 'its', 'can', 'be', 'this', 'is', 'will', 'of', 'they', 'then', 'only', 'would'}
for p in phrases:
    ws = [w for w in words if p['start'] <= w['start'] <= p['end']]
    pdb = np.array([w['peak_db'] for w in ws]); pdur = np.array([w['dur'] for w in ws])
    p['peak_db'] = round(float(pdb.max()), 1)
    f0s = [w['f0_hz'] for w in ws if w['f0_hz']]; p['median_f0_hz'] = round(float(np.median(f0s)), 1) if f0s else None
    content = np.array([w['w'].strip(',.?').lower() not in FUNC for w in ws], float)
    score = (pdb - pdb.mean()) / 3 + (pdur - pdur.mean()) / 0.15 + content * 3
    k = int(np.argmax(score)); p['stressed_word'] = ws[k]['w']; p['stressed_word_time'] = ws[k]['start']; p['stressed_word_frame'] = ws[k]['f_start']
nf0 = f0[inw_p & np.isfinite(f0)]
nar_f0 = [round(float(np.median(nf0)), 1), round(float(np.percentile(nf0, 10)), 1), round(float(np.percentile(nf0, 90)), 1)]

# ============================================================ curated music sections
sections = [
    dict(id='M0', start=0.0, end=round(4 / 30, 6), label='Digital near-silence (4 frames)', music='Nothing audible (-73..-90 dBFS).'),
    dict(id='M1', start=round(4 / 30, 6) + 1e-6, end=16.8, label='Drone / golden age',
         music='Fast fade-in (~0.5 s) of a dark D pedal drone (open fifth D-A, lowest partial ~71 Hz with ~30-cent, 6-8 Hz wobble) under a soft, '
               'very wide sustained pad. No percussion. The drone re-swells in narration gaps; music-only level -38 dBFS (3.5 s) rising to -31 dBFS (13.4 s).'),
    dict(id='M2', start=16.8, end=26.6, label='Lament (drone exits)',
         music='The D drone fades from ~16.8 s (-15 dB at ~17.8 s, -25 dB by ~18.3 s, i.e. under "and left no heir"). Mid-register sustained chords take over '
               '(D minor 7 -> F major 7 colour, energy 250 Hz-2 kHz, no sub-bass) with ensemble-like pitch wobble (10-12 cents at 6-7 Hz): string-section / choir-pad timbre. '
               'Music-only level ~-31 dBFS; fullest around 23-25.5 s.'),
    dict(id='M3', start=26.6, end=33.9, label='Hollow war (music almost silent)',
         music='Right after "...beneath the crown." the music collapses by ~20 dB (from ~-27 dBFS at 25 s to -47 dBFS at 27 s) and stays at or below about -45 dBFS '
               'for ~7 s: under the whole of "The wars lasted a hundred years and ended nothing." and the start of "Cities fell to ruin." Only a thin, airy, high, '
               'bass-less texture remains (no sub-bass, no percussion). Two fully exposed near-silent gaps: 26.6-28.1 s and 31.8-32.7 s (-47 dBFS).'),
    dict(id='M4', start=33.9, end=42.7, label='Ruin plateau (soft pad returns)',
         music='A soft, mid-register Dm(add9) pad returns at ~33.9-34.0 s (+5 dB) and holds a plateau around -40 dBFS under "Roads were swallowed by the forest" and '
               '"Men forgot what lay beyond their own borders", creeping up to ~-36 dBFS by 41.5 s; a D7 colour (F# appears) in the 41 s gap. Still no bass below ~60 Hz.'),
    dict(id='M5', start=42.7, end=59.46, label='Rise to climax (bass returns, slow bar pulse)',
         music='Big low-register entry at 42.78 s on "the world grew dark" (+26 dB in 22-120 Hz), then bass swells every ~2.1 s '
               '(42.78, 44.85, 47.00, 49.06, 51.21, 53.30, 55.49, 57.55 s): a slow bar pulse (~114 bpm if 4 beats per bar). Fullest, widest, brightest '
               'texture of the piece: a sustained Bb3 (233 Hz, strong 2nd-6th partials, ~10-cent vibrato: horn / cello / choir-like) over F and Bb major-7 '
               'harmony; music-only level -32.5 dBFS (44.5 s) -> -30 (50 s) -> -25.6 dBFS in the climax gap 58.14-59.46 s (loudest music of the piece, Bbmaj7 colour).'),
    dict(id='M6', start=59.46, end=61.84, label='Recession under the question',
         music='From ~59.4 s, exactly as "what will the chronicles say of you?" begins, the music pulls back ~19 dB in ~1.4 s (-25 dBFS -> -44 dBFS by ~60.8 s); '
               'the bass is gone by ~60.8 s. The final words sit almost alone over a faint high chord.'),
    dict(id='M7', start=61.84, end=round(DUR, 3), label='Tail (ring-out, no narration)',
         music='After the last word (61.84 s) only a soft, very stable (pitch sd 4 cents), bass-less and dark (nothing above ~2 kHz) high chord remains '
               '(G5-E5-A5-C6 partials: an open, unresolved Am7/C6 colour, not the D-minor tonic), decaying ~1 dB/s from -39 to -44 LUFS. '
               'The file ends at 66.107 s while still at ~-48 dBFS, with only a ~30 ms micro-fade: an abrupt end unless the picture covers it.'),
]
for s in sections:
    s['f_start'] = fr(s['start']); s['f_end'] = fr(s['end'])

# ============================================================ musical accents (top 30, merged, deduped)
cands = [dict(time=o['time'], strength=o['strength'], kind='onset', source=o['source'], word=o['word']) for o in onsets]
cands += [dict(time=b['time'], strength=b['strength'], kind='bass_entry', source='music (side-channel 22-120 Hz rise)', word=b['word']) for b in bass if b['time'] > 1]
cands.sort(key=lambda c: -c['strength'])
accents = []
for c in cands:
    if all(abs(c['time'] - a['time']) > 0.2 for a in accents):
        accents.append(c)
    if len(accents) >= 30: break
for a in accents: a['frame'] = fr(a['time'])

# ============================================================ save
cols = ['rms_db', 'peak_db', 'lufs_momentary', 'onset_strength', 'spectral_flux', 'onset_low200', 'music_level_db', 'music_level_db_1s',
        'music_onset_side', 'harmonic_novelty', 'section_novelty', 'narration', 'voiced_prob', 'centroid_hz', 'perc_ratio',
        'band_sub_20_60', 'band_bass_60_250', 'band_lowmid_250_500', 'band_mid_500_2k', 'band_pres_2k_6k', 'band_air_6k_16k']
arr = np.stack([rms_db, F['pf_peak_db'], lufs, onset, flux, norm01(F['pf_onset_low200']), music_db, music_db_1s, music_on, norm01(hnov), nov_f,
                narr.astype(float), F['pf_voiced_prob'], F['pf_centroid_hz'], F['pf_perc_ratio'], F['pf_band_sub_20_60'], F['pf_band_bass_60_250'],
                F['pf_band_lowmid_250_500'], F['pf_band_mid_500_2k'], F['pf_band_pres_2k_6k'], F['pf_band_air_6k_16k']], 1).astype(np.float32)
np.save(f'{O}/audio_frames.npy', arr)
with open(f'{O}/audio_frames.csv', 'w') as fh:
    fh.write('frame,time_s,' + ','.join(cols) + '\n')
    for i in range(NF):
        fh.write(f'{i},{i / FPS:.4f},' + ','.join(f'{v:.4f}' for v in arr[i]) + '\n')
pickle.dump(dict(N=N, NF=NF, PAD=PAD, DUR=DUR, words=words, phrases=phrases, beats=beats, gaps=gaps, onsets=onsets, low_mix=low_mix, bass=bass,
                 pulse=pulse, tempo=tempo, words_per_s=words_per_s, silences=silences, dips=dips, cres=cres, macro=macro, chords=chords, keys=keys,
                 swells=swells, harm_changes=harm_changes, novelty_peaks=novelty_peaks, drone=drone, music_start=music_start, fade=fade, sections=sections,
                 accents=accents, cols=cols, arr=arr, cal=float(cal), integrated=float(F['integrated']), true_peak_db=float(tp_db),
                 sample_peak_db=float(20 * np.log10(np.abs(x).max())), nar_f0=nar_f0), open(f'{O}/analysis.pkl', 'wb'))
print('ok cal', round(cal, 2), '| tp', round(tp_db, 2))
for k in ['pulse', 'drone', 'music_start', 'fade', 'macro', 'keys']:
    print(k, eval(k))
