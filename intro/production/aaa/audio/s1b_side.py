"""Stage 1b: music-only analysis on the SIDE channel (L-R)/2.
The narration is mixed dead-centre (side level does not rise during words: median +0.0 dB vs +5.6 dB on mid),
so the side channel is a voice-free view of the (very wide) music bed."""
import json, numpy as np, soundfile as sf, librosa, scipy.ndimage as ndi
O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
x, sr = sf.read(f'{O}/audio_f32.wav', dtype='float32')
N = len(x); SPF = 1470; NF = int(np.ceil(N / SPF)); pad = NF * SPF - N
side = (x[:, 0] - x[:, 1]) / 2
sidep = np.concatenate([side, np.zeros(pad, np.float32)])
mid = (x[:, 0] + x[:, 1]) / 2
side_rms_db = 20 * np.log10(np.sqrt((sidep.reshape(NF, SPF) ** 2).mean(1)) + 1e-10)
H = 441; NFFT = 2048
S = np.abs(librosa.stft(side, n_fft=NFFT, hop_length=H))
T = S.shape[1]; tf = np.arange(T) * H / sr
freqs = librosa.fft_frequencies(sr=sr, n_fft=NFFT)
mel = librosa.feature.melspectrogram(S=S ** 2, sr=sr, n_mels=128, fmin=20, fmax=16000)
mel_db = librosa.power_to_db(mel)
mel_f = librosa.mel_frequencies(n_mels=130, fmin=20, fmax=16000)[1:-1]
on = librosa.onset.onset_strength(S=mel_db, sr=sr, hop_length=H, lag=2, max_size=3)
on_low = librosa.onset.onset_strength(S=mel_db[mel_f < 200], sr=sr, hop_length=H, lag=2, max_size=1)
on_hi = librosa.onset.onset_strength(S=mel_db[mel_f >= 2000], sr=sr, hop_length=H, lag=2, max_size=3)
logS = np.log1p(100 * S)
flux = np.maximum(0, np.diff(logS, axis=1, prepend=logS[:, :1])).sum(0)
bands = {'sub_20_60': (20, 60), 'bass_60_250': (60, 250), 'lowmid_250_500': (250, 500), 'mid_500_2k': (500, 2000),
         'pres_2k_6k': (2000, 6000), 'air_6k_16k': (6000, 16000)}
bandE = {k: 10 * np.log10((S[(freqs >= lo) & (freqs < hi)] ** 2).sum(0) / (NFFT ** 2 / 4) + 1e-12) for k, (lo, hi) in bands.items()}
Hh, Pp = librosa.decompose.hpss(S, margin=1.0)
perc = (Pp ** 2).sum(0) / ((Hh ** 2).sum(0) + (Pp ** 2).sum(0) + 1e-12)
centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
# harmonic content (CQT 36 bpo, C1..C9) of the side channel
hopc = 512
C = np.abs(librosa.cqt(side, sr=sr, hop_length=hopc, fmin=librosa.note_to_hz('C1'), n_bins=288, bins_per_octave=36))
tc = np.arange(C.shape[1]) * hopc / sr
Cs = ndi.median_filter(C, size=(1, 17))  # 0.2 s smoothing of sustained tones
chroma = np.zeros((12, C.shape[1]))
for k in range(288):
    chroma[(int(round(k / 3))) % 12] += Cs[k]
def to_frames(v, t, how='max'):
    idx = np.clip((t * 30).astype(int), 0, NF - 1)
    if how == 'max':
        out = np.full(NF, -np.inf); np.maximum.at(out, idx, v)
    else:
        s = np.zeros(NF); c = np.zeros(NF); np.add.at(s, idx, v); np.add.at(c, idx, 1); out = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    bad = ~np.isfinite(out)
    if bad.any(): out[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], out[~bad])
    return out
pf = dict(side_rms_db=side_rms_db, side_onset=to_frames(on, tf), side_onset_low=to_frames(on_low, tf), side_onset_hi=to_frames(on_hi, tf),
          side_flux=to_frames(flux, tf), side_perc=to_frames(perc, tf, 'mean'), side_centroid=to_frames(centroid, tf, 'mean'),
          **{'side_band_' + k: to_frames(v, tf, 'mean') for k, v in bandE.items()})
cf = np.stack([to_frames(chroma[i], tc, 'mean') for i in range(12)])
np.savez_compressed(f'{O}/feat_side.npz', tf=tf, on=on, on_low=on_low, on_hi=on_hi, flux=flux, tc=tc,
                    Cdb=librosa.amplitude_to_db(Cs, ref=Cs.max()).astype(np.float32), mel_db=mel_db.astype(np.float32), cf=cf,
                    **{'pf_' + k: v for k, v in pf.items()})
words = json.load(open(f'{O}/../words.json'))['words']
inw = np.zeros(NF, bool)
for w in words: inw[int(w['start'] * 30):int(w['end'] * 30) + 1] = True
print('side band levels: in-words vs not (mean dB):')
for k in bands:
    v = pf['side_band_' + k]; print(f'  {k:16s} words {v[inw].mean():6.1f}  gaps {v[~inw][5:-5].mean():6.1f}')
mid_bands = {k: 10 * np.log10((np.abs(librosa.stft(mid, n_fft=NFFT, hop_length=H))[(freqs >= lo) & (freqs < hi)] ** 2).sum(0) / (NFFT ** 2 / 4) + 1e-12) for k, (lo, hi) in bands.items()}
print('mid vs side band levels in music-only gaps (dB): side-mid')
gm = np.zeros(T, bool)
ws = [(w['start'], w['end']) for w in words]
for a, b in [(ws[i][1], ws[i + 1][0]) for i in range(len(ws) - 1)] + [(ws[-1][1], N / sr)]:
    if b - a > 0.5: gm[(tf > a + 0.08) & (tf < b - 0.05)] = True
for k in bands:
    print(f'  {k:16s} side {bandE[k][gm].mean():6.1f} mid {mid_bands[k][gm].mean():6.1f}  diff {bandE[k][gm].mean() - mid_bands[k][gm].mean():5.1f}')
