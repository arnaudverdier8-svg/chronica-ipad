"""Piece material palette = game TAPISSERIE pieces merged with the MILLEFLEURS (default palette) overrides
(decoded view/palettes.gd). sRGB hex."""
TAP = {'wood': '#6E5032', 'wood_dark': '#46301C', 'plank': '#A68A5E', 'stone': '#CFC3AA', 'stone_dark': '#8A7F6C', 'rock': '#8C8070',
       'plaster': '#E3D5B8', 'roof': '#8C5236', 'thatch': '#B8975A', 'slate': '#4B5862', 'skin': '#D8B48E', 'hair': '#4A3420',
       'cloth': '#BBA47C', 'cloth_dark': '#4E4436', 'leather': '#74502F', 'metal': '#B3B1A6', 'metal_dark': '#68675F', 'gold': '#B49248',
       'window': '#2E2216', 'fire': '#D9822B', 'black': '#2E2012', 'leaf': '#6E7A42', 'crop': '#7E8A48', 'dirt': '#7D5E3C',
       'hay': '#C9A65E', 'horse': '#7E5132', 'horse_dark': '#3F2B1B', 'white': '#E8D8BB', 'iron': '#6E5248', 'water': '#4A6372',
       'wool': '#E8D8BB', 'roof_tile': '#BB6742', 'roof_tile_old': '#6E4033', 'roof_thatch': '#C29A58', 'roof_thatch_old': '#94805A',
       'roof_slate': '#525D68', 'roof_shingle': '#6B5A48', 'roof_lead': '#7C8182', 'roof_moss': '#6E7352', 'roof_civic': '#BB6742',
       'roof_hall': '#3F6E6A', 'thatch_store': '#8E7A55', 'lead': '#7C8182', 'earth': '#6A5338'}
MF = {'roof': '#BB6742', 'slate': '#2E4962', 'rag': '#8A332B', 'gold': '#CD9E3D', 'leaf': '#4D774A', 'crop': '#769550',
      'water': '#357588', 'plaster': '#DFCFB6', 'bone': '#DFCFB6', 'white': '#E4D5BD', 'wool': '#E4D5BD', 'thatch': '#C6A05E',
      'hay': '#D2AB60', 'stone': '#CEC5B8', 'stone_dark': '#8D8579', 'rock': '#8E8579', 'cloth': '#C4AD8D', 'cloth_dark': '#433933',
      'metal': '#B3B0A9', 'metal_dark': '#6A6861'}
PAL = dict(TAP); PAL.update(MF)
REALM = {'gold': '#D49B30', 'red': '#A3302B', 'blue': '#4C79B0', 'green': '#46A085'}
OUTLINE = '#3B2615'   # game piece outline brown


def col(name, realm='gold'):
    if name in ('team', 'blazon'): return REALM[realm]
    if name == 'team_dark': return '#7A5A1E' if realm == 'gold' else '#6E2420'
    return PAL.get(name, '#8A7A60')
