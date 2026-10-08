"""Art-directed placement of the fog quilts.  Positions are in STRIP coordinates (u along the chronicle in mm, v across: 0 = the top
edge, 400 = the bottom edge; outside that range the quilt lies on the walnut) and are mapped to the table by geometry.strip_to_world."""
# (sprite, u, v, angle_deg, mm_per_sprite_px, flip, gain)
QUILTS = [
    # --- the far left: the fog has already swallowed the start of the chronicle (the capital and the road stay readable)
    ('cloud_puff_6', 150, 375, -8, 0.95, False, 0.62),
    ('cloud_puff_3', 330, 428, 6, 0.85, True, 0.58),
    ('cloud_puff_2', 130, 18, 10, 0.80, False, 0.58),
    ('cloud_puff_4', 70, 235, -5, 0.80, True, 0.60),
    ('cloud_puff_5', 470, 452, -4, 0.72, False, 0.55),
    ('cloud_puff_7', 300, -34, 8, 0.58, True, 0.55),
    ('cloud_puff_8', 20, 90, 4, 0.60, False, 0.55),
    # --- creeping over the margins, mid-left (top border) and under the strip
    ('cloud_puff_1', 1000, 10, 5, 0.62, False, 0.55),
    ('cloud_puff_7', 1135, -34, -12, 0.46, False, 0.52),
    ('cloud_puff_8', 1330, 424, -12, 0.45, True, 0.52),
    ('cloud_puff_2', 1770, 418, 7, 0.42, False, 0.52),
    # --- right of centre, bottom margin
    ('cloud_puff_5', 2620, 412, 3, 0.60, False, 0.55),
    ('cloud_puff_3', 2760, 444, 8, 0.55, True, 0.52),
    ('cloud_puff_4', 2930, 428, -6, 0.52, False, 0.52),
    # --- the far right: the fog closes in from below; the top border and the thread stay clear
    ('cloud_puff_6', 3230, 392, 4, 0.74, True, 0.58),
    ('cloud_puff_7', 3395, 372, -10, 0.70, False, 0.60),
    ('cloud_puff_4', 3540, 408, 6, 0.74, False, 0.58),
    ('cloud_puff_3', 3640, 352, -6, 0.66, True, 0.56),
    ('cloud_puff_2', 3330, 460, -3, 0.66, False, 0.52),
    ('cloud_puff_5', 3480, 470, 4, 0.66, True, 0.52),
]
