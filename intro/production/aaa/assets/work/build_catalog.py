import json,os,glob,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from descs import D,UNIT,ICON_UNIT
from groups import group_of
A='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/assets'
I='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/intro'
meta={os.path.relpath(m['out'],A+'/tex')[:-4]:m for m in json.load(open(A+'/work/extract_meta.json'))}
FIGJ={}
for u in UNIT: FIGJ[u]=None
ICONS={
'building_barracks':'castle gatehouse with red banners','building_forge':'smithy with roaring hearth and anvil','building_granary':'thatched granary with wheat','building_guild':'half-timbered guildhall with blue lion banner','building_library':'stone library with arched windows','building_market':'market stall with navy/cream striped awning','building_stable':'wooden stable with horse looking out','building_walls':'stone curtain wall with towers','building_workshop':'half-timbered workshop with gear',
'den':'rocky cave lair (goblin den)','ruin':'overgrown ruined stone arch',
'job_bridge':'wooden bridge','job_clear':'axe in a stump with a sapling (forest clearing)','job_farm':'wheat sheaf and hoe','job_fishery':'fish and net','job_gather':'basket of berries and mushrooms','job_goldmine':'mine mouth with gold-laden cart','job_great_work':'arch under construction with scaffold','job_lumber':'axe in tree stump','job_mine':'timbered mine entrance and pick','job_ore_pit':'open pit of dark ore','job_outpost':'wooden post with blue lion banner','job_pasture':'woolly sheep','job_quarry':'pickaxe and cut stone','job_repair':'hammer on planks','job_road':'cobbled road receding','job_settle':'cottage with blue flag (found a village)','job_siege':'siege engine','job_study':'open book with quill','job_watchtower':'wooden watchtower',
'level_0':'camp of striped tents with pennants (settlement level 0)','level_1':'thatched village cottages (level 1)','level_2':'town with red roofs and church (level 2)','level_3':'walled castle-town with red roofs and towers (level 3)',
'res_food':'wheat sheaf','res_gold':'stack of gold coins','res_iron':'iron ingots','res_knowledge':'open book','res_stone':'cut stone blocks','res_wood':'stacked logs',
'stat_attack':'sword','stat_crown':'gold crown with red velvet cap','stat_defense':'navy shield with gold lion','stat_diplomacy':'clasped hands (navy and red cuffs)','stat_housing':'half-timbered house','stat_hp':'red quilted heart','stat_moves':'winged boot','stat_time':'hourglass','stat_work':'crossed hammers',
'tech_archery':'bow and arrow','tech_architecture':'stone arch with compasses','tech_chivalry':'plumed great helm with pennant','tech_engineering':'gear with compasses','tech_guilds':'crossed tools with ribbon','tech_husbandry':'horse head with wheat','tech_masonry':'mallet on stone block','tech_mining':'pickaxe and crystals','tech_siegecraft':'trebuchet','tech_trade':'scales with goods','tech_writing':'scroll and quill'}
ICONUSE={'stat_crown':'"one crown" (0-8s) insert, crown motif','stat_time':'"the wars lasted a hundred years" (28-32s) hourglass','stat_diplomacy':'oath / sworn alliance (9-13s)','ruin':'"cities fell to ruin" (32.7-34.3s) map marker','job_road':'"roads were swallowed by the forest" (35-37s) map marker','job_clear':'"roads swallowed by the forest" (35-37s)','res_wood':'forest beat (35-37s)','job_settle':'"one village" (50.8-54.9s)','level_0':'"one village" growth sequence start (50.8-54.9s)','level_1':'village growth sequence','level_2':'village growth sequence','level_3':'village growth sequence end / "made whole again" (46-50s)','tech_writing':'"what will the chronicles say" (56-62s)','res_knowledge':'chronicle / blank page (50.8-62s)','job_study':'chronicle (56-62s)','stat_defense':'realm defence, heraldic insert','building_walls':'walls / realm borders (38-44s)','job_outpost':'"one banner" (50.8s)','tech_chivalry':'war montage (28-32s)','tech_siegecraft':'war montage (28-32s)','stat_attack':'war montage (28-32s)'}
GLY={'g_book':'open illuminated book','g_boot':'laced leather boot','g_check':'gold check mark','g_close':'gold X','g_compass':'gold/navy compass rose','g_gear':'gold gear','g_hourglass':'brass hourglass','g_laurel':'gold laurel wreath','g_lute':'lute','g_rest':'crescent moon over navy drape (rest)','phase_dawn':'round brass medallion: sunrise over the sea, navy sky','phase_day':'round brass medallion: golden sun on navy','phase_dusk':'round brass medallion: sunset, red sky over the sea','phase_night':'round brass medallion: crescent moon and stars on navy','gear':'small gear'}
GLYUSE={'g_hourglass':'"a hundred years" (28-32s)','g_compass':'"what lay beyond their own borders" (37.9-44.5s)','g_book':'"the chronicles" (56-62s) / blank page','g_laurel':'victory / "made whole" (46-50s)','phase_dusk':'"the world grew dark" (37.9-44.5s): dusk->night medallion sequence','phase_night':'"the world grew dark" (37.9-44.5s)','phase_dawn':'"now every ruler..." new dawn (46s)','phase_day':'opening golden age (0-13s)'}
def entry(rel):
    m=meta[rel]; d,n=rel.split('/'); g=group_of(rel+'.png')
    kind=desc=use=None
    if rel in D: kind,desc,use=D[rel]
    elif d=='figures':
        u,pose=None,None
        for k in UNIT:
            if n.startswith(k+'_'): u=k
        rest=n[len(u)+1:]; pose,mp=rest.split('_')
        kind={'albedo':'figure_albedo','normal':'figure_normal','mask':'figure_mask'}[mp]
        base=f'Embroidered figure card "{u}", {pose} pose - {UNIT[u]}. Single full-figure image (NOT a frame strip); brown outline cord, satin-stitch fill.'
        if mp=='albedo': desc=base+' RGBA, alpha = coverage (cut at 0.5). Team-livery zones are neutral grey (tint with figure_tint.py).'; use='Animate soldiers in the war montage: idle->strike key-pose swap + 0.12s lunge (game timing), squash/stretch, parallax; tinted variants in tex_tinted/.'
        elif mp=='normal': desc=base+' Normal map: decoded from KTX2/UASTC RG-as-RA; Z reconstructed; RGB = n*0.5+0.5 (OpenGL Y-up), alpha copied from albedo.'; use='Relight the stitched relief (raking candle light, flicker) in the compositor or as a Blender plane material.'
        else: desc=base+' Half-res mask: R = team livery zones, G = shield field (game stitches a procedural heraldic charge here), B = thread sheen (specular), A = brown outline cord.'; use='Realm recolouring (R), custom shield charges (G), thread glints (B). Upscale with cv2 per-channel, never PIL RGBA resize (premultiplies by A).'
    elif d=='icons' and n.startswith('unit_'):
        u=n[5:]; kind='unit_icon'; desc=f'Embroidered bust portrait icon (256x256): {ICON_UNIT[u]}; richer, more painterly patch style than the figure cards.'; use='Character medallions / roll-call inserts in the war montage (28-32s) or "every ruler" (46-50s); max ~2x upscale.'
    elif d=='icons':
        kind='icon'; desc=f'Embroidered game icon (128x128): {ICONS.get(n,n)}.'; use=ICONUSE.get(n,'Map / HUD marker; low value (128px, ~2x upscale max).')
    elif d in('table_glyphs',) or (d=='ui_linen' and (n.startswith('g_') or n.startswith('phase_') or n=='gear')):
        kind='glyph'; desc=f'{"Brass/gold embroidered glyph" if d=="table_glyphs" else "Older linen-set glyph (small)"} ({m["w"]}x{m["h"]}): {GLY.get(n,n)}.'; use=GLYUSE.get(n,'UI glyph; low cinematic value.') if d=='table_glyphs' else 'Low (small, older linen UI style).'
    elif g=='panels':
        kind='panel'
        tex='parchment' if ('parchment' in rel or 'card' in n or 'tooltip' in n or 'menu_item' in n or 'plaque' in n) and 'faction' not in n and 'card_job' not in n else ('linen' if 'linen' in n or d=='ui_linen' else 'dark linen / walnut')
        if n=='menu_card': desc='Blank parchment card in a walnut frame with brass corner studs (260x340), portrait.'; use='"One blank page" (53-55s) - blank parchment to write on; scale <=2x.'
        elif n=='panel_parchment': desc='Cream linen panel with gold rope frame (256x256, 9-slice).'; use='Blank page / caption plate (9-slice).'
        else: desc=f'9-slice UI panel/card ({tex}) {m["w"]}x{m["h"]}.'; use='Caption / subtitle plate background at most; low.'
    elif g=='ui_widgets':
        kind='ui_widget'; desc=f'Interactive UI control ({n}), {m["w"]}x{m["h"]}.'; use='None (pure UI). Round discs/recenter medallions could back a round icon at most.'
    else:
        kind='misc'; desc=rel; use=''
    return dict(name=rel,path=m['out'],w=m['w'],h=m['h'],kind=kind,group=g,description=desc,cinematic_use=use,
                source=m['src'],codec=m['codec'])
cat=[entry(r) for r in sorted(meta)]
# realm-tinted figure cards
for p in sorted(glob.glob(A+'/tex_tinted/*.png')):
    n=os.path.basename(p)[:-4]; im=Image.open(p)
    cat.append(dict(name='tinted/'+n,path=p,w=im.width,h=im.height,kind='figure_tinted',group='units',description=f'Figure card {n} recoloured with the realm colour (Palettes border colour) using the in-game formula (figure_tint.py).',cinematic_use='Drop-in soldiers for war montage / realm armies; same pose pairs as the source albedo.',source='derived',codec='png'))
# 3D models
for r in json.load(open(A+'/models/models.json')):
    cat.append(dict(name='model3d/'+r['name'],path=r['obj'],w=None,h=None,kind='model3d',group='models3d',
        description=f'Low-poly game model decoded from res://.godot/imported/{r["name"]}.glb-*.scn (Godot 4 binary ArrayMesh): parts {r["parts"]}, {r["verts"]} verts / {r["tris"]} tris, flat-colour materials {list(r["materials"])} (MTL recoloured to the game TAPISSERIE palette, linear Kd). Godot units, Y-up; bbox {r["bbox_min"]}..{r["bbox_max"]}.',
        cinematic_use=('Blender map scene: settlements/castles for "cities fell to ruin", "one village" growth (settle_0 -> settle_3), realm borders (walls_*).' if r['name'].startswith(('settle','walls','capital','ruin','great_work','watchtower')) else 'Blender scene dressing; needs an embroidery/stitch material to match the tapestry look (in-game piece.gdshader adds stitch relief).'),
        source='res://(glb import)',codec='obj'))
# existing panels + v1 plates
PAN=[('intro/p1_oath','p1_oath.png','tapestry_panel',
 'v1 AI-generated tapestry panel, 2752x1536 RGB. Needle-painted embroidery on cream linen: old crowned king (purple robe, ermine) on a carved throne beneath a purple banner (crown + two gold lions); four lords at a long white-clothed table lay hands on a sword (the oath); goblets, bread, candles. The lords\' tunics are gold/red/blue/green with badges that match crest_builders/legion/merchants/nomads. QUALITY: high - clean anatomy, coherent hands, consistent long-and-short stitch texture, no obvious AI glitches at 1:1. STYLE: rich, illustrative needle-painting with realistic faces - more refined than Bayeux and finer than the in-game figure cards (which use thick brown cords and flat fills); palette (navy/gold/cream + faction colours) matches the game menu art well.',
 'Beats 0.14-8.28s ("one realm, one table, one oath, one crown") and 9.22-13.42s ("raised their cups and swore") - note nobody raises a cup; they touch a sword (cups present on the table). Only 1.075x the 2560x1440 master: Ken Burns push-in limited to ~7% before upscaling; tight insets (king face, crown) are 3-4x upscales and will soften.'),
('intro/p3_death','p3_death.png','tapestry_panel',
 'v1 AI-generated tapestry panel, 2752x1536 RGB. The king lies in state on a stone bier draped in purple, crown on, hands clasped on a sword, ermine cape, tasselled pillow; tall candles; black canopy with gold trim; navy field framed by cream linen margins. QUALITY: high, convincing thread texture and lighting. STYLE: consistent with p1 (same king design: white beard, crown, purple/ermine) - good continuity.',
 'Beat 14.88-17.76s ("Then the king died and left no heir"); slow push-in or pan along the body; candle flicker overlay (candle_left/right). Same 1.075x resolution limit.'),
('intro/p6_ruin','p6_ruin.png','tapestry_panel',
 'v1 AI-generated tapestry panel, 2752x1536 RGB. A walled city/castle burning: crumbling towers, flaming half-timbered houses, black swirling smoke, crows, banded red/purple sky, torn red banner on a broken spear in the foreground, cream linen margin. QUALITY: high; flames and smoke are well stylised as embroidery. STYLE: consistent with p1/p3 (same linen ground and stitch scale).',
 'Beats 28.16-31.84s ("wars lasted a hundred years and ended nothing") and 32.74-34.28s ("Cities fell to ruin"); animate flames/smoke with warps, drifting embers, crows. Same 1.075x limit.'),
('intro/p1_empty','p1_empty.png','tapestry_panel_derived',
 'v1 derivative of p1_oath with the king removed: the throne interior is replaced by a flat navy procedural fill with a gold outline; a visible blurred smear remains where the crown/head was (just below the banner point, above the chair back). QUALITY: NOT shippable as-is - the smear and the flat, unstitched chair break the illusion.',
 'Intended for 18.72-26.64s ("looked at the empty chair"). Needs repair: re-stitch the chair back procedurally (stitch shader / hatch fill) and clean the smear, or crossfade only briefly / crop below the smear.'),
('intro/war_bg','war_bg.png','backdrop',
 'v1 procedural stitched backdrop 2752x1536: banded purple->red->orange dusk sky in horizontal satin stitches, dark blue hills with gold outline, olive grass field. QUALITY: decent but plain; reads as stitched.',
 'Backdrop for the figure-card war montage (28-32s); place tinted figure cards on the grass line.'),
('intro/map_albedo','map_albedo.png','map_texture',
 'v1 stitched map texture 4096x2304: green felt field with directional stitches, blue river and sea corner, dark green forest blobs, wheat fields, dashed roads, crossroads circle, walnut border. QUALITY: serviceable; simpler than the game\'s own terrain shading.',
 'Blender map scene (v1 map_scene.py) for the map beats (35-55s); combine with decoded 3D models and cloud kit.'),
('intro/clouds','clouds.png','atlas',
 'v1 atlas 1600x400 of the game cloud textures laid out on dark green (superseded by tex/table_clouds/*).','Use tex/table_clouds instead.'),
('intro/crown','crown.png','prop',
 'v1 cut-out 256x188 of an embroidered crown (gold, red velvet cap, jewels), transparent.','"One crown" insert / crown floating over the empty chair (18-26s); small - <=2x.')]
for name,f,kind,desc,use in PAN:
    im=Image.open(I+'/'+f)
    cat.append(dict(name=name,path=I+'/'+f,w=im.width,h=im.height,kind=kind,group='tapestry_panels',description=desc,cinematic_use=use,source='v1 (scratchpad/intro)',codec='png'))
json.dump(cat,open(A+'/catalog.json','w'),indent=1,ensure_ascii=False)
import collections
print(len(cat),collections.Counter(c['kind'] for c in cat))
