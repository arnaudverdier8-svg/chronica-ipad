# CHRONICA intro cinematic: production hand-off

This folder is everything needed to continue the intro cinematic on a local machine with a GPU
(the cloud container that started it has 4 CPU cores and no GPU).

## Where the project stands

| Stage | Status |
|---|---|
| Audio analysis (66.107 s decoded; master = 1984 frames at 30 fps; padded audio master) | Done: `aaa/audio/` |
| Repo and game audit (menu layout, video support, HTML overlay plan) | Done: `aaa/game/` |
| Style bible, palette, act colour script | Done: `aaa/style/` |
| Asset extraction (all textures, figure cards, 59 game models as OBJ) | Done: `aaa/assets/` |
| Storyboard: "The Living Frieze", 26 shots S01-S26 covering frames 0-1983 | Done: `aaa/story/storyboard_final.md` / `.json` |
| Rendering approach (3-way bake-off; 2.5D relight "R25" + Eevee for lifts) | Done: `aaa/rnd/pipeline_decision.md` |
| Shared embroidery library `chron` | Done: `aaa/lib/chron`, `aaa/lib/README.md` |
| Six keyframes | f91, f669, f1319, f1983 done (`keyframes/`); f899 rework and the f1760 / proof-of-concept rework were still running in the cloud when this was packed |
| Proof of concept f1664-1782 ("the cloth becomes the board") | v2 rendered; v3 rework in progress in the cloud |
| Client approval of storyboard + keyframes + proof of concept | **Pending** |
| Full production of the 26 shots, master, game-optimised encode, integration | Not started (waits for approval) |

## Folder map

- `aaa/story/storyboard_final.md`: the shot-by-shot storyboard (frames, audio events, camera, technique, transitions, colour script, sync map, render budget, hand-off rules). Start here.
- `aaa/rnd/pipeline_decision.md`: the rendering recipe (MapSet asset contract, R25 shading, Eevee recipe, gates G1-G8, QA, time estimates).
- `aaa/lib/`: the embroidery library (read `README.md`). Baked MapSets were NOT copied (1.8 GB); re-bake them with the commands in the README (faster on a strong CPU).
- `aaa/prod/<shot>/`: the scripts, shot JSON and READMEs that built each keyframe / the proof of concept (renders were not copied).
- `aaa/prod/handoff/`: the exact menu hand-off frame f1983 and the chrome mattes (pixel-identical to the live menu outside the blank card).
- `aaa/assets/`: extracted textures, realm-tinted figure cards, game models (OBJ), extraction scripts (`work/`).
- `intro/`: the three AI tapestry panels (p1_oath, p3_death, p6_ruin) and the crown cut-out. These cannot be regenerated; keep them.
- `ex/`, `ents.pkl`, `pck.py`, `ext.py`: first extraction of the game textures from `index.pck`.
- `keyframes/`: current keyframes as JPEG (reference for continuity).

## Running it locally (Omarchy / Arch + NVIDIA)

1. `bash intro/production/setup_omarchy.sh` installs Blender 4.1.1 (official build: legacy Eevee + OptiX), a Python venv, Node deps, and recreates the absolute script paths as symlinks.
2. `source intro/production/.venv/bin/activate`
3. On the GPU machine, drop the `xvfb-run -a -s "-screen 0 1920x1080x24"` prefix that the cloud scripts used: run `blender -b ...` directly so Eevee uses the NVIDIA GPU.
4. In Cycles scenes, enable the GPU: `bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'OPTIX'`, then set `scene.cycles.device = 'GPU'`. Blender 4.1 also has OpenImageDenoise built in.
5. Re-bake the library caches (see `aaa/lib/README.md`), then re-render any shot from its folder's README.

## Continue with Claude Code on this machine

```
cd chronica-ipad
git fetch origin && git checkout claude/inspiring-bardeen-6ur170
claude remote-control
```
Then ask: "Read intro/production/HANDOFF.md and continue the Chronica intro production." The session appears in the Claude Code app.

## Final deliverables still to produce (after approval)

- Master 2560x1440, 30 fps, 1984 frames, muxed with `aaa/audio/audio_master_1984f_s16.wav` (ffprobe both streams = 66.133 s).
- Game-optimised encodes: H.264 + AAC 1920x1080 (~2-2.5 Mb/s) and VP9 + Opus WebM for the HTML overlay; optional Theora `.ogv` for Godot.
- Remotion project for the edit (`aaa/tools/remotion-test` shows the working config).
- Contact sheet, QA report (duration, fps, no black/duplicate frames, menu-match diff).
- Integration: `aaa/game/intro_overlay_snippet.html` (tested design: gate the engine start until the video ends; the last frames equal the live menu, then a 0.9 s dissolve).
