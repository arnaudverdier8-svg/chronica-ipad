"""Stage 1: decode-level facts + dense features.
Outputs feat.npz (fine 10 ms grid + per-video-frame grid)."""
import json, numpy as np, soundfile as sf, librosa, pyloudnorm as pyln, scipy.signal as sps, time
O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
W = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/words.json'
t0 = time.time()
x, sr = sf.read(f'{O}/audio_f32.wav', dtype='float32')
assert sr == 44100
N = len(x)
FPS = 30
SPF = sr // FPS  # 1470 samples per video frame
NF = int(np.ceil(N / SPF))  # 1984
pad = NF * SPF - N
xp = np.vstack([x, np.zeros((pad, 2), np.float32)])
m = xp.mean(1)

# ---------- per-video-frame RMS (exact frame windows) ----------
fr = m.reshape(NF, SPF)
rms_db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-10)
peak_db = 20 * np.log10(np.abs(fr).max(1) + 1e-10)

# ---------- K-weighted momentary loudness (400 ms, centered on frame center) ----------
meter = pyln.Meter(sr)
xk = xp.astype(np.float64).copy()
for f in meter._filters.values():
    xk = np.stack([f.apply_filter(xk[:, c]) for c in range(2)], 1)
ms = (xk ** 2).sum(1)  # sum of channel mean squares (G=1 for L/R)
win = int(0.4 * sr)
cs = np.concatenate([[0], np.cumsum(ms)])
centers = (np.arange(NF) + 0.5) * SPF
a = np.clip((centers - win / 2).astype(int), 0, len(ms)); b = np.clip((centers + win / 2).astype(int), 0, len(ms))
lufs_m = -0.691 + 10 * np.log10((cs[b] - cs[a]) / np.maximum(b - a, 1) + 1e-12)
integrated = meter.integrated_loudness(x.astype(np.float64))

# ---------- fine grid: 10 ms hop ----------
H = 441
NFFT = 2048
S = np.abs(librosa.stft(m, n_fft=NFFT, hop_length=H, center=True))  # (1025, T)
T = S.shape[1]
tf = np.arange(T) * H / sr
freqs = librosa.fft_frequencies(sr=sr, n_fft=NFFT)
P = S ** 2
logS = np.log1p(100 * S)

# spectral flux (positive log-magnitude diff, L1) whole band and low band
d = np.diff(logS, axis=1, prepend=logS[:, :1])
d = np.maximum(d, 0)
flux = d.sum(0)
lowb = (freqs >= 20) & (freqs < 200)
subb = (freqs >= 20) & (freqs < 80)
flux_low = d[lowb].sum(0)
flux_sub = d[subb].sum(0)

# librosa onset strength (mel, max-filtered = superflux-like)
on_env = librosa.onset.onset_strength(y=m, sr=sr, hop_length=H, n_fft=NFFT, lag=2, max_size=3)
on_env = on_env[:T] if len(on_env) >= T else np.pad(on_env, (0, T - len(on_env)))
# low-frequency onset envelope using mel bands < 200 Hz
mel = librosa.feature.melspectrogram(S=P, sr=sr, n_mels=128, fmin=20, fmax=16000)
mel_f = librosa.mel_frequencies(n_mels=128 + 2, fmin=20, fmax=16000)[1:-1]
mel_db = librosa.power_to_db(mel, ref=1.0)
on_low = librosa.onset.onset_strength(S=mel_db[mel_f < 200], sr=sr, hop_length=H, lag=2, max_size=1)

# band energies (dB) on fine grid
bands = {'sub_20_60': (20, 60), 'bass_60_250': (60, 250), 'lowmid_250_500': (250, 500), 'mid_500_2k': (500, 2000),
         'pres_2k_6k': (2000, 6000), 'air_6k_16k': (6000, 16000)}
bandE = {k: 10 * np.log10(P[(freqs >= lo) & (freqs < hi)].sum(0) / (NFFT ** 2 / 4) + 1e-12) for k, (lo, hi) in bands.items()}
centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
flat = librosa.feature.spectral_flatness(S=S)[0]

# HPSS for percussive ratio
Hh, Pp = librosa.decompose.hpss(S, margin=1.0)
perc_ratio = (Pp ** 2).sum(0) / ((Hh ** 2).sum(0) + (Pp ** 2).sum(0) + 1e-12)

# ---------- narration mask from words.json ----------
words = json.load(open(W))['words']
vmask = np.zeros(T, bool)
for w in words:
    vmask[(tf >= w['start']) & (tf < w['end'])] = True

# ---------- REPET-SIM style background (music bed) estimate ----------
H2 = 1024
S2 = np.abs(librosa.stft(m, n_fft=4096, hop_length=H2))
S2f = np.minimum(S2, librosa.decompose.nn_filter(S2, aggregate=np.median, metric='cosine',
                                                  width=int(librosa.time_to_frames(2, sr=sr, hop_length=H2))))
mask_bg = librosa.util.softmask(S2f, 2 * (S2 - S2f), power=2)
mask_fg = librosa.util.softmask(S2 - S2f, 10 * S2f, power=2)
bg = mask_bg * S2
fg = mask_fg * S2
t2 = np.arange(S2.shape[1]) * H2 / sr
bg_db = 10 * np.log10((bg ** 2).sum(0) / (4096 ** 2 / 4) + 1e-12)
fg_db = 10 * np.log10((fg ** 2).sum(0) / (4096 ** 2 / 4) + 1e-12)
# music-bed onset envelope from background estimate
bg_on = librosa.onset.onset_strength(S=librosa.amplitude_to_db(bg), sr=sr, hop_length=H2, lag=2, max_size=3)

# ---------- pitch of narrator (pyin on 16k foreground-ish mono) ----------
m16 = librosa.resample(m, orig_sr=sr, target_sr=16000)
f0, vflag, vprob = librosa.pyin(m16, fmin=60, fmax=400, sr=16000, frame_length=1024, hop_length=160)
tp = np.arange(len(f0)) * 160 / 16000

# ---------- chroma (for SSM / key) ----------

chroma = librosa.feature.chroma_cqt(y=m, sr=sr, hop_length=2048)
tc = np.arange(chroma.shape[1]) * 2048 / sr
mfcc = librosa.feature.mfcc(S=mel_db, n_mfcc=20)

# ---------- aggregate fine -> video frames ----------
def to_frames(v, t, how='max'):
    idx = np.clip((t * FPS).astype(int), 0, NF - 1)
    out = np.full(NF, np.nan)
    if how == 'max':
        out2 = np.full(NF, -np.inf); np.maximum.at(out2, idx, v); out = out2
    else:
        s = np.zeros(NF); c = np.zeros(NF); np.add.at(s, idx, v); np.add.at(c, idx, 1); out = s / np.maximum(c, 1)
    # fill empties by interpolation
    bad = ~np.isfinite(out)
    if bad.any():
        out[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], out[~bad])
    return out

perframe = dict(
    rms_db=rms_db, peak_db=peak_db, lufs_momentary=lufs_m,
    onset_strength=to_frames(on_env, tf), spectral_flux=to_frames(flux, tf),
    onset_low200=to_frames(on_low[:T], tf[:len(on_low[:T])]), flux_low200=to_frames(flux_low, tf), flux_sub80=to_frames(flux_sub, tf),
    centroid_hz=to_frames(centroid, tf, 'mean'), flatness=to_frames(flat, tf, 'mean'), perc_ratio=to_frames(perc_ratio, tf, 'mean'),
    narration=to_frames(vmask.astype(float), tf, 'max'),
    music_bed_db=to_frames(bg_db, t2, 'mean'), voice_fg_db=to_frames(fg_db, t2, 'mean'), music_bed_onset=to_frames(bg_on[:len(t2)], t2),
    voiced_prob=to_frames(np.nan_to_num(vprob), tp, 'max'),
)
for k, v in bandE.items():
    perframe['band_' + k] = to_frames(v, tf, 'mean')

np.savez_compressed(f'{O}/feat.npz', N=N, sr=sr, NF=NF, pad=pad, integrated=integrated,
                    tf=tf, on_env=on_env, on_low=on_low[:T], flux=flux, flux_low=flux_low, flux_sub=flux_sub, vmask=vmask,
                    centroid=centroid, perc_ratio=perc_ratio, t2=t2, bg_db=bg_db, fg_db=fg_db, bg_on=bg_on[:len(t2)],
                    f0=f0, vprob=vprob, tp=tp, chroma=chroma, tc=tc, mfcc=mfcc, mel_db=mel_db.astype(np.float32),
                    bg_mel=librosa.power_to_db(librosa.feature.melspectrogram(S=bg ** 2, sr=sr, n_mels=128, fmin=20, fmax=16000)).astype(np.float32),
                    **{'pf_' + k: v for k, v in perframe.items()},
                    **{'fb_' + k: v for k, v in bandE.items()})
print('done', time.time() - t0, 's; N', N, 'NF', NF, 'pad', pad, 'integrated LUFS', integrated)
