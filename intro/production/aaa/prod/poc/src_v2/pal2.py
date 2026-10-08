"""v2 palette of the board bake: muted wool dyes matched to the live menu board (sampled in OKLab per terrain, data/menu_palette.json)
and the game's own UI colours (assets/models/game_palette.json: SAPIN, SAPIN_CLAIR, DENIM, OCRE, BRUN ...).
Director note 1: olive / sapin greens, dark denim sea, desaturated wheat, dull ochre hills; nothing lime, nothing candy-orange.
Hex strings are sRGB. The film-level calibration (class grade, data/class_grade.json) trims these against the menu at f1782."""

# satin coupon dyes (before light): the lit satin reads ~10-15 % lighter than the dye
DYE = {'forest': ('#5E7753', 0.08), 'plains': ('#928A65', 0.05), 'farm': ('#8B8658', 0.06), 'hills': ('#A8855A', 0.07), 'mountain': ('#9C968A', 0.04), 'quarry': ('#A39373', 0.05)}
SEA = '#285B83'
LAKE = '#3C7998'
PAD_CHROMA = 0.45      # padding felt: same hue as the coupon, chroma x0.45 (undyed felt does not pre-announce the final colour)
PAD_L = 0.64           # and half-way to a pale felt lightness (OKLab L)

# crop plots (laid + couched rows)
PLOT_GREENS = ['#587637', '#68853F', '#4C6734', '#617D3B']
PLOT_WHEAT = ['#C2A754', '#B79A4A']
PLOT_PLOUGH = ['#7A5E3E', '#6E5438']
FENCE = '#4B3522'
STOOK = '#C9A24E'
STOOK_O = '#5B4220'

# hills / mountains
MOUND = [('#B98B52', '#D6AC72'), ('#B0814B', '#CFA56A'), ('#C09860', '#DDB87E')]
MOUND_O = '#58391C'
PEAK_LIT, PEAK_SHADE, PEAK_O = '#E2DDCF', '#9C978B', '#3A3029'
ROCK = ['#8C8070', '#9A8E7C']

# trees (sapin = dark pine, sapin clair, broadleaf olive) and wood
TREE = {'spruce': ('#223A2B', '#33563A'), 'fir': ('#263F2D', '#3A5E3C'), 'round': ('#3E5530', '#55703A')}
TRUNK = '#4A3420'
TUFT = '#5D6C3C'

# sea / cloth furniture
WAVE = '#BFD0D4'
GRID = '#5F86A6'
SEAM = '#C9BE9F'
COAST = '#3A2A1C'
DASH = '#33271B'
GOLD = (0.815, 0.515, 0.141)         # metal_gold_f0 (linear): couched realm borders
REALM_TIE = {'gold': '#4A2A14', 'red': '#9A302B'}
RIVER = ['#4B8CA8', '#5C9DB9', '#4B8CA8']
RIVER_TIE = '#2E5C78'
INK = '#3E3025'                      # iron-gall underdrawing (period red-brown/black)
LINEN_BASE = '#D6C6A3'               # palette.linen #D4BE98 / linen_hi #E6D7B6, pale flax rather than kraft
