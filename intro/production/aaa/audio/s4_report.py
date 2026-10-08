"""Stage 4: human-readable audio_report.md from audio_timeline.json."""
import json
O = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio'
J = json.load(open(f'{O}/audio_timeline.json'))
d, v, L, M, Nn = J['duration'], J['video'], J['loudness'], J['music'], J['narration']
fr = lambda t: int(t * 30 + 1e-9)
o = []
w = o.append
w('# CHRONICA intro: frame-accurate audio analysis\n')
w(f"Source: `{J['source']['audio']}` (md5 `{J['source']['md5']}`), with narration timings from `words.json` (ElevenLabs Scribe v1). "
  "Machine-readable version: `audio_timeline.json`. Per-frame data: `audio_frames.npy` / `audio_frames.csv`. Picture: `audio_overview.png`.\n")
w('## 1. Duration and frame count (authoritative)\n')
w('| quantity | value |\n|---|---|')
w(f"| Decoded PCM length | **{d['decoded_samples']:,} samples @ 44.1 kHz = {d['decoded_seconds']:.6f} s** (stereo) |")
w(f"| ffprobe container duration | {d['mp3_container_duration_s']} s = 2532 MPEG frames x 1152. This includes encoder delay and padding, so it is **not** the playable length |")
w(f"| ffprobe start_time | {d['mp3_start_time_s']} s = 1105 samples skipped by the decoder (576 LAME encoder delay + 529 decoder delay) |")
w('| LAME tag | encoder Lavc59.37 (libmp3lame), delay 576, end padding 960, about 169 kbps |')
w('| Gapless check | ffmpeg and libsndfile/mpg123 both decode exactly 2,915,328 samples = 2532 x 1152 - 1105 - 431 |')
w(f"| Seconds x 30 fps | 1983.216 frames |")
w(f"| **Video length** | **{v['total_frames']} frames (0..{v['last_frame_index']}) = {v['video_duration_s']:.6f} s** |")
w(f"| Audio pad | {v['audio_pad_samples']} samples (26.1 ms) of digital silence appended, giving 2,916,480 samples = 1984 x 1470 |")
w(f"| Ready-made master | `audio_master_1984f_f32.wav` (float32) and `audio_master_1984f_s16.wav` (PCM16), exactly 66.133333 s |")
w(f"| words.json alignment | {d['words_json_alignment']} |\n")
w(f"**Rounding policy.** Round up to 1984 frames and pad the audio with silence, so video duration equals audio duration exactly with no audio lost. "
  "Rounding down to 1983 frames would cut 318 samples (7.2 ms) of the final micro-fade. Mux from the padded WAV, never by stream-copying the MP3: "
  "its 66.142 s container duration and encoder priming would shift the end.\n")
w(f"**Frame convention used everywhere:** `frame = floor(t x 30)`, the frame on screen when the sound happens. For hard cuts on an attack, cutting 1 frame early (frame - 1) usually reads as on-beat.\n")
w('## 2. Loudness, stereo, voice\n')
w(f"- Integrated loudness {L['integrated_lufs']} LUFS, sample peak {L['sample_peak_dbfs']} dBFS, true peak {L['true_peak_dbtp']} dBTP. {L['normalisation_hint']}")
w(f"- Narration phrase peaks sit in a tight {L['narration_peak_range_dbfs'][0]} to {L['narration_peak_range_dbfs'][1]} dBFS band. The narrator is a deep male voice: F0 median {L['narrator_f0_hz']['median']} Hz (p10 {L['narrator_f0_hz']['p10']}, p90 {L['narrator_f0_hz']['p90']}). Pace is {L['words_per_second']} words/s while speaking.")
w(f"- {L['stereo']} This side channel drives the music-only measurements below (music level, bass entries, harmony). Residual narration leak into the side is at or below -27 dB relative to the voice.\n")
w('## 3. Narration structure\n')
w('Story beats (sentences grouped by meaning):\n')
w('| beat | time (s) | frames | content |\n|---|---|---|---|')
for b in Nn['story_beats']:
    w(f"| {b['id']} | {b['start']:.2f}-{b['end']:.2f} | {b['f_start']}-{b['f_end']} | {b['desc']} |")
w('\nPhrases (split at pauses of 0.45 s or more, or at punctuation). The stressed word comes from a loudness + length + content-word heuristic:\n')
w('| id | start s | end s | frames | text | stressed word (frame) | peak dBFS |\n|---|---|---|---|---|---|---|')
for p in Nn['phrases']:
    w(f"| {p['id']} | {p['start']:.2f} | {p['end']:.2f} | {p['f_start']}-{p['f_end']} | {p['text']} | {p['stressed_word']} ({p['stressed_word_frame']}) | {p['peak_db']} |")
w('\nMusic-only gaps longer than 0.5 s. These are the windows for cuts, panel changes and reveals. The music level comes from the voice-free side channel, calibrated to the mix; the chord estimate comes from side-channel chroma:\n')
w('| start s | end s | dur s | frames | music dBFS | est. harmony (top pitch classes) |\n|---|---|---|---|---|---|')
for g in M['music_only_gaps']:
    w(f"| {g['start']:.2f} | {g['end']:.2f} | {g['dur']:.2f} | {g['f_start']}-{g['f_end']} | {g['music_db']} | {g['chord_est']} ({', '.join(g['top_pitch_classes'])}) |")
w('\nHow to read the chord labels: in the M1 gaps (0-15 s) the C# comes mostly from the flat ~71 Hz drone partial, which sits between C#2 and D2. Read those gaps as a D5/Dadd9 drone with a slightly sour beating, not as Dmaj7. "F6" (F-A-D-E) is the same pitch set as Dm7(add9)/F. The 26.6 s and 31.8 s gaps are near-silent, so their labels are weak.\n')
w('\n## 4. What the music does\n')
w(f"**Character.** The score is an unmetered, rubato ambient/orchestral bed in **{M['key']['estimate']}** (Krumhansl fit {M['key']['krumhansl_top3'][0][0]} for {M['key']['krumhansl_top3'][0][1]}). "
  f"\n\n**Percussion:** {M['percussion']}\n\n**Caveat:** {M['instrumentation_note']}\n")
w('| section | time (s) | frames | what happens |\n|---|---|---|---|')
for s in M['sections']:
    w(f"| {s['id']} {s['label']} | {s['start']:.2f}-{s['end']:.2f} | {s['f_start']}-{s['f_end']} | {s['music']} |")
w('\n**Instrumentation evidence (heuristic):**')
w('- *Drone (M1):* lowest partial 71 Hz with harmonics at 146.6 / 220 / 293 Hz, i.e. D2/A2/D3/A3 (open fifth). Pitch wobble of about 30 cents at 6-8 Hz means bowed low strings, a male "hum" choir or a chorused synth drone. Energy sits in 60-250 Hz and nothing above 6 kHz (air band -70 to -85 dB), so it sounds dark.')
w('- *Pads/chords (M2, M4, M5):* stable sustained partials with 6-12 cents of pitch wobble at 6-8 Hz (ensemble vibrato), so a string section or choir pad. Side and mid are equal in power (about 0 dB), so they are very wide and reverberant.')
w('- *Sustained Bb3 (49.7-50.8 s and 58.1-59.5 s):* 233.0 Hz with strong 2nd-6th partials (-4 to -12 dB), so horn, cello or choir "ah". This is the brightest, most "hopeful" colour (Bb major = VI of D minor).')
w('- *Tail (M7):* G5/E5/A5/C6 partials with only 4 cents of pitch deviation (no vibrato), so a pad or synth (or frozen reverb). It has no bass and nothing above 2 kHz.')
w('- *No drums, timpani hits or risers were found.* The "accents" of the music are bass re-articulations, drone swells, entries and drop-outs.\n')
w('**Macro dynamic arc (music-only level).** M1 about -36 dBFS, then M2 about -29 (first peak, on "every lord ... empty chair"). The music then **collapses to -47..-52 for ~7 s (26.6-33.9 s: the war passage plays over near-silence)**, '
  f"returns to a -40 plateau (M4), and gets the **bass entry at 42.78 s** (-31). It builds to a **climax of -25.6 dBFS in the 58.14-59.46 s gap**, then **recedes ~19 dB under the final question (59.43 -> 60.80 s)** and rings out at about -45 to -48 to the end. "
  f"Long-range build: +{M['macro_crescendo']['rise_db']} dB from the 31.8 s valley to the climax.\n")
w('**Tempo / pulse.** ' + M['tempo']['verdict'])
bp = M['tempo']['bar_pulse']
w(f"- Bass bar pulse: {', '.join(f'{t:.2f}' for t in bp['events'])} s, period **{bp['period_s']} s** (max residual {bp['max_residual_ms']:.0f} ms), i.e. about {bp['bpm_if_4_beats_per_bar']} bpm at 4 beats per bar or about 85 bpm at 3. "
  f"Extrapolated next bars at {bp['extrapolated'][0]} and {bp['extrapolated'][1]} s, but the bass is already fading there. Frames: {', '.join(str(fr(t)) for t in bp['events'])}.")
st = M['tempo']['stats']
w(f"- Autocorrelation (peak vs shuffled baseline): full mix {st['full_mix_onset']['autocorr_peak']} @ {st['full_mix_onset']['autocorr_peak_lag_s']} s vs {st['full_mix_onset']['shuffled_baseline']}; side music {st['side_music_onset']['autocorr_peak']} @ {st['side_music_onset']['autocorr_peak_lag_s']} s vs {st['side_music_onset']['shuffled_baseline']}; "
  f"side low band {st['side_low_onset']['autocorr_peak']} @ {st['side_low_onset']['autocorr_peak_lag_s']} s vs {st['side_low_onset']['shuffled_baseline']}. librosa beat_track reports {st['full_mix_onset']['librosa_beat_track_bpm']} / {st['side_music_onset']['librosa_beat_track_bpm']} bpm, but these are syllable-rate artefacts, so **confidence in any global beat grid is low**. Cut to the narration and the events below, not to a metronome.\n")
w('## 5. Detected events\n')
w('**Drone exit:** ' + f"-6 dB at {M['drone']['fade_begin']} s (frame {M['drone']['fade_begin_frame']}), -15 dB at {M['drone']['minus15db']} s (frame {M['drone']['minus15db_frame']}), -25 dB at {M['drone']['minus25db']} s (frame {M['drone']['minus25db_frame']}). It fades under \"Then the king died ... and left no heir\".\n")
w('**Near-silences (mix < -40 dBFS, 0.25 s or longer):**\n')
w('| start s | end s | frames | dur s | mean dBFS |\n|---|---|---|---|---|')
for s in M['near_silences']:
    if s['dur'] >= 0.25: w(f"| {s['start']:.3f} | {s['end']:.3f} | {s['f_start']}-{s['f_end']} | {s['dur']:.2f} | {s['mean_db']} |")
w('\n**Crescendos (music level, 1 s smoothing; rise of 4 dB or more):**\n')
w('| start s (frame) | peak s (frame) | rise dB | slope dB/s | peak music dBFS |\n|---|---|---|---|---|')
for c in M['crescendos']:
    w(f"| {c['start']:.2f} ({c['f_start']}) | {c['peak']:.2f} ({c['f_peak']}) | +{c['rise_db']} | {c['slope_db_per_s']} | {c['peak_music_db']} |")
w('\nIn-gap swells, where the music rises inside a music-only gap into the next phrase: ' + '; '.join(f"{s['start']:.2f}-{s['end']:.2f} s (+{s['rise_db']} dB, into {s['into_phrase']})" for s in M['gap_swells']) + '.\n')
w('**Low-frequency (< 200 Hz) transients.** In the full mix every strong one falls inside a narration word (narrator F0 73-134 Hz plus plosives), so they are voice, not drums. '
  'On the voice-free side channel (22-120 Hz) the music shows these bass entries/swells (rise in dB, level after):\n')
w('| time s | frame | rise dB | level after dBFS | during word |\n|---|---|---|---|---|')
for b in M['bass_entries']:
    if b['time'] > 1 and b['level_after_db'] > -50:
        w(f"| {b['time']:.2f} | {b['frame']} | +{b['rise_db']} | {b['level_after_db']} | {b['word'] or '(gap)'} |")
w('\n**Section boundaries.** The curated sections in section 4 combine the algorithmic novelty peaks (Foote checkerboard kernel, +/-4 s and +/-8 s, on side-channel chroma + band energies + music level) '
  'with the drone, valley, bass and fade measurements. Algorithmic peaks: ' + ', '.join(f"{n['time']:.1f} s (f{n['frame']}, {n['strength']:.2f})" for n in M['novelty_peaks']) +
  '. The 0.6 s peak is the fade-in; the 60.6 s peak is the end-of-file effect of the wide kernel on the 59.4-61.0 s recession.\n')
f = M['fade']
w(f"**Final fade / ending.** Music recession starts at {f['music_fade_start']} s (frame {f['music_fade_start_frame']}), right as P21 begins. It is -{f['music_fade_depth_db']} dB by {f['music_fade_end']} s (frame {f['music_fade_end_frame']}), and the bass is gone at {f['bass_gone_time']} s. "
  f"Narration ends at {f['narration_end']} s (frame {f['narration_end_frame']}). The tail chord decays {f['tail_decay_db_per_s']} dB/s ({f['tail_lufs_start']} -> {f['tail_lufs_end']} LUFS); the last second is at {f['last_second_rms_db']} dBFS RMS. "
  f"A micro-fade starts at {f['micro_fade_start']} s (frame {f['micro_fade_frame']}) and the last sample is at {f['audio_end']} s. **The audio does not fade to silence**: it stops from about -48 dBFS in about 30 ms. Picture should be at or near black or on a held title card by then. "
  "An optional 0.5-1 s gain ramp to silence in the final mix would also hide it.\n")
w('## 6. Top-30 accents (merged and ranked; deduplicated within 0.2 s)\n')
w('Narration attacks dominate the full-mix transients, so the list mixes the strongest narration attacks (over music) with voice-free music bass entries.\n')
w('| # | time s | frame | strength | kind | word |\n|---|---|---|---|---|---|')
for i, a in enumerate(J['accents_top30']):
    w(f"| {i + 1} | {a['time']:.2f} | {a['frame']} | {a['strength']:.2f} | {a['kind']} ({a['source']}) | {a['word'] or '-'} |")
w('\n## 7. The 25 sync points a cinematic should hit\n')
w('| # | time s | frame | (end) | what happens |\n|---|---|---|---|---|')
for i, s in enumerate(J['sync_points_top25']):
    end = f"{s['end_time']:.2f} s / f{s['end_frame']}" if 'end_time' in s else ''
    w(f"| {i + 1} | {s['time']:.3f} | {s['frame']} | {end} | {s['what']} |")
w('\n**Mapping to existing art (suggestion).** p1_oath.png fits B1-B2 (0.14-13.42 s); p3_death.png fits B3 (14.88-26.64 s, with the drone exit at 16-18 s and the collapse at 26.6 s); '
  'p6_ruin.png fits B4 (28.16-44.54 s, over a near-silent score until 33.9 s, then the plateau and the bass entry at 42.78 s). '
  'B5-B6 (46.08-61.84 s) is the rising, brightest music with the 2.1 s bass pulse and should carry the "new chronicle / blank page / you" imagery. The tail (61.84-66.13 s) is the title/logo.\n')
w('## 8. Method and caveats\n')
w('- Decode: ffmpeg to float32 WAV (`audio_f32.wav`; PCM16 copy `audio_s16.wav`; original MP3 copied as `audio_original.mp3`). '
  'Features at 10 ms hops (n_fft 2048) are aggregated to video frames (max for onsets/flux, mean for spectra); RMS is computed on exact 1470-sample frame windows.')
w('- Onsets: librosa onset strength (mel, lag 2, max-filter 3 = superflux-like) and peak-picking. Spectral flux: positive log-magnitude difference. Loudness: BS.1770 K-weighting (pyloudnorm filters), 400 ms window.')
w('- Music vs narration: Scribe word spans, plus the discovery that the narration is perfectly centred. The side channel (L-R)/2 does not rise during words (median +0.0 dB vs +5.6 dB on mid; envelope correlation with word spans 0.06 vs 0.52), '
  'while the music has equal power in side and mid. Music level = side power minus a -27 dB narration-leak term (correction capped at 3 dB), calibrated to the mix in music-only gaps (offset +1.2 dB). '
  'Under the loudest words in the quietest passages (28-31.5 s) the side still contains some leak, so treat the music level there as an upper bound (at or below -48 dBFS).')
w('- Harmony: CQT (36 bins/octave) of the side channel, median-smoothed, folded to chroma, then template matching (triads/7ths/add9/6/sus) and a Krumhansl-Schmuckler key. Chord labels are estimates, most reliable in the music-only gaps.')
w('- Neural source separation (Demucs/Spleeter/Open-Unmix) was not possible because their weight hosts are blocked by the proxy. A REPET-SIM and an F0-comb-masked CQT were also tried (`dbg/`); the side channel proved cleaner.')
w('- Scripts: `s1_features.py` (mix features), `s1b_side.py` (side features), `s2_analyze.py` (detection), `s3_outputs.py` (JSON + PNG), `s4_report.py` (this file). Total CPU is about 2 minutes.')
open(f'{O}/audio_report.md', 'w').write('\n'.join(o) + '\n')
print('report lines', len(o))
