"""Paths, the PX ladder, frame<->time and storyboard/audio event lookup.  No hard-coded absolute paths:
everything is derived from this file's location (aaa/lib/chron/config.py)."""
import os, json, math
from functools import lru_cache

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # aaa/lib
AAA = os.path.dirname(LIB)                                            # aaa
SCRATCH = os.path.dirname(AAA)                                        # scratchpad
CACHE = os.path.join(AAA, 'cache')
MAPS = os.path.join(CACHE, 'maps')                                    # MapSets live here: MAPS/<sheet>/
HINTS = os.path.join(LIB, 'hints')
PANELS = {k: os.path.join(SCRATCH, 'intro', f'{k}.png') for k in ('p1_oath', 'p3_death', 'p6_ruin')}
PALETTE = os.path.join(AAA, 'style', 'palette.json')
FONTS = os.path.join(AAA, 'style', 'fonts')

FPS = 30
OUT_W, OUT_H = 2560, 1440
PX_BAKE = 10.0                       # px/mm of level 0 for panels
PX_LADDER = (10.0, 5.0, 2.5, 1.25)   # level 0..3
SRC_PX = 5.0                         # AI panels are 5 px/mm (2752 x 1536 px = 550.4 x 307.2 mm)

# material ids (contract)
LINEN, WOOL, SILK, METAL, INK, CORD, WALNUT, PARCH, FELT = 0, 1, 2, 3, 4, 5, 6, 7, 8


def frame_of(t_s):
    return int(math.floor(t_s * FPS + 1e-9))


def time_of(frame):
    return frame / FPS


@lru_cache(None)
def palette():
    return json.load(open(PALETTE))


@lru_cache(None)
def storyboard():
    return json.load(open(os.path.join(AAA, 'story', 'storyboard_final.json')))


@lru_cache(None)
def words():
    return json.load(open(os.path.join(AAA, 'words.json')))


def event(name):
    """'word:crown' -> first frame of that word (from words.json); 'shot:S09' -> (start, end) frames."""
    kind, _, key = name.partition(':')
    if kind == 'shot':
        for s in storyboard()['shots']:
            if s['id'] == key:
                return s['start_frame'], s['end_frame']
        raise KeyError(name)
    if kind == 'word':
        w = words()
        lst = w.get('words', w) if isinstance(w, dict) else w
        for it in lst:
            txt = str(it.get('word', it.get('text', ''))).strip(".,;:!?'\"").lower()
            if txt == key.lower():
                t = it.get('start', it.get('t0', it.get('s')))
                return frame_of(float(t))
        raise KeyError(name)
    raise KeyError(name)


def sheet_dir(sheet):
    return os.path.join(MAPS, sheet)
