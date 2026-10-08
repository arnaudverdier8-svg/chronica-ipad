import re
def group_of(rel):
    d,n=rel.split('/'); n=n[:-4]
    if d=='figures': return 'figure_maps' if (n.endswith('_normal') or n.endswith('_mask')) else 'units'
    if d=='icons':
        if n.startswith('unit_'): return 'units'
        if n in('icon','icon_source'): return 'branding'
        return 'icons'
    if d=='table_clouds': return 'clouds'
    if d=='table_glyphs': return 'icons'
    if d=='table_heraldry': return 'heraldry'
    if d=='table_tapestry': return 'branding'
    if d in('table_carved','table_backgrounds','table_wood'): return 'ornaments'
    if d=='table_parchment':
        if n in('rule_line','rule_orn','plaque'): return 'ornaments'
        return 'panels'
    if d=='table_buttons':
        return 'panels' if n.startswith('menu_item') else 'ui_widgets'
    if d=='ui':
        if n.startswith('crest_'): return 'heraldry'
        if n in('logo_chronica','game_over_defeat','game_over_victory','menu_veil','topbar'): return 'branding'
        if n.startswith('panel') or n.startswith('card_'): return 'panels'
        if n=='separator': return 'ornaments'
        return 'ui_widgets'
    if d=='ui_embroidery_v2':
        if n.startswith('vignette'): return 'branding'
        if n.startswith('panel'): return 'panels'
        return 'ui_widgets'
    if d=='ui_linen':
        if n in('millefleurs',): return 'branding'
        if n.startswith('shield') or n.startswith('lion_') or n.startswith('banner_'): return 'heraldry'
        if n in('orn_left','orn_right','groove','satin_or','sep_h','sep_v','plaque','frame'): return 'ornaments'
        if n in('panel','panel_flat','modal'): return 'panels'
        if n.startswith('phase_') or n.startswith('g_') or n=='gear': return 'icons'
        return 'ui_widgets'
    return 'misc'
