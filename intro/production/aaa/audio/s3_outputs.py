"""Stage 3: audio_timeline.json, audio_report.md, audio_overview.png from analysis.pkl."""
import json, pickle, hashlib, numpy as np, librosa, soundfile as sf
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
A = pickle.load(open(f'{O}/analysis.pkl', 'rb'))
FPS = 30; NF = A['NF']; DUR = A['DUR']; N = A['N']
fr = lambda t: int(np.floor(t * FPS + 1e-9))
r3 = lambda v: round(float(v), 3)
col = lambda n: A['arr'][:, A['cols'].index(n)]
P = {p['id']: p for p in A['phrases']}
W = A['words']
def wt(word, after=0.0):
    word = word.strip(',.?').lower()
    return next(w for w in W if w['w'].strip(',.?').lower() == word and w['start'] >= after)

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating,)): return round(float(o), 6)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, float): return round(o, 6)
    return o

# ------------------------------------------------------------------ events
ev = []
def add(t, typ, strength, desc, **kw):
    d = dict(frame=fr(t), time=r3(t), type=typ, strength=round(float(strength), 3), description=desc); d.update(kw); ev.append(d)

add(0.0, 'audio_start', 1.0, 'File start. Frames 0-3 are near-digital silence (-73..-90 dBFS); sound begins at frame 4 (0.133 s).')
add(4 / 30 + 1e-6, 'music_start', 0.9, 'Music bed (D drone + pad) fades in under the first word; drone within 6 dB of full level by %.2f s.' % A['music_start']['drone_within_6dB_of_full'])
for b in A['beats']:
    add(b['start'], 'story_beat_start', 1.0, f"{b['id']} start: {b['desc']}", beat=b['id'])
    if b['id'] != 'B7':
        add(b['end'], 'story_beat_end', 0.8, f"{b['id']} end (last word ends)", beat=b['id'])
for p in A['phrases']:
    first = any(b['start'] == p['start'] for b in A['beats'])
    add(p['start'], 'narration_phrase_start', 1.0 if first else 0.7, f"{p['id']} \"{p['text']}\"", phrase=p['id'])
    add(p['end'], 'narration_phrase_end', 0.5, f"{p['id']} ends", phrase=p['id'])
    add(p['stressed_word_time'], 'stressed_word', 0.5, f"{p['id']} most emphasised word (loudness+length+content heuristic): {p['stressed_word']}", phrase=p['id'])
for g in A['gaps']:
    add(g['start'], 'music_only_gap', min(1, g['dur'] / 1.5), f"Music-only gap {g['dur']:.2f} s (to {g['end']:.3f} s / frame {g['f_end']}); music {g['music_db']} dBFS; harmony ~{g['chord_est']} ({'/'.join(g['top_pitch_classes'])})",
        end=g['end'], end_frame=g['f_end'])
for a in A['accents']:
    add(a['time'], 'accent', a['strength'], f"Top-30 accent ({a['kind']}, {a['source']}{', word: ' + a['word'] if a['word'] else ''})")
pl = A['pulse']
for i, t in enumerate(pl['events']):
    add(t, 'bass_pulse', 0.8, f"Bass re-articulation #{i + 1} of the slow ~{pl['period_s']:.3f} s bar pulse (side-channel 22-120 Hz)")
for b in A['bass']:
    if b['time'] < 42 and b['time'] > 1 and b['strength'] >= 0.35:
        add(b['time'], 'bass_swell', b['strength'], f"Drone/bass re-swell +{b['rise_db']} dB (side-channel 22-120 Hz){' on ' + b['word'] if b['word'] else ' (music-only gap)'}")
for s in A['sections']:
    add(s['start'], 'section_boundary', 1.0 if s['id'] in ('M3', 'M5', 'M7') else 0.8, f"{s['id']} {s['label']}: {s['music']}", section=s['id'], end=s['end'], end_frame=s['f_end'])
for n in A['novelty_peaks']:
    add(n['time'], 'novelty_peak', n['strength'], 'Algorithmic section-novelty peak (Foote kernel on side-channel chroma + band energies + music level)')
for h in A['harm_changes'][:10]:
    add(h['time'], 'harmony_change', h['strength'], 'Chroma change of the music (side channel, 1 s windows)')
for s in A['silences']:
    if s['dur'] >= 0.25:
        add(s['start'], 'near_silence', min(1, s['dur'] / 1.5), f"Mix below -40 dBFS for {s['dur']:.2f} s (mean {s['mean_db']} dBFS, to frame {s['f_end']})", end=s['end'], end_frame=s['f_end'])
for c in A['cres']:
    add(c['start'], 'crescendo_start', min(1, c['rise_db'] / 10), f"Music crescendo +{c['rise_db']} dB over {c['dur']} s (peak at {c['peak']:.2f} s, {c['peak_music_db']} dBFS)")
    add(c['peak'], 'crescendo_peak', min(1, c['rise_db'] / 10), f"Crescendo peak ({c['peak_music_db']} dBFS music level)")
for s in A['swells']:
    add(s['start'], 'music_swell', min(1, s['rise_db'] / 10), f"Music swell +{s['rise_db']} dB inside the gap, leading into {s['into_phrase']}")
m = A['macro']
add(m['start'], 'macro_crescendo_start', 1.0, f"Long-range build begins: music-only level {m['valley_level_db']} dBFS here -> {m['peak_gap_level_db']} dBFS at the climax (+{m['rise_db']} dB over ~{m['peak_music_1s_time'] - m['start']:.0f} s)")
add(m['peak_gap'][0], 'music_climax', 1.0, f"Music climax gap {m['peak_gap'][0]}-{m['peak_gap'][1]} s: loudest music of the piece ({m['peak_gap_level_db']} dBFS), Bbmaj7 colour; 1 s peak at {m['peak_music_1s_time']} s")
d = A['drone']
add(d['fade_begin'], 'drone_fade_start', 0.8, f"D drone (music floor) starts to fade (-6 dB) under \"Then the king died / and left no heir\"")
add(d['minus15db'], 'drone_exit', 1.0, 'D drone down 15 dB (effectively gone at -25 dB by %.2f s): the bottom of the score drops out on "no heir"' % d['minus25db'])
f = A['fade']
add(f['music_fade_start'], 'music_fade_start', 1.0, f"Music starts its final recession as the last question begins (-{f['music_fade_depth_db']} dB by {f['music_fade_end']} s)")
add(f['bass_gone_time'], 'bass_gone', 0.7, 'Bass fully gone (-20 dB) under "say of you?"')
add(f['music_fade_end'], 'music_fade_end', 0.9, f"Music reaches its tail level (~{f['tail_music_db']} dBFS): soft high unresolved chord only")
add(f['narration_end'], 'narration_end', 1.0, 'Last word ends ("you?"). Only the ring-out chord remains (decays ~1 dB/s).')
add(f['micro_fade_start'], 'micro_fade_start', 0.6, 'Final ~30 ms micro-fade begins (the music is still at ~-48 dBFS: the audio ends abruptly)')
add(DUR, 'audio_end', 1.0, f'Last decoded sample ({N} samples). Video ends at the end of frame {NF - 1} (66.1333 s) after {A["PAD"]} samples of padded silence.')
ev.sort(key=lambda e: (e['time'], e['type']))

# ------------------------------------------------------------------ 25 sync points
def sp(t, what, t_end=None):
    d = dict(time=r3(t), frame=fr(t), what=what)
    if t_end is not None: d.update(end_time=r3(t_end), end_frame=fr(t_end))
    return d
sync = [
    sp(0.0, 'Picture start. Audio frames 0-3 are silent; sound begins at frame 4. Fade up from black over frames 0-4 at most.'),
    sp(P['P01']['start'], 'Narration "There was a time..." and the D drone start together (strongest attack of the file at 0.17 s, frame 5).'),
    sp(wt('one')['start'], 'Litany 1/4 "one realm" ("realm" at %.2f s, frame %d).' % (wt('realm,')['start'], wt('realm,')['f_start'])),
    sp(P['P02']['start'], 'Litany 2/4 "one table" ("table" at %.2f s, frame %d), with a drone re-swell at 4.22 s.' % (wt('table,')['start'], wt('table,')['f_start'])),
    sp(P['P03']['start'], 'Litany 3/4 "one oath"; then a 0.47 s near-silence (6.17-6.63 s, -45 dBFS) and a +10 dB swell.'),
    sp(P['P04']['start'], 'Litany 4/4 "one crown." (attack on "crown" at 7.65 s, frame 229). End of the golden-age beat at 8.28 s.'),
    sp(P['P05']['start'], 'B2 oath: "They raised their cups" ("cups" attack 10.26 s, frame 307). Music crescendo 6.2 -> 9.0 s peaks here.'),
    sp(wt('swore')['start'], '"and swore it would never end." Strongest early drone swell at 11.94 s (frame 358); phrase ends 13.42 s, then a 1.46 s music-only gap (frames 402-446) for the panel change.', P['P06']['end']),
    sp(P['P07']['start'], 'B3 death: "Then the king died" ("died" at 15.64 s, frame 469).'),
    sp(d['fade_begin'], 'The D drone (the floor of the score) fades out under "and left no heir": -15 dB at %.2f s (frame %d), gone by %.2f s.' % (d['minus15db'], d['minus15db_frame'], d['minus25db']), d['minus25db']),
    sp(P['P09']['start'], '"and every lord..." Lament chords (Dm9/F colour), music about 5 dB louder than in B1 (about -28 dBFS). "empty chair" at 21.88-22.72 s (frames 656-681).'),
    sp(P['P10']['start'], '"and saw his own head beneath the crown." ("crown" at 26.18 s, frame 785).'),
    sp(26.6, 'The music collapses by about 20 dB into near-silence (frames 797-844, -47 dBFS for 1.6 s). This is the strongest internal boundary. Hold, stillness or a cut to black.', 28.16),
    sp(P['P11']['start'], 'B4 war: "The wars lasted a hundred years and ended nothing." The music stays at or below about -45 dBFS (nearly silent) until about 33.9 s, with a second silent gap at 31.73-32.67 s.'),
    sp(P['P12']['start'], '"Cities fell to ruin." (attack 32.92 s, frame 987; "fell" 33.32 s, frame 999)'),
    sp(33.9, 'A soft pad returns (about +7 dB, 33.4 -> 35.4 s) into "Roads were swallowed by the forest." (35.04 s, frame 1051).'),
    sp(P['P14']['start'], '"Men forgot what lay beyond their own borders," (attack 37.98 s, frame 1139). The music sits on a -40 dBFS plateau.'),
    sp(pl['events'][0], 'Biggest musical event: the bass and low register enter on "grew" ("the world grew dark", phrase starts 41.80 s), +26 dB in 22-120 Hz. "dark" lands at 43.08 s (frame 1292).'),
    sp(pl['events'][1], 'A bass swell in the 1.54 s music-only gap (frames 1336-1382). Bar pulse #2 of 8 (period about 2.115 s).'),
    sp(P['P16']['start'], 'B5 present: "Now every ruler believes the world can be made whole again." Bass pulses at 47.00 s (frame 1410) and 49.06 s (frame 1471).'),
    sp(P['P17']['start'], 'Litany 2: "One banner," / "one village," (51.98 s, frame 1559) / "one blank page." (53.30 s, frame 1599). Bass pulses land on "banner" (51.21 s) and "one [blank page]" (53.30 s). Bb major in the gap just before (49.72-50.80 s).'),
    sp(P['P20']['start'], 'B6: "When this age is remembered," Bass pulse #8 at 57.55 s (frame 1726) on "remembered".'),
    sp(m['peak_gap'][0], 'Music climax: the loudest music of the piece (-25.6 dBFS) in a 1.32 s music-only gap, peaking at %.2f s (frame %d). Best spot for the big visual reveal.' % (m['peak_music_1s_time'], m['peak_music_1s_frame']), m['peak_gap'][1]),
    sp(P['P21']['start'], '"what will the chronicles say of you?" The music recedes about 19 dB from %.2f s to %.2f s and the bass is gone by %.2f s. "chronicles" at 60.06 s (frame 1801), "you?" at 61.56-61.84 s (frames 1846-1855).' % (f['music_fade_start'], f['music_fade_end'], f['bass_gone_time'])),
    sp(f['narration_end'], 'Narration ends. A 4.27 s ring-out of a soft high unresolved chord follows (-44 -> -48 dBFS, about -1 dB/s): title or logo hold. Micro-fade at 66.075 s (frame 1982); last sample 66.107 s; final video frame is 1983 (1984 frames in total).', DUR),
]
assert len(sync) == 25

# ------------------------------------------------------------------ JSON
md5 = hashlib.md5(open(f'{O}/audio_original.mp3', 'rb').read()).hexdigest()
duration = dict(decoded_samples=N, sample_rate=44100, channels=2, decoded_seconds=round(DUR, 6),
                mp3_container_duration_s=66.142041, mp3_container_duration_note='ffprobe value = 2532 MPEG frames x 1152 samples (66.142041 s) INCLUDING encoder delay + padding; not the playable length.',
                mp3_start_time_s=0.025057, mp3_start_time_note='= 1105 samples skipped by the decoder (576 LAME encoder delay + 529 decoder delay).',
                lame_tag=dict(encoder='Lavc59.37 (libmp3lame)', encoder_delay_samples=576, end_padding_samples=960, mpeg_frames=2532, bitrate_kbps=169),
                gapless_check='ffmpeg and libsndfile/mpg123 both decode exactly 2,915,328 samples = 2532*1152 - 1105 - 431.',
                words_json_alignment='Scribe word starts vs. audio onsets: median offset +0.015 s (energy rise -0.01 s); within half a frame, so no correction is needed.')
video = dict(fps=30, total_frames=NF, last_frame_index=NF - 1, video_duration_s=round(NF / FPS, 6), samples_per_frame=1470,
             rounding_policy='ceil: 66.107211 s x 30 = 1983.216 frames -> 1984 frames. Pad the decoded audio with %d samples (26.1 ms) of digital silence so that audio = 1984 x 1470 = 2,916,480 samples = 66.133333 s = video duration exactly. (The alternative, 1983 frames, would cut 318 samples (7.2 ms) of the micro-fade.)' % A['PAD'],
             audio_pad_samples=A['PAD'], master_audio_wav='audio_master_1984f_f32.wav (float32) / audio_master_1984f_s16.wav (PCM16), 44.1 kHz stereo, exactly 2,916,480 samples',
             frame_convention='frame = floor(time*30): the frame whose display interval [f/30,(f+1)/30) contains the event. To make a visual hit read as "on" the sound, put the change on this frame (or 1 frame earlier for hard cuts).',
             mux_advice='Mux from the padded WAV (e.g. -c:a aac -b:a 256k or libopus); never stream-copy the MP3 (its 66.142 s container duration and priming would desync the end).')
loud = dict(integrated_lufs=round(A['integrated'], 2), sample_peak_dbfs=round(A['sample_peak_db'], 2), true_peak_dbtp=round(A['true_peak_db'], 2),
            narration_peak_range_dbfs=[min(p['peak_db'] for p in A['phrases']), max(p['peak_db'] for p in A['phrases'])],
            normalisation_hint='Integrated loudness is -19.7 LUFS with 6.9 dB of true-peak headroom. +3.7 dB gives -16 LUFS (TP about -3.2 dBTP); +5.7 dB gives -14 LUFS (TP about -1.2 dBTP). Apply the gain only if the delivery spec asks for it.',
            stereo='Narration is mixed dead-centre (it does not raise the side channel); the music is very wide (side approximately equal to mid in every band). Side = (L-R)/2 is a near voice-free view of the music.',
            narrator_f0_hz=dict(median=A['nar_f0'][0], p10=A['nar_f0'][1], p90=A['nar_f0'][2]), words_per_second=round(A['words_per_s'], 2))
per_frame = dict(columns=A['cols'], npy='audio_frames.npy (float32, shape [%d, %d], rows = video frames, columns as listed)' % (NF, len(A['cols'])), csv='audio_frames.csv',
                 notes=dict(rms_db='mix RMS over the exact 1470-sample window of each frame, dBFS', lufs_momentary='BS.1770 K-weighted, 400 ms window centred on the frame',
                            onset_strength='librosa superflux-style onset envelope, max within the frame, normalised to 0..1 (1 = strongest peak)',
                            spectral_flux='positive log-magnitude flux, 0..1', music_level_db='music level estimate in dBFS-equivalent from the side channel (narration-leak corrected, calibrated to the mix in music-only gaps)',
                            narration='1 if any Scribe word span overlaps the frame'),
                 rms_db=[round(float(v), 1) for v in col('rms_db')], onset_strength=[round(float(v), 3) for v in col('onset_strength')],
                 music_level_db=[round(float(v), 1) for v in col('music_level_db')], narration=[int(v) for v in col('narration')])
music = dict(key=dict(estimate='D minor (natural/Aeolian; Bb and F major-7 colours, C#/D drone beating)', krumhansl_top3=A['keys']),
             instrumentation_note='No neural stem separation was possible (model hosts are blocked). Timbre conclusions come from the side channel, pitch-stability (vibrato) measurements, HPSS and band balance, so they are heuristics.',
             percussion='None detected. HPSS percussive ratio in music-only gaps is 0.01-0.16 (narration frames 0.25). Every strong <200 Hz transient in the mix falls inside narration words (narrator F0 is 73-134 Hz).',
             tempo=dict(verdict='Unmetered, rubato ambient score with no steady beat. Autocorrelation peaks at 0.35/0.46/0.71 s follow the narration rhythm (2.85 words/s). The only robust periodicity is the slow bass bar pulse in 42.8-57.6 s.',
                        stats=A['tempo'], bar_pulse=pl),
             sections=A['sections'], music_only_gaps=A['gaps'], drone=A['drone'], music_start=A['music_start'], crescendos=A['cres'], gap_swells=A['swells'],
             macro_crescendo=m, near_silences=A['silences'], fade=f, bass_entries=A['bass'], harmony_changes=A['harm_changes'], novelty_peaks=A['novelty_peaks'],
             chords_per_half_second=A['chords'])
narration = dict(phrases=A['phrases'], story_beats=A['beats'],
                 words=[dict(w=w['w'], start=w['start'], end=w['end'], f_start=w['f_start'], f_end=w['f_end'], peak_db=w['peak_db'], f0_hz=w['f0_hz']) for w in W])
out = dict(source=dict(audio=f'{O}/audio_original.mp3', md5=md5, words='../words.json (ElevenLabs Scribe v1)', analysis_scripts=['s1_features.py', 's1b_side.py', 'dbg/musiccqt.py', 's2_analyze.py', 's3_outputs.py']),
           duration=duration, fps=30, total_frames=NF, video=video, loudness=loud, per_frame=per_frame, narration=narration, music=music,
           onsets_full_mix_top60=A['onsets'][:60], accents_top30=A['accents'], sync_points_top25=sync, events=ev)
json.dump(clean(out), open(f'{O}/audio_timeline.json', 'w'), indent=1)
print('events', len(ev))

# ------------------------------------------------------------------ figure
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8984'
S1, S2, S3 = '#2a78d6', '#eb6834', '#1baf7a'
x, sr = sf.read(f'{O}/audio_f32.wav', dtype='float32'); mid = x.mean(1); side = (x[:, 0] - x[:, 1]) / 2
H = 441
def melimg(sig):
    M = librosa.feature.melspectrogram(y=sig, sr=sr, n_fft=2048, hop_length=H, n_mels=160, fmin=25, fmax=16000)
    return librosa.power_to_db(M, ref=np.max(M))
Mm, Ms = melimg(mid), melimg(side)
T = Mm.shape[1] * H / sr
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2})
fig = plt.figure(figsize=(44, 25), facecolor='#fcfcfb')
gs = fig.add_gridspec(6, 1, height_ratios=[1.1, 1.3, 2.2, 2.2, 1.9, 1.6], hspace=0.08, left=0.035, right=0.995, top=0.955, bottom=0.065)
ax = [fig.add_subplot(gs[i]) for i in range(6)]
for a_ in ax[1:]: a_.sharex(ax[0])
fig.suptitle('CHRONICA intro: audio timeline (66.107 s decoded, 1984 frames at 30 fps).  Top axis: video frame; bottom axis: seconds.', x=0.035, ha='left', fontsize=20, color=INK)
# row 0: sections + story beats
a0 = ax[0]; a0.set_ylim(0, 2); a0.set_yticks([]); a0.set_facecolor('#fcfcfb')
for i, s in enumerate(A['sections']):
    a0.add_patch(Rectangle((s['start'], 1.05), s['end'] - s['start'], 0.9, color=['#e7e6e1', '#d6d5cf'][i % 2], lw=0))
    if s['end'] - s['start'] > 0.5:
        lab = f"{s['id']} {s['label']}"; mx = int((s['end'] - s['start']) / 0.15)
        a0.text(s['start'] + 0.08, 1.5, lab if len(lab) <= mx else lab[:max(2, mx - 3)] + '...', va='center', fontsize=11, color=INK, clip_on=True)
for i, b in enumerate(A['beats']):
    a0.add_patch(Rectangle((b['start'], 0.1), b['end'] - b['start'], 0.8, color=['#cde2fb', '#9ec5f4'][i % 2], lw=0))
    lab = f"{b['id']}  " + b['desc']; mx = int((b['end'] - b['start']) / 0.145)
    a0.text(b['start'] + 0.08, 0.5, lab if len(lab) <= mx else lab[:max(2, mx - 3)] + '...', va='center', fontsize=10.5, color=INK, clip_on=True)
a0.set_ylabel('music sections\nstory beats', fontsize=11)
secax = a0.secondary_xaxis('top', functions=(lambda t: t * 30, lambda f_: f_ / 30)); secax.set_xticks(np.arange(0, 2000, 60)); secax.set_xlabel('video frame (30 fps)', color=INK2)
# row 1: waveform envelope
a1 = ax[1]
fm = np.concatenate([mid, np.zeros(A['PAD'], np.float32)]).reshape(NF, 1470)
tt = (np.arange(NF) + 0.5) / FPS
a1.fill_between(tt, fm.min(1), fm.max(1), color='#9a9993', lw=0, label='mix waveform (per-frame min/max)')
fs_ = np.concatenate([side, np.zeros(A['PAD'], np.float32)]).reshape(NF, 1470)
a1.fill_between(tt, fs_.min(1), fs_.max(1), color=S2, lw=0, alpha=0.9, label='side channel (L-R)/2 = music without narration')
a1.set_ylim(-0.5, 0.5); a1.set_ylabel('amplitude'); a1.legend(loc='lower right', fontsize=10, frameon=True, framealpha=0.85, edgecolor='none', ncol=2)
for p in A['phrases']:
    a1.axvspan(p['start'], p['end'], ymin=0.93, ymax=1.0, color=S1, lw=0)
# row 2: mix mel spectrogram with phrase labels
a2 = ax[2]
a2.imshow(Mm, origin='lower', aspect='auto', extent=[0, T, 0, 160], vmin=-80, vmax=0, cmap='magma', interpolation='nearest')
mf = librosa.mel_frequencies(n_mels=162, fmin=25, fmax=16000)[1:-1]
yt = [50, 100, 200, 500, 1000, 2000, 5000, 10000]; a2.set_yticks([np.argmin(np.abs(mf - v)) for v in yt]); a2.set_yticklabels([f'{v // 1000}k' if v >= 1000 else str(v) for v in yt])
a2.set_ylabel('mix (mel, Hz)')
for i, p in enumerate(A['phrases']):
    a2.axvline(p['start'], color='#ffffff', lw=0.8, alpha=0.6)
    txt = p['text'] if len(p['text']) < 34 else p['text'][:31] + '...'
    a2.text(p['start'] + 0.05, 152 - (i % 3) * 9, f"{p['id']} {txt}", color='#ffffff', fontsize=10.5, va='top', clip_on=True,
            bbox=dict(boxstyle='square,pad=0.15', fc='#000000', ec='none', alpha=0.55))
# row 3: side mel spectrogram (music only)
a3 = ax[3]
a3.imshow(Ms, origin='lower', aspect='auto', extent=[0, T, 0, 160], vmin=-80, vmax=0, cmap='magma', interpolation='nearest')
a3.set_yticks([np.argmin(np.abs(mf - v)) for v in yt]); a3.set_yticklabels([f'{v // 1000}k' if v >= 1000 else str(v) for v in yt])
a3.set_ylabel('music view: side channel\n(mel, Hz)')
for g in A['gaps']:
    a3.axvspan(g['start'], g['end'], ymin=0, ymax=0.035, color='#ffffff', lw=0)
    if g['dur'] >= 0.7:
        a3.text((g['start'] + g['end']) / 2, 8, g['chord_est'], color='#ffffff', fontsize=9.5, ha='center', clip_on=True)
a3.text(0.2, 150, 'white bars along the bottom = music-only gaps, labelled with the estimated chord', color='#ffffff', fontsize=10, va='top')
# row 4: levels
a4 = ax[4]
a4.plot(tt, col('rms_db'), color='#b9b8b2', lw=1.0, label='mix RMS per frame (dBFS)')
a4.plot(tt, col('lufs_momentary'), color=S3, lw=2, label='mix momentary loudness (LUFS, 400 ms)')
a4.plot(tt, col('music_level_db_1s'), color=S2, lw=2.4, label='music level estimate (side channel, 1 s, dBFS)')
for s in A['silences']:
    if s['dur'] >= 0.25: a4.axvspan(s['start'], s['end'], color='#383835', alpha=0.12, lw=0)
for c in A['cres']:
    a4.annotate('', xy=(c['peak'], c['peak_music_db'] + 1), xytext=(c['start'], c['peak_music_db'] - c['rise_db'] + 1), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.4))
mm_ = A['macro']
a4.annotate(f"music climax {mm_['peak_gap_level_db']} dBFS", xy=(mm_['peak_music_1s_time'], mm_['peak_music_1s_db']), xytext=(mm_['peak_music_1s_time'] - 9, -12),
            arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2), fontsize=11, color=INK)
a4.annotate('music collapses (-20 dB)', xy=(26.6, -46), xytext=(19.5, -60), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2), fontsize=11, color=INK)
a4.annotate('D drone (low end) exits', xy=(A['drone']['minus15db'], -33), xytext=(12.5, -58), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2), fontsize=11, color=INK)
a4.annotate('bass enters ("grew dark")', xy=(42.78, -31), xytext=(34.5, -14), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2), fontsize=11, color=INK)
a4.annotate('music recedes under the question', xy=(60.4, -38), xytext=(51.5, -62), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2), fontsize=11, color=INK)
a4.set_ylim(-70, -5); a4.set_ylabel('level (dB)'); a4.grid(axis='y', color='#e7e6e1', lw=0.8); a4.legend(loc='lower left', fontsize=10.5, frameon=False, ncol=3)
a4.text(0.3, -8, 'shaded = mix below -40 dBFS; black arrows = detected crescendos', fontsize=10, color=INK2)
# row 5: onset + accents
a5 = ax[5]
a5.plot(tt, col('onset_strength'), color='#b9b8b2', lw=1.0, label='mix onset strength (0..1)')
a5.plot(tt, col('music_onset_side'), color=S2, lw=1.0, alpha=0.8, label='music onset strength, side channel (0..1)')
for a in A['accents']:
    mk = 'v' if a['kind'] == 'bass_entry' else 'o'
    a5.plot(a['time'], 1.16, mk, ms=9, color=S1 if a['kind'] == 'onset' else S2, mec='#fcfcfb', mew=1.5, clip_on=False)
for i, a in enumerate(sorted(A['accents'], key=lambda a: a['time'])):
    a5.text(a['time'], 1.25 + (i % 2) * 0.1, f"{a['frame']}", fontsize=8.5, ha='center', color=INK2, clip_on=False)
for t in pl['events']:
    a5.axvline(t, color=S2, lw=1.2, ls='--', alpha=0.8)
a5.text(pl['events'][0] + 0.1, 0.9, f"dashed = bass bar pulse, about {pl['period_s']:.3f} s apart", fontsize=10, color=INK)
a5.plot([], [], 'o', color=S1, ms=9, label='top-30 accent: narration attack + music')
a5.plot([], [], 'v', color=S2, ms=9, label='top-30 accent: music bass entry (frame number above)')
a5.set_ylim(0, 1.42); a5.set_ylabel('onsets'); a5.legend(loc='upper center', fontsize=11, frameon=False, ncol=4, bbox_to_anchor=(0.5, -0.28))
a5.set_xlabel('time (s)')
for a_ in ax:
    a_.set_xlim(0, NF / FPS)
    a_.set_xticks(np.arange(0, 67, 1)); a_.tick_params(axis='x', labelsize=10)
    for s in A['sections'][1:]:
        a_.axvline(s['start'], color=INK, lw=1.4, alpha=0.55)
for a_ in ax[:-1]: plt.setp(a_.get_xticklabels(), visible=False)
fig.savefig(f'{O}/audio_overview.png', dpi=72, facecolor='#fcfcfb')
print('png saved')
