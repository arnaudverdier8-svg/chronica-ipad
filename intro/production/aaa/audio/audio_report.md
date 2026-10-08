# CHRONICA intro: frame-accurate audio analysis

Source: `/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/audio/audio_original.mp3` (md5 `f0837d29396534df54023882e93861ee`), with narration timings from `words.json` (ElevenLabs Scribe v1). Machine-readable version: `audio_timeline.json`. Per-frame data: `audio_frames.npy` / `audio_frames.csv`. Picture: `audio_overview.png`.

## 1. Duration and frame count (authoritative)

| quantity | value |
|---|---|
| Decoded PCM length | **2,915,328 samples @ 44.1 kHz = 66.107211 s** (stereo) |
| ffprobe container duration | 66.142041 s = 2532 MPEG frames x 1152. This includes encoder delay and padding, so it is **not** the playable length |
| ffprobe start_time | 0.025057 s = 1105 samples skipped by the decoder (576 LAME encoder delay + 529 decoder delay) |
| LAME tag | encoder Lavc59.37 (libmp3lame), delay 576, end padding 960, about 169 kbps |
| Gapless check | ffmpeg and libsndfile/mpg123 both decode exactly 2,915,328 samples = 2532 x 1152 - 1105 - 431 |
| Seconds x 30 fps | 1983.216 frames |
| **Video length** | **1984 frames (0..1983) = 66.133333 s** |
| Audio pad | 1152 samples (26.1 ms) of digital silence appended, giving 2,916,480 samples = 1984 x 1470 |
| Ready-made master | `audio_master_1984f_f32.wav` (float32) and `audio_master_1984f_s16.wav` (PCM16), exactly 66.133333 s |
| words.json alignment | Scribe word starts vs. audio onsets: median offset +0.015 s (energy rise -0.01 s); within half a frame, so no correction is needed. |

**Rounding policy.** Round up to 1984 frames and pad the audio with silence, so video duration equals audio duration exactly with no audio lost. Rounding down to 1983 frames would cut 318 samples (7.2 ms) of the final micro-fade. Mux from the padded WAV, never by stream-copying the MP3: its 66.142 s container duration and encoder priming would shift the end.

**Frame convention used everywhere:** `frame = floor(t x 30)`, the frame on screen when the sound happens. For hard cuts on an attack, cutting 1 frame early (frame - 1) usually reads as on-beat.

## 2. Loudness, stereo, voice

- Integrated loudness -19.67 LUFS, sample peak -6.9 dBFS, true peak -6.89 dBTP. Integrated loudness is -19.7 LUFS with 6.9 dB of true-peak headroom. +3.7 dB gives -16 LUFS (TP about -3.2 dBTP); +5.7 dB gives -14 LUFS (TP about -1.2 dBTP). Apply the gain only if the delivery spec asks for it.
- Narration phrase peaks sit in a tight -19.1 to -15.5 dBFS band. The narrator is a deep male voice: F0 median 96.4 Hz (p10 73.0, p90 133.9). Pace is 2.85 words/s while speaking.
- Narration is mixed dead-centre (it does not raise the side channel); the music is very wide (side approximately equal to mid in every band). Side = (L-R)/2 is a near voice-free view of the music. This side channel drives the music-only measurements below (music level, bass entries, harmony). Residual narration leak into the side is at or below -27 dB relative to the voice.

## 3. Narration structure

Story beats (sentences grouped by meaning):

| beat | time (s) | frames | content |
|---|---|---|---|
| B1 | 0.14-8.28 | 4-248 | Golden age litany: one realm, one table, one oath, one crown |
| B2 | 9.22-13.42 | 276-402 | The oath: they raised their cups and swore it would never end |
| B3 | 14.88-26.64 | 446-799 | The king dies without heir; every lord eyes the empty chair and the crown |
| B4 | 28.16-44.54 | 844-1336 | A hundred years of war: cities fall, roads swallowed, borders forgotten, the world grows dark |
| B5 | 46.08-54.86 | 1382-1645 | Now: every ruler believes the world can be made whole; one banner, one village, one blank page |
| B6 | 56.32-61.84 | 1689-1855 | The question: when this age is remembered, what will the chronicles say of you? |
| B7 | 61.84-66.11 | 1855-1983 | Music-only tail (title / logo) |

Phrases (split at pauses of 0.45 s or more, or at punctuation). The stressed word comes from a loudness + length + content-word heuristic:

| id | start s | end s | frames | text | stressed word (frame) | peak dBFS |
|---|---|---|---|---|---|---|
| P01 | 0.14 | 3.48 | 4-104 | There was a time when the world knew only one realm, | world (39) | -16.9 |
| P02 | 4.20 | 5.06 | 126-151 | one table, | table, (140) | -17.8 |
| P03 | 5.42 | 6.16 | 162-184 | one oath, | oath, (173) | -17.4 |
| P04 | 7.08 | 8.28 | 212-248 | one crown. | crown. (230) | -18.2 |
| P05 | 9.22 | 10.74 | 276-322 | They raised their cups | raised (285) | -18.2 |
| P06 | 11.32 | 13.42 | 339-402 | and swore it would never end. | swore (349) | -18.1 |
| P07 | 14.88 | 16.12 | 446-483 | Then the king died | died (469) | -17.1 |
| P08 | 16.62 | 17.76 | 498-532 | and left no heir, | heir, (522) | -18.7 |
| P09 | 18.72 | 22.72 | 561-681 | and every lord who had sat at that table looked at the empty chair | lord (578) | -15.7 |
| P10 | 23.90 | 26.64 | 717-799 | and saw his own head beneath the crown. | own (741) | -19.1 |
| P11 | 28.16 | 31.84 | 844-955 | The wars lasted a hundred years and ended nothing. | years (899) | -17.1 |
| P12 | 32.74 | 34.28 | 982-1028 | Cities fell to ruin. | Cities (982) | -16.5 |
| P13 | 35.04 | 37.18 | 1051-1115 | Roads were swallowed by the forest. | Roads (1051) | -15.7 |
| P14 | 37.96 | 40.98 | 1138-1229 | Men forgot what lay beyond their own borders, | borders, (1211) | -17.1 |
| P15 | 41.80 | 44.54 | 1254-1336 | and the world grew dark at its edges. | world (1263) | -18.1 |
| P16 | 46.08 | 49.72 | 1382-1491 | Now every ruler believes the world can be made whole again. | believes (1419) | -15.5 |
| P17 | 50.80 | 51.48 | 1524-1544 | One banner, | banner, (1533) | -18.2 |
| P18 | 51.98 | 52.78 | 1559-1583 | one village, | village, (1569) | -16.9 |
| P19 | 53.30 | 54.86 | 1599-1645 | one blank page. | page. (1630) | -18.7 |
| P20 | 56.32 | 58.14 | 1689-1744 | When this age is remembered, | remembered, (1726) | -16.3 |
| P21 | 59.46 | 61.84 | 1783-1855 | what will the chronicles say of you? | chronicles (1801) | -17.5 |

Music-only gaps longer than 0.5 s. These are the windows for cuts, panel changes and reveals. The music level comes from the voice-free side channel, calibrated to the mix; the chord estimate comes from side-channel chroma:

| start s | end s | dur s | frames | music dBFS | est. harmony (top pitch classes) |
|---|---|---|---|---|---|
| 3.48 | 4.20 | 0.72 | 104-126 | -37.0 | Dadd9 (D, A, E, C#) |
| 6.16 | 7.08 | 0.92 | 184-212 | -39.9 | Dmaj7 (D, C#, A, C) |
| 8.28 | 9.22 | 0.94 | 248-276 | -32.8 | Dmaj7 (D, A, Eb, C#) |
| 10.74 | 11.32 | 0.58 | 322-339 | -34.5 | Dmaj7 (D, A, C#, Eb) |
| 13.42 | 14.88 | 1.46 | 402-446 | -33.5 | Dmaj7 (D, A, C#, Eb) |
| 17.76 | 18.72 | 0.96 | 532-561 | -28.1 | F6 (F, D, A, E) |
| 22.72 | 23.90 | 1.18 | 681-717 | -29.4 | F6 (F, A, D, Bb) |
| 26.64 | 28.16 | 1.52 | 799-844 | -46.5 | Gm(add9) (A, F, G, D) |
| 31.84 | 32.74 | 0.90 | 955-982 | -46.9 | C6 (G, C, F#, A) |
| 34.28 | 35.04 | 0.76 | 1028-1051 | -41.9 | Dm(add9) (F, D, E, A) |
| 37.18 | 37.96 | 0.78 | 1115-1138 | -40.1 | Dm(add9) (D, F, E, A) |
| 40.98 | 41.80 | 0.82 | 1229-1254 | -38.2 | Dm7 (D, A, C, F#) |
| 44.54 | 46.08 | 1.54 | 1336-1382 | -31.9 | F6 (F, D, E, A) |
| 49.72 | 50.80 | 1.08 | 1491-1524 | -32.0 | Bbmaj7 (Bb, D, F, F#) |
| 52.78 | 53.30 | 0.52 | 1583-1599 | -30.9 | Dm(add9) (F, E, D, B) |
| 54.86 | 56.32 | 1.46 | 1645-1689 | -29.0 | Dm(add9) (D, F, E, A) |
| 58.14 | 59.46 | 1.32 | 1744-1783 | -25.5 | F6 (F, D, Bb, A) |
| 61.84 | 66.11 | 4.27 | 1855-1983 | -47.0 | G6 (G, E, D, F) |

How to read the chord labels: in the M1 gaps (0-15 s) the C# comes mostly from the flat ~71 Hz drone partial, which sits between C#2 and D2. Read those gaps as a D5/Dadd9 drone with a slightly sour beating, not as Dmaj7. "F6" (F-A-D-E) is the same pitch set as Dm7(add9)/F. The 26.6 s and 31.8 s gaps are near-silent, so their labels are weak.


## 4. What the music does

**Character.** The score is an unmetered, rubato ambient/orchestral bed in **D minor (natural/Aeolian; Bb and F major-7 colours, C#/D drone beating)** (Krumhansl fit 0.943 for D minor). 

**Percussion:** None detected. HPSS percussive ratio in music-only gaps is 0.01-0.16 (narration frames 0.25). Every strong <200 Hz transient in the mix falls inside narration words (narrator F0 is 73-134 Hz).

**Caveat:** No neural stem separation was possible (model hosts are blocked). Timbre conclusions come from the side channel, pitch-stability (vibrato) measurements, HPSS and band balance, so they are heuristics.

| section | time (s) | frames | what happens |
|---|---|---|---|
| M0 Digital near-silence (4 frames) | 0.00-0.13 | 0-3 | Nothing audible (-73..-90 dBFS). |
| M1 Drone / golden age | 0.13-16.80 | 4-504 | Fast fade-in (~0.5 s) of a dark D pedal drone (open fifth D-A, lowest partial ~71 Hz with ~30-cent, 6-8 Hz wobble) under a soft, very wide sustained pad. No percussion. The drone re-swells in narration gaps; music-only level -38 dBFS (3.5 s) rising to -31 dBFS (13.4 s). |
| M2 Lament (drone exits) | 16.80-26.60 | 504-798 | The D drone fades from ~16.8 s (-15 dB at ~17.8 s, -25 dB by ~18.3 s, i.e. under "and left no heir"). Mid-register sustained chords take over (D minor 7 -> F major 7 colour, energy 250 Hz-2 kHz, no sub-bass) with ensemble-like pitch wobble (10-12 cents at 6-7 Hz): string-section / choir-pad timbre. Music-only level ~-31 dBFS; fullest around 23-25.5 s. |
| M3 Hollow war (music almost silent) | 26.60-33.90 | 798-1017 | Right after "...beneath the crown." the music collapses by ~20 dB (from ~-27 dBFS at 25 s to -47 dBFS at 27 s) and stays at or below about -45 dBFS for ~7 s: under the whole of "The wars lasted a hundred years and ended nothing." and the start of "Cities fell to ruin." Only a thin, airy, high, bass-less texture remains (no sub-bass, no percussion). Two fully exposed near-silent gaps: 26.6-28.1 s and 31.8-32.7 s (-47 dBFS). |
| M4 Ruin plateau (soft pad returns) | 33.90-42.70 | 1017-1281 | A soft, mid-register Dm(add9) pad returns at ~33.9-34.0 s (+5 dB) and holds a plateau around -40 dBFS under "Roads were swallowed by the forest" and "Men forgot what lay beyond their own borders", creeping up to ~-36 dBFS by 41.5 s; a D7 colour (F# appears) in the 41 s gap. Still no bass below ~60 Hz. |
| M5 Rise to climax (bass returns, slow bar pulse) | 42.70-59.46 | 1281-1783 | Big low-register entry at 42.78 s on "the world grew dark" (+26 dB in 22-120 Hz), then bass swells every ~2.1 s (42.78, 44.85, 47.00, 49.06, 51.21, 53.30, 55.49, 57.55 s): a slow bar pulse (~114 bpm if 4 beats per bar). Fullest, widest, brightest texture of the piece: a sustained Bb3 (233 Hz, strong 2nd-6th partials, ~10-cent vibrato: horn / cello / choir-like) over F and Bb major-7 harmony; music-only level -32.5 dBFS (44.5 s) -> -30 (50 s) -> -25.6 dBFS in the climax gap 58.14-59.46 s (loudest music of the piece, Bbmaj7 colour). |
| M6 Recession under the question | 59.46-61.84 | 1783-1855 | From ~59.4 s, exactly as "what will the chronicles say of you?" begins, the music pulls back ~19 dB in ~1.4 s (-25 dBFS -> -44 dBFS by ~60.8 s); the bass is gone by ~60.8 s. The final words sit almost alone over a faint high chord. |
| M7 Tail (ring-out, no narration) | 61.84-66.11 | 1855-1983 | After the last word (61.84 s) only a soft, very stable (pitch sd 4 cents), bass-less and dark (nothing above ~2 kHz) high chord remains (G5-E5-A5-C6 partials: an open, unresolved Am7/C6 colour, not the D-minor tonic), decaying ~1 dB/s from -39 to -44 LUFS. The file ends at 66.107 s while still at ~-48 dBFS, with only a ~30 ms micro-fade: an abrupt end unless the picture covers it. |

**Instrumentation evidence (heuristic):**
- *Drone (M1):* lowest partial 71 Hz with harmonics at 146.6 / 220 / 293 Hz, i.e. D2/A2/D3/A3 (open fifth). Pitch wobble of about 30 cents at 6-8 Hz means bowed low strings, a male "hum" choir or a chorused synth drone. Energy sits in 60-250 Hz and nothing above 6 kHz (air band -70 to -85 dB), so it sounds dark.
- *Pads/chords (M2, M4, M5):* stable sustained partials with 6-12 cents of pitch wobble at 6-8 Hz (ensemble vibrato), so a string section or choir pad. Side and mid are equal in power (about 0 dB), so they are very wide and reverberant.
- *Sustained Bb3 (49.7-50.8 s and 58.1-59.5 s):* 233.0 Hz with strong 2nd-6th partials (-4 to -12 dB), so horn, cello or choir "ah". This is the brightest, most "hopeful" colour (Bb major = VI of D minor).
- *Tail (M7):* G5/E5/A5/C6 partials with only 4 cents of pitch deviation (no vibrato), so a pad or synth (or frozen reverb). It has no bass and nothing above 2 kHz.
- *No drums, timpani hits or risers were found.* The "accents" of the music are bass re-articulations, drone swells, entries and drop-outs.

**Macro dynamic arc (music-only level).** M1 about -36 dBFS, then M2 about -29 (first peak, on "every lord ... empty chair"). The music then **collapses to -47..-52 for ~7 s (26.6-33.9 s: the war passage plays over near-silence)**, returns to a -40 plateau (M4), and gets the **bass entry at 42.78 s** (-31). It builds to a **climax of -25.6 dBFS in the 58.14-59.46 s gap**, then **recedes ~19 dB under the final question (59.43 -> 60.80 s)** and rings out at about -45 to -48 to the end. Long-range build: +21.7 dB from the 31.8 s valley to the climax.

**Tempo / pulse.** Unmetered, rubato ambient score with no steady beat. Autocorrelation peaks at 0.35/0.46/0.71 s follow the narration rhythm (2.85 words/s). The only robust periodicity is the slow bass bar pulse in 42.8-57.6 s.
- Bass bar pulse: 42.78, 44.85, 47.00, 49.06, 51.21, 53.30, 55.49, 57.55 s, period **2.115 s** (max residual 48 ms), i.e. about 113.5 bpm at 4 beats per bar or about 85 bpm at 3. Extrapolated next bars at 59.671 and 61.786 s, but the bass is already fading there. Frames: 1283, 1345, 1410, 1471, 1536, 1599, 1664, 1726.
- Autocorrelation (peak vs shuffled baseline): full mix 0.116 @ 0.46 s vs 0.04; side music 0.117 @ 0.71 s vs 0.035; side low band 0.088 @ 0.35 s vs 0.037. librosa beat_track reports 130.4 / 117.6 bpm, but these are syllable-rate artefacts, so **confidence in any global beat grid is low**. Cut to the narration and the events below, not to a metronome.

## 5. Detected events

**Drone exit:** -6 dB at 16.01 s (frame 480), -15 dB at 17.82 s (frame 534), -25 dB at 18.28 s (frame 548). It fades under "Then the king died ... and left no heir".

**Near-silences (mix < -40 dBFS, 0.25 s or longer):**

| start s | end s | frames | dur s | mean dBFS |
|---|---|---|---|---|
| 6.167 | 6.633 | 185-198 | 0.47 | -45.0 |
| 26.567 | 28.167 | 797-844 | 1.60 | -47.0 |
| 31.733 | 32.667 | 952-979 | 0.93 | -47.1 |
| 34.300 | 34.933 | 1029-1047 | 0.63 | -42.9 |
| 61.767 | 66.133 | 1853-1983 | 4.37 | -46.7 |

**Crescendos (music level, 1 s smoothing; rise of 4 dB or more):**

| start s (frame) | peak s (frame) | rise dB | slope dB/s | peak music dBFS |
|---|---|---|---|---|
| 6.17 (185) | 9.03 (271) | +8.8 | 3.07 | -33.0 |
| 15.97 (479) | 18.20 (546) | +6.0 | 2.7 | -28.1 |
| 29.87 (896) | 32.80 (984) | +6.5 | 2.23 | -45.8 |
| 33.37 (1001) | 35.37 (1061) | +6.8 | 3.39 | -41.1 |
| 41.63 (1249) | 43.27 (1298) | +7.3 | 4.46 | -30.6 |
| 50.67 (1520) | 51.67 (1550) | +4.0 | 4.01 | -28.8 |

In-gap swells, where the music rises inside a music-only gap into the next phrase: 6.50-7.17 s (+10.3 dB, into P04); 41.37-41.90 s (+4.1 dB, into P15); 45.73-46.17 s (+5.8 dB, into P16); 55.27-56.40 s (+4.8 dB, into P20).

**Low-frequency (< 200 Hz) transients.** In the full mix every strong one falls inside a narration word (narrator F0 73-134 Hz plus plosives), so they are voice, not drums. On the voice-free side channel (22-120 Hz) the music shows these bass entries/swells (rise in dB, level after):

| time s | frame | rise dB | level after dBFS | during word |
|---|---|---|---|---|
| 2.54 | 76 | +9.3 | -36.8 | (gap) |
| 4.22 | 126 | +12.5 | -44.8 | one |
| 6.70 | 201 | +13.7 | -39.2 | (gap) |
| 7.58 | 227 | +9.2 | -44.1 | (gap) |
| 9.87 | 296 | +14.3 | -41.9 | raised |
| 10.78 | 323 | +13.0 | -40.8 | (gap) |
| 11.94 | 358 | +18.2 | -38.4 | swore |
| 13.03 | 390 | +12.5 | -38.3 | (gap) |
| 14.27 | 428 | +9.6 | -39.8 | (gap) |
| 16.53 | 495 | +10.4 | -39.1 | (gap) |
| 25.03 | 750 | +16.7 | -49.9 | (gap) |
| 42.78 | 1283 | +26.0 | -42.6 | grew |
| 44.85 | 1345 | +19.5 | -43.5 | (gap) |
| 47.00 | 1410 | +18.3 | -46.5 | ruler |
| 49.06 | 1471 | +13.7 | -44.6 | whole |
| 51.21 | 1536 | +14.9 | -45.2 | banner, |
| 53.30 | 1599 | +21.6 | -43.4 | one |
| 55.49 | 1664 | +13.5 | -44.0 | (gap) |
| 57.55 | 1726 | +18.4 | -44.7 | remembered, |
| 58.50 | 1755 | +11.0 | -42.8 | (gap) |

**Section boundaries.** The curated sections in section 4 combine the algorithmic novelty peaks (Foote checkerboard kernel, +/-4 s and +/-8 s, on side-channel chroma + band energies + music level) with the drone, valley, bass and fade measurements. Algorithmic peaks: 0.6 s (f18, 0.55), 8.8 s (f264, 0.24), 17.4 s (f522, 0.57), 26.6 s (f798, 0.59), 34.0 s (f1020, 0.20), 42.6 s (f1278, 0.48), 48.0 s (f1440, 0.37), 52.2 s (f1566, 0.28), 60.6 s (f1818, 1.00). The 0.6 s peak is the fade-in; the 60.6 s peak is the end-of-file effect of the wide kernel on the 59.4-61.0 s recession.

**Final fade / ending.** Music recession starts at 59.433 s (frame 1783), right as P21 begins. It is -18.8 dB by 60.8 s (frame 1824), and the bass is gone at 60.79 s. Narration ends at 61.84 s (frame 1855). The tail chord decays -1.07 dB/s (-39.4 -> -43.6 LUFS); the last second is at -48.5 dBFS RMS. A micro-fade starts at 66.075 s (frame 1982) and the last sample is at 66.107211 s. **The audio does not fade to silence**: it stops from about -48 dBFS in about 30 ms. Picture should be at or near black or on a held title card by then. An optional 0.5-1 s gain ramp to silence in the final mix would also hide it.

## 6. Top-30 accents (merged and ranked; deduplicated within 0.2 s)

Narration attacks dominate the full-mix transients, so the list mixes the strongest narration attacks (over music) with voice-free music bass entries.

| # | time s | frame | strength | kind | word |
|---|---|---|---|---|---|
| 1 | 0.17 | 5 | 1.00 | onset (narration attack (+music)) | There |
| 2 | 42.78 | 1283 | 0.87 | bass_entry (music (side-channel 22-120 Hz rise)) | grew |
| 3 | 0.63 | 18 | 0.81 | onset (narration attack (+music)) | a |
| 4 | 11.94 | 358 | 0.70 | bass_entry (music (side-channel 22-120 Hz rise)) | swore |
| 5 | 53.30 | 1599 | 0.69 | bass_entry (music (side-channel 22-120 Hz rise)) | one |
| 6 | 44.85 | 1345 | 0.62 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 7 | 7.65 | 229 | 0.55 | onset (narration attack (+music)) | crown. |
| 8 | 57.55 | 1726 | 0.54 | bass_entry (music (side-channel 22-120 Hz rise)) | remembered, |
| 9 | 15.28 | 458 | 0.53 | onset (narration attack (+music)) | the |
| 10 | 6.70 | 201 | 0.53 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 11 | 10.26 | 307 | 0.51 | onset (narration attack (+music)) | cups |
| 12 | 9.87 | 296 | 0.50 | bass_entry (music (side-channel 22-120 Hz rise)) | raised |
| 13 | 13.03 | 390 | 0.48 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 14 | 10.78 | 323 | 0.48 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 15 | 47.00 | 1410 | 0.47 | bass_entry (music (side-channel 22-120 Hz rise)) | ruler |
| 16 | 51.12 | 1533 | 0.47 | onset (narration attack (+music)) | banner, |
| 17 | 32.92 | 987 | 0.46 | onset (narration attack (+music)) | Cities |
| 18 | 4.66 | 139 | 0.44 | onset (narration attack (+music)) | table, |
| 19 | 55.49 | 1664 | 0.41 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 20 | 49.06 | 1471 | 0.41 | bass_entry (music (side-channel 22-120 Hz rise)) | whole |
| 21 | 16.53 | 495 | 0.40 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 22 | 33.65 | 1009 | 0.38 | onset (narration attack (+music)) | fell |
| 23 | 28.19 | 845 | 0.38 | onset (narration attack (+music)) | The |
| 24 | 37.98 | 1139 | 0.37 | onset (narration attack (+music)) | Men |
| 25 | 14.27 | 428 | 0.37 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 26 | 4.22 | 126 | 0.36 | bass_entry (music (side-channel 22-120 Hz rise)) | one |
| 27 | 58.50 | 1755 | 0.36 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 28 | 38.48 | 1154 | 0.36 | onset (narration attack (+music)) | forgot |
| 29 | 2.54 | 76 | 0.36 | bass_entry (music (side-channel 22-120 Hz rise)) | - |
| 30 | 29.32 | 879 | 0.35 | onset (narration attack (+music)) | lasted |

## 7. The 25 sync points a cinematic should hit

| # | time s | frame | (end) | what happens |
|---|---|---|---|---|
| 1 | 0.000 | 0 |  | Picture start. Audio frames 0-3 are silent; sound begins at frame 4. Fade up from black over frames 0-4 at most. |
| 2 | 0.140 | 4 |  | Narration "There was a time..." and the D drone start together (strongest attack of the file at 0.17 s, frame 5). |
| 3 | 2.560 | 76 |  | Litany 1/4 "one realm" ("realm" at 3.04 s, frame 91). |
| 4 | 4.200 | 126 |  | Litany 2/4 "one table" ("table" at 4.68 s, frame 140), with a drone re-swell at 4.22 s. |
| 5 | 5.420 | 162 |  | Litany 3/4 "one oath"; then a 0.47 s near-silence (6.17-6.63 s, -45 dBFS) and a +10 dB swell. |
| 6 | 7.080 | 212 |  | Litany 4/4 "one crown." (attack on "crown" at 7.65 s, frame 229). End of the golden-age beat at 8.28 s. |
| 7 | 9.220 | 276 |  | B2 oath: "They raised their cups" ("cups" attack 10.26 s, frame 307). Music crescendo 6.2 -> 9.0 s peaks here. |
| 8 | 11.640 | 349 | 13.42 s / f402 | "and swore it would never end." Strongest early drone swell at 11.94 s (frame 358); phrase ends 13.42 s, then a 1.46 s music-only gap (frames 402-446) for the panel change. |
| 9 | 14.880 | 446 |  | B3 death: "Then the king died" ("died" at 15.64 s, frame 469). |
| 10 | 16.010 | 480 | 18.28 s / f548 | The D drone (the floor of the score) fades out under "and left no heir": -15 dB at 17.82 s (frame 534), gone by 18.28 s. |
| 11 | 18.720 | 561 |  | "and every lord..." Lament chords (Dm9/F colour), music about 5 dB louder than in B1 (about -28 dBFS). "empty chair" at 21.88-22.72 s (frames 656-681). |
| 12 | 23.900 | 717 |  | "and saw his own head beneath the crown." ("crown" at 26.18 s, frame 785). |
| 13 | 26.600 | 798 | 28.16 s / f844 | The music collapses by about 20 dB into near-silence (frames 797-844, -47 dBFS for 1.6 s). This is the strongest internal boundary. Hold, stillness or a cut to black. |
| 14 | 28.160 | 844 |  | B4 war: "The wars lasted a hundred years and ended nothing." The music stays at or below about -45 dBFS (nearly silent) until about 33.9 s, with a second silent gap at 31.73-32.67 s. |
| 15 | 32.740 | 982 |  | "Cities fell to ruin." (attack 32.92 s, frame 987; "fell" 33.32 s, frame 999) |
| 16 | 33.900 | 1017 |  | A soft pad returns (about +7 dB, 33.4 -> 35.4 s) into "Roads were swallowed by the forest." (35.04 s, frame 1051). |
| 17 | 37.960 | 1138 |  | "Men forgot what lay beyond their own borders," (attack 37.98 s, frame 1139). The music sits on a -40 dBFS plateau. |
| 18 | 42.780 | 1283 |  | Biggest musical event: the bass and low register enter on "grew" ("the world grew dark", phrase starts 41.80 s), +26 dB in 22-120 Hz. "dark" lands at 43.08 s (frame 1292). |
| 19 | 44.850 | 1345 |  | A bass swell in the 1.54 s music-only gap (frames 1336-1382). Bar pulse #2 of 8 (period about 2.115 s). |
| 20 | 46.080 | 1382 |  | B5 present: "Now every ruler believes the world can be made whole again." Bass pulses at 47.00 s (frame 1410) and 49.06 s (frame 1471). |
| 21 | 50.800 | 1524 |  | Litany 2: "One banner," / "one village," (51.98 s, frame 1559) / "one blank page." (53.30 s, frame 1599). Bass pulses land on "banner" (51.21 s) and "one [blank page]" (53.30 s). Bb major in the gap just before (49.72-50.80 s). |
| 22 | 56.320 | 1689 |  | B6: "When this age is remembered," Bass pulse #8 at 57.55 s (frame 1726) on "remembered". |
| 23 | 58.140 | 1744 | 59.46 s / f1783 | Music climax: the loudest music of the piece (-25.6 dBFS) in a 1.32 s music-only gap, peaking at 58.67 s (frame 1760). Best spot for the big visual reveal. |
| 24 | 59.460 | 1783 |  | "what will the chronicles say of you?" The music recedes about 19 dB from 59.43 s to 60.80 s and the bass is gone by 60.79 s. "chronicles" at 60.06 s (frame 1801), "you?" at 61.56-61.84 s (frames 1846-1855). |
| 25 | 61.840 | 1855 | 66.11 s / f1983 | Narration ends. A 4.27 s ring-out of a soft high unresolved chord follows (-44 -> -48 dBFS, about -1 dB/s): title or logo hold. Micro-fade at 66.075 s (frame 1982); last sample 66.107 s; final video frame is 1983 (1984 frames in total). |

**Mapping to existing art (suggestion).** p1_oath.png fits B1-B2 (0.14-13.42 s); p3_death.png fits B3 (14.88-26.64 s, with the drone exit at 16-18 s and the collapse at 26.6 s); p6_ruin.png fits B4 (28.16-44.54 s, over a near-silent score until 33.9 s, then the plateau and the bass entry at 42.78 s). B5-B6 (46.08-61.84 s) is the rising, brightest music with the 2.1 s bass pulse and should carry the "new chronicle / blank page / you" imagery. The tail (61.84-66.13 s) is the title/logo.

## 8. Method and caveats

- Decode: ffmpeg to float32 WAV (`audio_f32.wav`; PCM16 copy `audio_s16.wav`; original MP3 copied as `audio_original.mp3`). Features at 10 ms hops (n_fft 2048) are aggregated to video frames (max for onsets/flux, mean for spectra); RMS is computed on exact 1470-sample frame windows.
- Onsets: librosa onset strength (mel, lag 2, max-filter 3 = superflux-like) and peak-picking. Spectral flux: positive log-magnitude difference. Loudness: BS.1770 K-weighting (pyloudnorm filters), 400 ms window.
- Music vs narration: Scribe word spans, plus the discovery that the narration is perfectly centred. The side channel (L-R)/2 does not rise during words (median +0.0 dB vs +5.6 dB on mid; envelope correlation with word spans 0.06 vs 0.52), while the music has equal power in side and mid. Music level = side power minus a -27 dB narration-leak term (correction capped at 3 dB), calibrated to the mix in music-only gaps (offset +1.2 dB). Under the loudest words in the quietest passages (28-31.5 s) the side still contains some leak, so treat the music level there as an upper bound (at or below -48 dBFS).
- Harmony: CQT (36 bins/octave) of the side channel, median-smoothed, folded to chroma, then template matching (triads/7ths/add9/6/sus) and a Krumhansl-Schmuckler key. Chord labels are estimates, most reliable in the music-only gaps.
- Neural source separation (Demucs/Spleeter/Open-Unmix) was not possible because their weight hosts are blocked by the proxy. A REPET-SIM and an F0-comb-masked CQT were also tried (`dbg/`); the side channel proved cleaner.
- Scripts: `s1_features.py` (mix features), `s1b_side.py` (side features), `s2_analyze.py` (detection), `s3_outputs.py` (JSON + PNG), `s4_report.py` (this file). Total CPU is about 2 minutes.
