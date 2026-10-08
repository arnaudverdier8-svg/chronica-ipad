"""100 % crops of key regions of the final 8-bit keyframe (no resampling) + a review contact sheet."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
im = cv2.imread(OUT + '/keyframe_f1319_2560x1440_8bit.png')
CROPS = {
    'c01_left_end_realm_fog': (0, 520, 880, 480),
    'c02_oath_with_king': (330, 560, 640, 400),
    'c03_death_panel_border_lions': (880, 560, 560, 400),
    'c04_empty_chair_war_hole_field': (1380, 540, 700, 420),
    'c05_burn_through_ruin_fog': (1900, 560, 660, 420),
    'c06_gold_thread_glint': (2130, 440, 430, 260),
    'c07_top_edge_fringe_unravelling_lions': (1100, 500, 700, 240),
    'c08_bottom_edge_weft_quilts': (1300, 780, 720, 260),
    'c09_table_edge_falloff': (0, 1000, 1280, 440),
}
os.makedirs(OUT + '/crops_100pct', exist_ok=True)
for k, (x, y, w, h) in CROPS.items():
    cv2.imwrite(f'{OUT}/crops_100pct/{k}.png', im[y:y + h, x:x + w])
    print(k, (x, y, w, h))
