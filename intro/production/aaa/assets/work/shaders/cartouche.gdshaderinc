// ============================================================================
// cartouche.gdshaderinc : le CARTOUCHE d'une colonie (view/city_labels.gd),
// le corps commun de ses deux shaders :
//   cartouche.gdshader      la plaque (part = 0), au POCHOIR : elle ne se
//                           dessine pas sur une figurine en carte brodée ;
//   cartouche_nom.gdshader  les lettres du nom (part = 1) et la PLACE DU NOM
//                           (part = 2 : la plaque, sous les lettres
//                           seulement), sans pochoir : rien ne les ajoure.
//
// Une plaque de lin crème brodée, couchée sur la carte au pied de la ville,
// sur DEUX lignes comme sur la cible (« Greymoor / ★5 ») : le nom brodé au
// fil brun (les lettres, un TextMesh, de la géométrie et non une texture),
// puis, dans un onglet qui prolonge la plaque vers le bas, le RANG de la
// colonie : une étoile d'or brodée par niveau, cernée de brun ; l'onglet
// d'une capitale est tendu de la couleur du peuple (étoiles crème).
//
// Le bord, cousu tout autour de la plaque et de son onglet (une seule
// silhouette, raccordée par des congés) : un fil brun, un cordon torsadé à la
// couleur du peuple tenu par des points de fixation, un second fil brun, puis
// un point devant brun à l'intérieur. Les coins de la plaque sont échancrés
// (le cartouche des vieilles cartes) ; deux pointes à la couleur du peuple,
// cernées de brun, dépassent des côtés.
//
// Tout est calculé (aucune texture lue), anti-moiré par la bibliothèque de
// points. COÛT par pixel : 0 hash (st_linen, st_couched, st_running, une
// étoile, géométrie), aucune boucle.
//
// Comme sur la cible, le cartouche passe AU-DESSUS du décor (sapins, monts
// des cases voisines) : il se dessine sans test de profondeur, après tout
// l'opaque et après les fils de view/overlays.gd (CityLabel.PRIORITY), et le
// nom (une priorité de plus) par-dessus la plaque.
//
// LES UNITÉS ET LE NOM. Le nom reste ENTIER : ses lettres et la plaque sous
// elles (la place du nom : la hauteur de la plaque, la largeur du texte)
// passent par-dessus tout, une tête d'unité comprise. Ailleurs (les bouts
// de la plaque, les pointes, l'onglet du rang), le cartouche s'efface devant
// les unités qui s'y tiennent :
//   - une figurine en CARTE BRODÉE marque ses pixels au pochoir (bit 4,
//     figure.gdshader) : la plaque n'y est pas dessinée, l'ajour suit sa
//     silhouette exacte, à tout zoom et pour autant d'unités qu'il en faut ;
//   - une figurine en modèle Blender (l'argument de test `nocards`) n'écrit
//     pas le pochoir : la plaque s'ajoure autour d'elle (hole0..3, posés par
//     CityLabel : son pied sur le sol en coordonnées du monde ; le jour a la
//     forme de la figurine vue d'en haut, son socle rond et son corps couché
//     vers le nord).
// CityLabel soulève d'abord le cartouche au-dessus de la tête des unités du
// sud, autant que le pied du mur le permet.
// ============================================================================

#ifndef CHRONICA_CARTOUCHE_GDSHADERINC
#define CHRONICA_CARTOUCHE_GDSHADERINC

#include "res://view/shaders/stitch.gdshaderinc"

// La plaque du nom (unités monde, centrée sur l'origine du maillage, à plat
// dans xz : x vers la droite de l'écran, z vers le bas), l'onglet du rang
// sous elle (largeur, hauteur ; hauteur 0 : pas d'onglet), les pointes.
uniform vec2 size = vec2(1.6, 0.42);
uniform vec2 tab = vec2(0.43, 0.22);
uniform float ears = 0.13;
// La demi-largeur de la place du nom (le texte et une petite marge) : ce que
// rien n'ajoure.
uniform float name_half = 0.6;
uniform vec3 team : source_color = vec3(0.706, 0.573, 0.282);
uniform int pips = 0;
uniform float capital = 0.0;
// 0 : la plaque ; 1 : les lettres du nom ; 2 : la place du nom.
uniform int part = 0;
uniform vec3 ink : source_color = vec3(0.231, 0.153, 0.067);
// Les jours (figurines en modèle seulement) : (x, z) du pied d'une figurine
// sur le sol (monde), z = 1 si le jour sert, 0 sinon ; w sa hauteur couchée
// (0 : FIG_UP).
uniform vec4 hole0 = vec4(0.0);
uniform vec4 hole1 = vec4(0.0);
uniform vec4 hole2 = vec4(0.0);
uniform vec4 hole3 = vec4(0.0);
// L'emprise d'une figurine en modèle sur le sol, autour de son pied
// (= CityLabel) : rayon du socle, demi-largeur du corps (bouclier compris),
// hauteur couchée.
const float FIG_DISK = 0.29;
const float FIG_HALF_W = 0.2;
const float FIG_UP = 0.9;
// Le rang : pas entre deux étoiles, rayon d'une étoile (= CityLabel).
const float STAR_GAP = 0.23;
const float STAR_R = 0.1;
// Le bord, de l'extérieur vers l'intérieur (profondeurs sous la silhouette).
const float EDGE_OUT = 0.014;   // fil brun
const float CORD_HW = 0.024;     // demi-largeur du cordon
const float EDGE_IN = 0.008;    // second fil brun
const float RUN_AT = 0.088;     // point devant

varying vec2 v_p;
varying vec2 v_w;

void vertex() {
	v_p = VERTEX.xz;
	v_w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

// Un jour : 1 sur l'emprise de la figurine h (bords adoucis), 0 dehors.
float hole(vec2 w, vec4 h, float px) {
	vec2 d = w - h.xy;
	float up = h.w > 0.0 ? h.w : FIG_UP;
	vec2 q = abs(vec2(d.x, d.y + up * 0.5)) - vec2(FIG_HALF_W, up * 0.5) + 0.07;
	float body = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 0.07;
	float disk = length(d) - FIG_DISK;
	return st_step(-min(body, disk), px) * step(0.5, h.z);
}

// Rectangle arrondi : distance signée (négative dedans).
float sd_box(vec2 p, vec2 half_size, float r) {
	vec2 q = abs(p) - half_size + r;
	return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// Union adoucie (congé de rayon ≈ k) de deux distances.
float smin(float a, float b, float k) {
	float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
	return mix(b, a, h) - k * h * (1.0 - h);
}

// Étoile à cinq branches (distance signée, négative dedans ; pointe en
// haut, y vers le haut) : rayon r, creux rf (fraction de r).
float sd_star5(vec2 p, float r, float rf) {
	const vec2 k1 = vec2(0.809016994, -0.587785252);
	const vec2 k2 = vec2(-0.809016994, -0.587785252);
	p.x = abs(p.x);
	p -= 2.0 * max(dot(k1, p), 0.0) * k1;
	p -= 2.0 * max(dot(k2, p), 0.0) * k2;
	p.x = abs(p.x);
	p.y -= r;
	vec2 ba = rf * vec2(-k1.y, k1.x) - vec2(0.0, 1.0);
	float h = clamp(dot(p, ba) / dot(ba, ba), 0.0, r);
	return length(p - ba * h) * sign(p.y * ba.x - p.x * ba.y);
}

void fragment() {
	// D'abord, hors de toute branche : l'empreinte du pixel (sur la plaque, et
	// sur le sol pour les jours).
	vec2 p = v_p;
	float px = st_px(p);
	float pxw = st_px(v_w);
	vec2 hs = size * 0.5;
	// La place du nom : rien ne l'ajoure.
	float name_box = st_step(name_half - abs(p.x), px) * st_step(hs.y - abs(p.y), px);
	float jour = max(max(hole(v_w, hole0, pxw), hole(v_w, hole1, pxw)),
		max(hole(v_w, hole2, pxw), hole(v_w, hole3, pxw))) * (1.0 - name_box);

	// La silhouette : la plaque aux coins échancrés, l'onglet raccordé dessous.
	float d_plate = sd_box(p, hs, 0.03);
	d_plate = max(d_plate, 0.075 - length(abs(p) - hs));
	float has_tab = step(0.001, tab.y);
	vec2 tc = vec2(0.0, hs.y + tab.y * 0.5 - 0.04);
	vec2 th = vec2(tab.x * 0.5, tab.y * 0.5 + 0.04);
	float d_tab = sd_box(p - tc, th, 0.06);
	// Les coins bas de l'onglet, échancrés eux aussi.
	d_tab = max(d_tab, 0.05 - length(abs(p - tc) - th));
	float d_body = mix(d_plate, smin(d_plate, d_tab, 0.06), has_tab);
	// Les pointes : deux losanges allongés vers l'extérieur, à mi-hauteur de
	// la plaque (leur moitié intérieure passe sous la plaque).
	float eh = hs.y * 0.42;
	float ew = ears + 0.04;
	vec2 pe = vec2(abs(p.x) - (hs.x - 0.04), p.y);
	float d_ear = (abs(pe.y) / eh + abs(pe.x) / ew - 1.0) * eh * ew / length(vec2(eh, ew));
	float d = min(d_body, d_ear);

	// La toile crème : du lin.
	vec2 lt;
	float lin = st_linen(p, 0.016, px, lt);
	vec3 creme = st_albedo(ST_CREME);
	vec3 brun = st_albedo(ST_BRUN);
	vec3 col = creme * (0.93 + 0.12 * (lin - 0.5));
	// L'onglet d'une capitale : tendu de la couleur du peuple (sous la plaque).
	float in_low = step(hs.y, p.y) * step(d_body, 0.0) * has_tab * capital;
	col = mix(col, team * (0.92 + 0.12 * (lin - 0.5)), in_low);
	col = mix(col, brun, st_band(p.y - hs.y, 0.005, px) * step(abs(p.x), th.x) * has_tab * capital);

	// Les pointes : à la couleur du peuple, cernées de brun, un fil crème au
	// milieu (hors de la plaque seulement).
	float out_body = st_step(d_body, px);
	float ear_in = st_step(-d_ear, px) * out_body;
	vec3 ear_col = team * (0.95 + 0.12 * (lin - 0.5));
	ear_col = mix(ear_col, creme, st_band(pe.y, 0.006, px) * step(0.0, -d_ear - 0.02));
	col = mix(col, ear_col, ear_in);
	col = mix(col, brun, st_band(d_ear + 0.007, 0.007, px) * out_body);

	// Le bord : fil brun, cordon couché torsadé (tenu par des fixations
	// brunes), fil brun ; le long du côté le plus proche (plaque ou onglet).
	float ein = -d_body;
	vec2 qp = abs(p) - hs;
	float along_p = mix(p.x, p.y, step(qp.y, qp.x));
	vec2 qt = abs(p - tc) - th;
	float along_t = mix(p.x, p.y - tc.y, step(qt.y, qt.x));
	float along = mix(along_p, along_t, step(d_tab, d_plate) * has_tab);
	float on_body = step(d_body, 0.0);
	StThread cord = st_couched(along, ein - (EDGE_OUT + CORD_HW), CORD_HW, 0.034, 0.12, px);
	col = mix(col, st_paint_tie(st_paint(col, team, cord), brun, cord), on_body);
	col = mix(col, brun, st_band(ein - EDGE_OUT * 0.5, EDGE_OUT * 0.5, px) * on_body);
	col = mix(col, brun, st_band(ein - (EDGE_OUT + 2.0 * CORD_HW + EDGE_IN * 0.5), EDGE_IN * 0.5, px));

	// Le point devant brun, à l'intérieur, le long du bord.
	StThread run = st_running(along, ein - RUN_AT, 0.05, 0.03, 0.011, px);
	col = mix(col, brun * 1.1, run.cover * on_body);

	// Le rang : une étoile d'or par niveau, brodée (éclairée du haut à
	// gauche), cernée de brun ; crème sur l'onglet d'une capitale.
	float n = float(pips);
	float x0 = -(n - 1.0) * 0.5 * STAR_GAP;
	float k = clamp(floor((p.x - x0) / STAR_GAP + 0.5), 0.0, max(n - 1.0, 0.0));
	vec2 sp = p - vec2(x0 + k * STAR_GAP, hs.y + tab.y * 0.5 - 0.035);
	sp.y = -sp.y;
	float ds = sd_star5(sp, STAR_R, 0.5);
	float has_star = step(0.5, n) * has_tab;
	float star = st_step(-ds, px) * has_star;
	float star_line = st_step(-(ds - 0.017), px) * has_star;
	float lit = clamp((sp.y - sp.x) / STAR_R, -1.0, 1.0) * st_fade(STAR_R, px);
	vec3 gold = mix(st_albedo(ST_OR), creme, capital) * (1.04 + 0.2 * lit);
	// Le satin de l'étoile : une rainure par branche, du centre vers la pointe.
	float ang = atan(sp.x, sp.y);
	float br = abs(fract(ang / 1.2566371 + 0.5) - 0.5);
	gold *= 1.0 - 0.18 * smoothstep(0.06, 0.0, br) * st_fade(STAR_R * 0.5, px) * step(0.012, length(sp));
	col = mix(col, brun, star_line * (1.0 - star));
	col = mix(col, gold, star);

	// Les lettres : le fil brun du nom, d'un ton plein (elles ne font que
	// quelques pixels d'épaisseur : un motif y crépiterait).
	float is_text = part == 1 ? 1.0 : 0.0;
	ALBEDO = mix(col, ink, is_text);
	// Le bord filtré : pas de crénelage ; les lettres sont des polygones,
	// lissés par le MSAA. La plaque s'ajoure (jours) ; la place du nom ne se
	// dessine que sur elle-même.
	float plate = st_step(-d, px);
	float a_plate = part == 2 ? plate * name_box : plate * (1.0 - jour);
	ALPHA = mix(a_plate, 1.0, is_text);
}

#endif
