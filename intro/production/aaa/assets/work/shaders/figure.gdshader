shader_type spatial;
// Une figurine en CARTE BRODÉE (view/figures.gd, assets/figures/) : UN quad,
// UN appel de dessin, la broderie dans trois textures dessinées et brodées
// par tools/embroider/ (docs/ART.md §4.1). Même lumière, même nuit, même
// voile et même profondeur que les pièces (piece.gdshader) :
//   - la carte se tient DEBOUT, cisaillée comme elles (figure.gdshaderinc) ;
//   - elle est éclairée comme une broderie couchée (pc_relief) : la normale
//     de la carte (x à droite, y en haut, z vers l'œil) passe au monde par
//     le repère du nœud (miroir et chute compris), puis pc_relief ;
//   - la nuit, le plancher de lanterne des figurines (l'émission `figure`
//     de piece.gdshader), SAUF sur le cordon (A du masque) : il reste brun,
//     non éclairé et sans voile, comme la coque des pièces (pc_hull_color).
//
// LES TEXTURES (sans source_color : on les lit telles quelles, on calcule
// en sRGB comme les pièces, puis st_albedo()) :
//   albedo_tex  RGB couleur du fil (zones du peuple en gris de valeur g0),
//               A couverture (découpe à 0,5 ; ALPHA_SCISSOR) ;
//   normal_tex  RG = n.xy × 0,5 + 0,5 (z refait ici : importée en « carte de
//               normales », RG seulement) ;
//   mask_tex    R peuple, G champ du meuble, B brillance du fil, A cordon.
//
// LE PEUPLE : col = mix(albédo, ton × gris / g0, R) (le gris garde fils et
// ombres ; g0 est calibré pour que la médiane éclairée tombe sur le ton).
// LE MEUBLE : pc_charge dans le repère « arms » de la pose (p = Mi × (texel −
// o), demi-largeur 1, y en haut), là où G : crème (brique sur le champ d'or),
// liseré brun, un léger bombé ; il se fond dans le champ quand l'écu tombe
// sous une dizaine de pixels (comme le blason des pièces). En miroir, p.x est
// retourné : le meuble garde son sens.
//
// L'anticrénelage alpha (alpha to coverage) n'existe pas en gl_compatibility
// (Godot 4.7 : BLEND_MODE_ALPHA_TO_COVERAGE « ne fait rien ») : le bord est
// une découpe nette ; le cordon brun, épais et sombre, la rend propre.
//
// COÛT par pixel : trois lectures de texture, 0 hash ; sur le champ de l'écu
// seulement, trois évaluations de pc_charge (le meuble et sa pente).

render_mode skip_vertex_transform, cull_disabled, diffuse_lambert, specular_disabled, shadows_disabled;
// Le pochoir : la carte marque ses pixels (bit FIG_STENCIL = 4) ; le fantôme
// de la sélection (select_ghost.gdshader), dessiné sans test de profondeur
// pour se voir à travers murs et futaies, ne passe pas sur une figurine
// (sinon il barrait le visage de l'unité choisie, dont la carte couchée
// vers le nord croise le bord nord de sa case).
stencil_mode write, compare_always, 4;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"
#include "res://view/shaders/figure.gdshaderinc"

uniform sampler2D albedo_tex : filter_linear_mipmap, repeat_disable;
uniform sampler2D normal_tex : filter_linear_mipmap, repeat_disable;
uniform sampler2D mask_tex : filter_linear_mipmap, repeat_disable;
// Le ton du peuple (sRGB, Figures.card_tone) et le gris de référence g0.
uniform vec3 team = vec3(0.6, 0.23, 0.14);
uniform float g0 = 0.65;
// Le meuble (pc_charge : 0 aucun) et sa couleur (sRGB).
uniform int charge = 0;
// Le symbole de la TROUPE sur l'écu flottant (Figures.TROOP_SYMBOL ; 0 :
// le meuble du peuple).
uniform int troop = 0;
// L'unité choisie (Figures.material(…, selected)) : son écu flottant luit à
// la couleur de son peuple — un anneau vif autour du cordon, qui bat
// doucement — pour qu'on sache d'un coup d'œil quelle troupe on tient.
uniform bool selected = false;
uniform vec3 charge_col = vec3(0.91, 0.847, 0.733);
// La carte (px) et le repère du meuble : origine o (px) et inverse de la
// matrice [ex ey] (colonnes, px -> repère) rangée (m00, m10, m01, m11).
uniform vec2 card_size = vec2(416.0, 528.0);
uniform vec2 arms_o = vec2(0.0);
uniform vec4 arms_inv = vec4(0.0);

global uniform float g_night;
// « Cacher les unités » (Pieces.set_units_hidden, bouton et touche U) : les
// figurines s'effacent, leur écu flottant reste — on voit la case entière et
// où se tient chaque troupe.
global uniform float g_units_hide;
global uniform vec4 g_veil;

// Vers le soleil du jour (Vis.PHASE_LIGHT « day » : hauteur 42°, lacet
// 225°) : le reflet de soie et le cordon de nuit (qui garde son relief du
// jour) ; sin(42°) pour ramener un aplat à 1.
const vec3 FIG_SUN = vec3(-0.5254, 0.6691, -0.5254);
const float FIG_SUN_SIN = 0.6691;

// Le repère de la carte dans le monde (miroir et chute compris).
varying flat vec3 v_x;
varying flat vec3 v_y;
varying flat vec3 v_z;
varying flat float v_mirror;

void vertex() {
	vec3 vp;
	POSITION = fig_position(VERTEX, MODEL_MATRIX, VIEW_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX, vp);
	VERTEX = vp;
	mat3 m = mat3(MODEL_MATRIX);
	v_x = normalize(m[0]);
	v_y = normalize(m[1]);
	v_z = normalize(m[2]);
	v_mirror = determinant(m) < 0.0 ? -1.0 : 1.0;
	NORMAL = normalize((VIEW_MATRIX * vec4(v_z, 0.0)).xyz);
}

// L'ÉCU FLOTTANT du peuple, au-dessus de la tête (Figures.mesh : un second
// quad de la même surface, UV x de 2 à 3 ; pas d'appel de dessin de plus).
// Il est brodé ICI, sans texture, comme l'écu d'une carte : le cordon brun
// (A du masque), le liseré d'or, le champ du peuple en rangs de satin qui
// suivent le bord, le meuble du peuple (pc_charge) ; un léger bombé. Ses
// coordonnées s : demi-largeur du champ 1, y en haut ; l'écu en amande
// (heater) va de y = 0,8 (le chef) à y = -1,48 (la pointe). FB_LO / FB_HI :
// l'étendue du quad (= Figures.BADGE_LO / BADGE_HI).
// La largeur du halo autour des figurines (px d'écran).
const float HALO_PX = 1.4;
const vec2 FB_LO = vec2(-1.7, -2.25);
const vec2 FB_HI = vec2(1.7, 1.5);

// Distance signée à l'écu (négative dedans) : le chef carré, la pointe en
// ogive (deux arcs de rayon 1,6 centrés à x = ±0,6).
float fb_heater(vec2 s) {
	if (s.y > 0.0) {
		return max(abs(s.x) - 1.0, s.y - 0.8);
	}
	return max(length(s - vec2(-0.6, 0.0)), length(s - vec2(0.6, 0.0))) - 1.6;
}

// LES SYMBOLES DE TROUPE de l'écu flottant (dans le repère du meuble :
// demi-largeur 1, y en haut ; négatif dedans). Des traits épais, lisibles à
// une dizaine de pixels : 1 marteau (ingénieur), 2 œil (éclaireur), 3 lance
// (lancier), 4 arc et flèche (archer), 5 épée (homme d'armes), 6 scutum
// (légionnaire), 7 hache (mercenaire), 8 fer à cheval (chevalier), 9 fer à
// cheval et flèche (archer monté), 10 roue (catapulte).
float fb_seg(vec2 p, vec2 a, vec2 b, float r) {
	vec2 pa = p - a, ba = b - a;
	float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * h) - r;
}

float fb_arrow(vec2 p) {
	float shaft = fb_seg(p, vec2(-0.95, 0.0), vec2(0.55, 0.0), 0.08);
	// la pointe : un triangle (x de 0,45 à 1,0)
	vec2 q = vec2(p.x - 0.45, abs(p.y));
	float head = max(max(-q.x, q.y - 0.32 * (1.0 - q.x / 0.55)), q.x - 0.55);
	float fl = max(fb_seg(vec2(p.x, abs(p.y)), vec2(-0.95, 0.24), vec2(-0.65, 0.0), 0.07), -p.x - 1.0);
	return min(min(shaft, head * 0.8), fl);
}

float fb_symbol(vec2 p, int t) {
	if (t == 1) {
		vec2 d = normalize(vec2(0.62, 1.0));
		vec2 c = vec2(0.22, 0.38);
		vec2 n = vec2(-d.y, d.x);
		float handle = fb_seg(p, vec2(-0.5, -0.85), c, 0.12);
		float head = fb_seg(p, c - n * 0.62, c + n * 0.42, 0.22);
		return min(handle, head);
	} else if (t == 2) {
		float lens = max(length(p - vec2(0.0, -0.62)), length(p - vec2(0.0, 0.62))) - 1.08;
		float outline = abs(lens) - 0.09;
		float pupil = length(p) - 0.27;
		return min(outline, pupil);
	} else if (t == 3) {
		float shaft = fb_seg(p, vec2(0.0, -0.98), vec2(0.0, 0.2), 0.1);
		vec2 q = vec2(abs(p.x), p.y - 0.55);
		float blade = (q.x * 0.5 + abs(q.y) * 0.27 - 0.135) / length(vec2(0.5, 0.27));
		float bar = fb_seg(p, vec2(-0.25, 0.08), vec2(0.25, 0.08), 0.07);
		return min(min(shaft, blade), bar);
	} else if (t == 4) {
		float bow = max(abs(length(p - vec2(-0.55, 0.0)) - 0.98) - 0.1, -(p.x + 0.1));
		bow = max(bow, abs(p.y) - 0.88);
		float str = fb_seg(p, vec2(0.0, 0.84), vec2(0.0, -0.84), 0.04);
		return min(min(bow, str), fb_arrow(p));
	} else if (t == 5) {
		float blade = max(fb_seg(p, vec2(0.0, -0.3), vec2(0.0, 0.82), 0.17), p.y - 0.82 - 0.06 + abs(p.x) * 1.2);
		float guard = fb_seg(p, vec2(-0.55, -0.3), vec2(0.55, -0.3), 0.12);
		float grip = fb_seg(p, vec2(0.0, -0.3), vec2(0.0, -0.75), 0.09);
		float pommel = length(p - vec2(0.0, -0.86)) - 0.17;
		return min(min(blade, guard), min(grip, pommel));
	} else if (t == 6) {
		vec2 q = abs(p - vec2(0.0, -0.05));
		float box = length(max(q - vec2(0.5, 0.82), 0.0)) + min(max(q.x - 0.5, q.y - 0.82), 0.0) - 0.08;
		float rim = abs(box) - 0.09;
		float boss = length(p - vec2(0.0, -0.05)) - 0.22;
		float band = max(fb_seg(p, vec2(-0.5, -0.05), vec2(0.5, 0.0 - 0.05), 0.06), box);
		return min(min(rim, boss), band);
	} else if (t == 7) {
		// la hache à deux tranchants : deux lames en éventail, bord convexe
		float haft = fb_seg(p, vec2(0.0, -0.98), vec2(0.0, 0.92), 0.1);
		vec2 q = vec2(abs(p.x), p.y - 0.42);
		float blade = max(abs(q.y) - (0.1 + 0.62 * q.x), length(q - vec2(-0.3, 0.0)) - 1.12);
		return min(haft, blade * 0.8);
	} else if (t == 8 || t == 9) {
		vec2 q = p - vec2(0.0, 0.1);
		float shoe = abs(length(q) - 0.62) - 0.19;
		shoe = max(shoe, -max(abs(q.x) - 0.3, q.y + 0.2));
		// les clous
		float nails = 1e3;
		for (int i = 0; i < 3; i++) {
			float an = 0.55 + float(i) * 0.75;
			nails = min(nails, length(vec2(abs(q.x), q.y) - 0.62 * vec2(cos(an), sin(an))) - 0.06);
		}
		shoe = max(shoe, -nails);
		if (t == 9) {
			return min(shoe, fb_arrow(p - vec2(0.0, -0.55)));
		}
		return shoe;
	} else if (t == 10) {
		float ring = abs(length(p) - 0.72) - 0.13;
		float hub = length(p) - 0.2;
		float spokes = 1e3;
		for (int i = 0; i < 4; i++) {
			float an = float(i) * 0.785398 + 0.392699;
			vec2 dv = vec2(cos(an), sin(an));
			spokes = min(spokes, fb_seg(p, -dv * 0.7, dv * 0.7, 0.07));
		}
		return min(min(ring, hub), spokes);
	}
	return 1e3;
}

// Le meuble d'un écu de la carte (pc_charge), ou le symbole de la troupe
// sur l'écu flottant (fb : 1).
float fb_mark(vec2 p, float fb) {
	// (le symbole, épaissi : des traits qui tiennent à une dizaine de px)
	return fb > 0.5 ? fb_symbol(p, troop) - 0.05 : pc_charge(p, charge);
}

void fragment() {
	// L'écu flottant ? (le quad du haut : UV x > 1,5)
	float fb = step(1.5, UV.x);
	float sel_glow = 0.0;
	if (fb < 0.5 && g_units_hide > 0.5) {
		discard;
	}
	vec2 s = mix(FB_LO, FB_HI, vec2(UV.x - 2.0, 1.0 - UV.y));
	float spx = max(max(length(dFdx(s)), length(dFdy(s))), 1e-6);

	// Hors de toute branche : le repère du meuble et l'empreinte d'un pixel.
	mat2 mi = mat2(arms_inv.xy, arms_inv.zw);
	vec2 p = mi * (UV * card_size - arms_o);
	float bpx = max(max(length(dFdx(p)), length(dFdy(p))), 1e-6);

	vec4 a = texture(albedo_tex, UV);
	vec4 mk = texture(mask_tex, UV);
	vec2 nxy = texture(normal_tex, UV).rg * 2.0 - 1.0;

	// LE HALO : hors de la silhouette, à moins de HALO_PX pixels d'écran
	// d'elle, un liseré noir (gardé sombre la nuit : A du masque) qui détache la
	// figurine de la toile, comme le trait d'une enluminure (Figures.HALO_M :
	// la marge du quad qui le porte). Huit lectures de couverture.
	float halo = 0.0;
	if (fb < 0.5 && a.a < 0.5) {
		vec2 du = fwidth(UV) * HALO_PX;
		float m = 0.0;
		for (int i = 0; i < 8; i++) {
			float an = float(i) * 0.785398;
			m = max(m, texture(albedo_tex, UV + vec2(cos(an), sin(an)) * du).a);
		}
		halo = step(0.5, m);
		vec3 hc = vec3(0.07, 0.05, 0.04);
		a = vec4(hc * halo, halo);
		mk = vec4(0.0, 0.0, 0.0, halo);
		nxy = vec2(0.0);
	}
	if (fb > 0.5) {
		// l'écu de l'unité choisie grandit un peu dans son quad
		if (selected) {
			s /= 1.14;
			spx /= 1.14;
		}
		float d = fb_heater(s);
		vec2 gd = vec2(fb_heater(s + vec2(0.01, 0.0)), fb_heater(s + vec2(0.0, 0.01))) - d;
		vec2 gn = gd / max(length(gd), 1e-6);
		// le cordon : au moins un pixel et demi, quel que soit le zoom
		float cw = max(0.15, 1.5 * spx);
		float field = 1.0 - st_step(d + 0.17, spx);
		float rim = st_band(d + 0.11, 0.05, spx) * (1.0 - field);
		float cord = 1.0 - field - rim;
		// le satin du champ : des rangs qui suivent le bord ; le gris se
		// teint du peuple (R du masque), à la valeur g0 de la carte
		float row = 0.5 + 0.5 * cos(d * 70.0);
		float rows = mix(0.5, row, 1.0 - smoothstep(0.03, 0.07, spx));
		float gray = g0 * (0.93 + 0.1 * rows + 0.06 * clamp(s.y, -1.0, 1.0));
		a.rgb = vec3(gray) * field + ST_OR * rim + ST_BRUN * cord;
		a.a = 1.0 - st_step(d - cw, spx);
		mk = vec4(field, field, 0.28 * field + 0.75 * rim, cord);
		if (selected) {
			// l'anneau de lumière : au-delà du cordon, un fil clair du
			// peuple, cerné d'un fil brun à l'extérieur (il reste brodé)
			float gw = max(0.3, 3.4 * spx);
			float glow = st_step(d - cw + 0.02, spx) * (1.0 - st_step(d - cw - gw, spx));
			float outer = st_band(d - cw - gw + 0.03, 0.03, spx) * glow;
			vec3 gc = clamp(team * 1.5 + vec3(0.3), 0.0, 1.0);
			a.rgb = mix(a.rgb, mix(gc, ST_BRUN, outer), glow);
			a.a = max(a.a, glow);
			mk = mix(mk, vec4(0.0, 0.0, 0.6, outer), glow);
			sel_glow = glow * (1.0 - outer);
		}
		// le bombé du champ, les rangs en relief, le cordon arrondi
		vec2 dome = s * vec2(0.2, 0.14) * field;
		float cr = clamp((d - cw * 0.5) / (cw * 0.5), -1.0, 1.0);
		nxy = dome + gn * (0.12 * (row - 0.5) * field * (1.0 - smoothstep(0.03, 0.07, spx)) + 0.55 * cr * cord);
		// le symbole : centré un peu au-dessus du milieu, demi-largeur 0,64
		p = (s - vec2(0.0, -0.24)) / 0.64;
		bpx = spx / 0.64;
	}
	p.x *= v_mirror;

	// Le peuple : le ton, à la valeur du gris.
	float gray = (a.r + a.g + a.b) / (3.0 * g0);
	vec3 col = mix(a.rgb, clamp(team * gray, 0.0, 1.0), mk.r);

	// Le meuble, sur le champ de l'écu (ou de l'écusson).
	vec2 tilt = vec2(0.0);
	if ((charge > 0 || (fb > 0.5 && troop > 0)) && mk.g > 0.004) {
		float d = fb_mark(p, fb);
		// le symbole de l'écu flottant ne se fond jamais : c'est lui qu'on lit
		float vis = max(1.0 - smoothstep(0.16, 0.36, bpx), fb);
		float cov = mix(0.24, st_step(-d, bpx), vis) * mk.g;
		vec3 cc = charge_col * (0.95 + 0.25 * (clamp(gray, 0.75, 1.2) - 1.0));
		col = mix(col, cc, cov);
		col = mix(col, ST_BRUN, st_band(d, 0.05, bpx) * vis * mk.g * 0.85);
		// Le bombé : la normale penche vers l'extérieur sur le bord du meuble
		// (la pente de d, dans le repère, ramenée à la carte : y en haut).
		vec2 gd = vec2(fb_mark(p + vec2(0.02, 0.0), fb), fb_mark(p + vec2(0.0, 0.02), fb)) - d;
		gd.x *= v_mirror;
		vec2 gt = transpose(mi) * gd;
		gt = vec2(gt.x, -gt.y);
		float ring = smoothstep(-0.18, -0.12, d) * (1.0 - smoothstep(-0.03, 0.0, d));
		tilt = gt / max(length(gt), 1e-6) * 0.35 * ring * vis * mk.g * (1.0 - fb);
	}

	// La normale de la carte -> le monde -> la broderie couchée.
	vec2 nt = nxy + tilt;
	vec3 nc = normalize(vec3(nt, sqrt(max(1.0 - dot(nxy, nxy), 0.0))));
	vec3 nw = normalize(nc.x * v_x + nc.y * v_y + nc.z * v_z);
	vec3 nl = pc_relief(nw);
	NORMAL = normalize((VIEW_MATRIX * vec4(nl, 0.0)).xyz);

	vec3 alb = st_albedo(col);
	float ink = mk.a;
	float night = g_night;
	// Le cordon, la nuit : son fil du jour (relief compris) un peu assombri,
	// non éclairé (émission), sans voile.
	ALBEDO = alb * (1.0 - ink * night);
	vec3 emit = alb * night * (0.32 + 0.38 * (1.0 - clamp(st_luma(alb) * 1.6, 0.0, 1.0))) * (1.0 - ink);
	float ndl = max(dot(nl, FIG_SUN), 0.0);
	float irr = 0.42 + 0.6 * pow(ndl / FIG_SUN_SIN, 1.0 / 2.2);
	emit += alb * irr * (1.0 - 0.25 * night) * night * ink;
	// Le reflet de soie (B du masque), sur la demi-direction soleil / œil,
	// éteint la nuit.
	vec3 eye = normalize(mat3(INV_VIEW_MATRIX) * VIEW);
	float ndh = max(dot(nl, normalize(FIG_SUN + eye)), 0.0);
	float spec = mk.b * (pow(ndh, 26.0) * 0.30 + pow(ndh, 6.0) * 0.06) * (1.0 - 0.7 * night) * 0.6;
	// l'anneau de l'unité choisie bat (et luit la nuit comme le jour)
	float beat = 0.55 + 0.45 * sin(TIME * 4.0);
	emit += alb * sel_glow * (0.35 + 0.55 * beat);
	EMISSION = emit + st_albedo(vec3(spec));
	// Le voile de la veille (écrire FOG remplace celui du moteur) : pas sur le
	// cordon de nuit.
	vec4 veil = pc_veil(VERTEX, g_veil);
	FOG = vec4(veil.rgb, veil.a * (1.0 - ink * night));

	ALPHA = a.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
