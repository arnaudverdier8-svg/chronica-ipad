"""Art-directed placement of the fog quilts (v2: two coherent fronts closing in from the frame ends, densest at the ends and thinning inward as
chains of ever smaller puffs along the bottom margin and over the border; the mid-strip stays clear; no stand-alone singletons).
Positions are in STRIP coordinates (u along the chronicle in mm, v across: 0 = the top edge, 400 = the bottom edge; outside that range the
quilt lies on the walnut) and are mapped to the table by geometry.strip_to_world."""
# (sprite, u, v, angle_deg, mm_per_sprite_px, flip, gain)
QUILTS = [
    # --- the far left: the fog has already swallowed the start of the chronicle (the capital and the road stay readable)
    ('cloud_puff_6', 150, 372, -8, 0.95, False, 0.50),
    ('cloud_puff_3', 318, 424, 6, 0.85, True, 0.50),
    ('cloud_puff_4', 78, 240, -5, 0.80, True, 0.48),
    ('cloud_puff_2', 140, 28, 10, 0.78, False, 0.48),
    ('cloud_puff_5', 470, 452, -4, 0.72, False, 0.52),
    ('cloud_puff_7', 300, -34, 8, 0.58, True, 0.50),
    ('cloud_puff_8', 30, 100, 4, 0.62, False, 0.48),
    # chain inward (bottom margin, overlapping the cloth edge) and over the top border: smaller and smaller
    ('cloud_puff_1', 590, 436, 3, 0.52, False, 0.54),
    ('cloud_puff_3', 735, 428, -7, 0.44, True, 0.55),
    ('cloud_puff_7', 868, 438, 5, 0.34, False, 0.58),
    ('cloud_puff_5', 640, -30, 6, 0.40, True, 0.54),
    ('cloud_puff_2', 790, 8, -8, 0.30, False, 0.56),
    # --- the far right: the fog closes in from below; the top border and the thread stay clear
    ('cloud_puff_6', 3230, 392, 4, 0.74, True, 0.53),
    ('cloud_puff_7', 3395, 372, -10, 0.70, False, 0.53),
    ('cloud_puff_4', 3540, 408, 6, 0.74, False, 0.50),
    ('cloud_puff_3', 3640, 352, -6, 0.66, True, 0.48),
    ('cloud_puff_2', 3330, 462, -3, 0.66, False, 0.52),
    ('cloud_puff_5', 3480, 470, 4, 0.66, True, 0.50),
    ('cloud_puff_8', 3085, 414, -5, 0.50, False, 0.55),
    ('cloud_puff_1', 2945, 428, 6, 0.40, True, 0.56),
    ('cloud_puff_5', 2815, 436, -4, 0.32, False, 0.58),
    ('cloud_puff_3', 2700, 432, 3, 0.25, True, 0.60),
]
