shader_type spatial;
// Le plateau BRODÉ (docs/DIRECTION_TAPISSERIE.md) : chaque case est une
// pièce de tissu cousue bord à bord avec ses voisines, à peine bombée
// (capitonnage), taillée dans un coupon du patchwork (Meshes._coupons : d'une
// case à l'autre, l'olive-or, le jaune, la sauge et le lin alternent), et
// chaque terrain a son POINT DE REMPLISSAGE :
//   plaine    : la toile de lin, couverte de longs rangs de fil couché qui la
//               laissent voir entre eux, semée de petits points droits bruns ;
//   forêt     : rangs de satin olive serrés, horizontaux et ondulés (le sol
//               du bois : les arbres sont des pièces), semis clairsemé ;
//   collines  : rangs couchés qui ondulent amplement, comme des courbes de
//               niveau ; calmes : le relief est dans les monticules brodés
//               (view/props.gd), pas dans la pièce ;
//   montagne  : satin en biais, rangs taupe et crème à peine contrastés, le
//               versant nord-ouest (au soleil) un rien plus clair ;
//   rivière   : le point des plaines, où un CORDON BLEU CLAIR couché serpente
//               d'arête en arête, sans contour (la cible) ; il se jette dans
//               la mer ou le lac par une embouchure évasée.
// Les terrains se distinguent par la VALEUR et le POINT, pas par la
// saturation. Le fil n'est jamais d'un seul bain : traînées claires (or) et
// sombres (olive) le long des rangs, chaque rang et chaque point avec sa
// valeur et sa teinte. Chaque arête est un POINT DEVANT crème, cousu à
// cheval sur la couture (les deux pièces en dessinent chacune la moitié : le
// point est continu), sur un sillon sombre. Au bord de la mer ou d'un lac, un
// contour brun, et le point devant rentre dans la pièce. Le capitonnage : la
// pièce s'arrondit et s'assombrit un peu vers la couture.
// L'EMPIÈCEMENT : sous une pièce compacte (mine, carrière, camp de
// bûcherons, tour de guet, chantier, repaire, ruines : Meshes.occupied), un
// coupon de toile plus sombre (vers le brun du contour), sans motifs, est
// cousu au milieu de la case et bordé d'un point devant brun : la pièce s'en
// détache comme sur une tapisserie. Jamais crème ni or (ce serait le
// surlignage de déplacement ou de sélection) ; à peine assombri sur la
// montagne (la roche d'une mine s'y fondrait).
//
// DONNÉES DE MAILLAGE (Meshes.terrain) : COLOR.rgb = fil (sRGB de palette),
// COLOR.a = 1 dessus / 0 ourlet ; UV = centre de la case ; UV2.x = genre de
// point + 4 × occupation (0 / 1 : l'empiècement) ; UV2.y = côte (arête au
// bord de l'eau, 0 / 1) + 2 × tracé (0 hors rivière, sinon 1 + code du
// cordon : p1 + 8·p2 + 64·p3 + 512·embouchure, 7 = aucune arête). Normales
// verticales : le bombé est ici.
// Saisons : la couleur du fil vient de Vis.TERRAIN_COLORS (le maillage est
// refait au changement de saison) ; g_snow pâlit les points, refroidit les
// teintes et gèle le cordon. La nuit (g_night) : la lumière de la lune
// (SkyRig) bleuit et assombrit ; ici, le fil perd une part de sa teinte jaune
// pour que le bleu de la lune ne le fasse pas virer au vert.
//
// COÛT par pixel (dessus), budget iPad ≤ 6 : traînées st_vnoise = 4 hash,
// satin = 1, semis = 1 (plaine, forêt, collines) : 6 au plus ; le cordon de
// rivière : 0 hash (1 atan, 2 sin ; 2 atan avec un affluent) ; l'empiècement :
// 0 hash, ~45 ALU (st_hex_running_ht), dans une branche uniforme sur la case
// (seules les cases occupées la paient). ~300 ALU au pire (rivière) ; aucune
// boucle, aucune texture. Les hash de case sont faits aux sommets. Toutes les
// dérivées sont prises avant la moindre branche (st_px) ; chaque motif
// s'efface vers sa moyenne sous ~2 px (règle de stitch.gdshaderinc).

render_mode diffuse_lambert, specular_schlick_ggx;

#include "res://view/shaders/stitch.gdshaderinc"

global uniform float g_night;
global uniform float g_snow;

// La couture : apothème de l'arête d'une case (Hex.SIZE · √3 / 2).
const float SEAM_H = 0.8660254;

// Les couleurs de la préselection (uniforms globaux posés par
// Vis.use_palette ; défauts de « tapisserie » dans project.godot) :
// Le cordon des rivières (sRGB, = Vis.TERRAIN_COLORS["river"]) : un bleu
// (« tapisserie » : ardoise #3F5368, un rien plus clair que la mer), large,
// cousu dans la toile (la cible) ; gelé l'hiver (#A4B0B6).
global uniform vec3 g_river_col;
global uniform vec3 g_river_ice;
#define RIVER_COL g_river_col
#define RIVER_ICE g_river_ice
// La toile sous les fils, × la couleur du fil (« tapisserie » : 0,50 ;
// 0,49 ; 0,38, un olive-brun) ; plus sombre, les sillons se creusent.
global uniform vec3 g_terrain_under;
// La part de la couleur de la case dans le cordon crème des coutures
// (« tapisserie » : 0, le crème seul).
global uniform float g_terrain_cord_mix;
// Demi-largeur du cordon (une case a un rayon de 1).
const float RIVER_HW = 0.12;
// L'empiècement sous une pièce compacte : son apothème (dans la case, loin
// des frontières cousues vers 0,80 ; assez petit pour se lire comme un
// coupon sous la pièce, pas comme un surlignage de la case), la part du brun
// du contour dans sa toile (moindre sur la montagne), l'ombre de son
// épaisseur sur la toile autour, le point devant brun qui le borde
// (longueur, écart, épaisseur).
const float PATCH_H = 0.56;
const float PATCH_DARK = 0.40;
const float PATCH_DARK_MOUNTAIN = 0.16;
// (la forêt est déjà sombre : le coupon y tire moins vers le brun, et le
// vert du bois et ses arbres restent maîtres de la case)
const float PATCH_DARK_FOREST = 0.22;
const float PATCH_SHADOW = 0.22;
const float PATCH_ST_LEN = 0.07;
const float PATCH_ST_GAP = 0.035;
const float PATCH_ST_W = 0.022;

varying vec3 wpos;
varying vec3 wnorm;
varying vec3 v_base;          // couleur du fil, dans l'espace du renderer
varying vec2 v_center;        // centre de la case (monde xz)
varying flat vec3 v_tile;     // hasards propres à la case, 0..1
varying flat vec2 v_kind;     // x : genre de point + 4 × occupation, y : côte + 2 × tracé

// Rangs de fil couché : le satin de la bibliothèque, dont la rainure entre
// deux rangs est creusée (groove) sans toucher aux bouts des points : de
// longs rangs ondulés, pas un mur de briques. Moyenne de shade inchangée
// (la moyenne de u² sur un rang est 1/3).
StThread rows(vec2 uv, float w, float len, float seed, float bump, float jit, float groove, float rowvar, float px) {
	StThread s = st_satin(uv, w, len, seed, bump, jit, px);
	float f = st_fade(w, px);
	// Les bouts des points adoucis (ombre et trous : ils dessinaient des
	// briques), la rainure entre les rangs creusée.
	s.shade = 1.0 + (s.shade - 1.0) * 0.55;
	s.tilt.x *= 0.5;
	s.cover = 1.0 - (1.0 - s.cover) * 0.4;
	s.shade *= 1.0 - groove * (s.u * s.u - 0.3333) * f;
	// Chaque rang a sa valeur (un brin plus clair, un plus sombre) : suite de
	// Weyl sur l'indice du rang, sans hash ; moyenne nulle.
	float row = floor(uv.y / w);
	s.shade *= 1.0 + (fract(row * 0.6180339 + seed * 7.0) - 0.5) * rowvar * f;
	return s;
}

// Un fil n'est pas l'autre : d'un point à l'autre, la teinte hésite entre
// l'olive et l'or (rnd propre au point, moyenne 0,5 : la teinte moyenne ne
// bouge pas ; effacé avec le point).
vec3 strand(vec3 base, StThread s, float w, float px) {
	vec3 hue = vec3(-0.10, 0.0, 0.06) * (1.0 - 0.75 * g_snow);
	return base * (1.0 + (s.rnd - 0.5) * hue * st_fade(w * 1.5, px));
}

// Distance d'un point au segment [a, b].
float seg_d(vec2 q, vec2 a, vec2 b) {
	vec2 ab = b - a;
	float k = clamp(dot(q - a, ab) / dot(ab, ab), 0.0, 1.0);
	return length(q - a - ab * k);
}

// Les PETITS MOTIFS brodés par-dessus le remplissage (la cible : touffes
// d'herbe, fleurettes, petits arcs), un au plus par cellule de `cell`
// (st_scatter : 1 hash). mix_t : part de touffes, mix_f : de fleurettes (le
// reste : des arcs) ; density : part des cellules garnies. Rend la couverture
// (filtrée, effacée au loin) ; which : 0 touffe, 1 fleurette, 2 arc ; heart :
// le cœur de la fleurette (ocre).
const float MOTIF_S = 1.4;

float motif(vec2 wp, float cell, float seed, float density, float mix_t, float mix_f, float px, out float which, out float heart) {
	vec2 q;
	vec2 hh = st_scatter(wp, cell, seed, q);
	// Les motifs sont dessinés à l'échelle 1 puis agrandis (MOTIF_S) : q et px
	// dans le repère du motif.
	q /= MOTIF_S;
	px /= MOTIF_S;
	float present = step(fract(hh.y * 13.7), density);
	float vis = st_fade(0.05, px) * present;
	float m = fract(hh.x * 5.31);
	// Le nord est vers -z : les brins montent vers le haut de l'écran.
	vec2 b = vec2(0.0, 0.026);
	float lw = 0.0075;
	float dt = min(seg_d(q, b, b + vec2(-0.026, -0.044)),
		min(seg_d(q, b, b + vec2(0.0, -0.056)), seg_d(q, b, b + vec2(0.028, -0.040))));
	float tuft = st_band(dt, lw, px);
	float r = length(q);
	float ang = atan(q.y, q.x) + hh.x * ST_TAU;
	float petal = st_step(0.024 * (0.55 + 0.45 * abs(cos(2.5 * ang))) - r, px);
	heart = st_step(0.0085 - r, px);
	vec2 qa = q - vec2(0.0, 0.018);
	float arc = st_band(length(qa) - 0.034, lw, px) * st_step(0.004 - qa.y, px);
	which = m < mix_t ? 0.0 : (m < mix_t + mix_f ? 1.0 : 2.0);
	float c = which < 0.5 ? tuft : (which < 1.5 ? petal : arc);
	heart *= step(0.5, which) * step(which, 1.5);
	return c * vis;
}

// --- Le tracé du cordon (cases de rivière) ---------------------------------

// La normale sortante de l'arête qui regarde Hex.DIRS[d] (plan xz).
vec2 dirn(float d) {
	float a = -d * (ST_PI / 3.0);
	return vec2(cos(a), sin(a));
}

// Le repère d'un tronçon de rivière de l'arête d1 à l'arête d2 : un arc de
// cercle qui coupe les deux arêtes en leur milieu, à angle droit (centre au
// sommet commun de deux arêtes voisines, ou au centre de la case d'en face
// pour deux arêtes à un cran d'écart), une droite pour deux arêtes opposées.
// Deux cases voisines se raccordent donc sans coude. Rend (s : 0 sur d1, 1
// sur d2 ; across : distance signée ; L : longueur), T et B : tangente et
// travers (plan xz), across = dot(·, B).
vec3 river_arc(vec2 p, float d1, float d2, out vec2 T, out vec2 B) {
	vec2 n1 = dirn(d1);
	vec2 n2 = dirn(d2);
	vec2 m1 = SEAM_H * n1;
	float k = abs(d2 - d1);
	k = min(k, 6.0 - k);
	if (k > 2.5) {
		T = -n1;
		B = vec2(n1.y, -n1.x);
		return vec3(dot(m1 - p, n1) / (2.0 * SEAM_H), dot(p, B), 2.0 * SEAM_H);
	}
	bool tight = k < 1.5;
	vec2 C = tight ? (n1 + n2) * 0.5773503 : (n1 + n2) * 1.7320508;
	float R = tight ? 0.5 : 1.5;
	float span = tight ? 2.0943951 : 1.0471976;
	vec2 q = p - C;
	float r = max(length(q), 1e-4);
	vec2 a1 = (m1 - C) / R;
	vec2 a2 = SEAM_H * n2 - C;
	float sg = (a1.x * a2.y - a1.y * a2.x) >= 0.0 ? 1.0 : -1.0;
	float ang = atan(a1.x * q.y - a1.y * q.x, dot(a1, q)) * sg;
	B = q / r;
	T = vec2(-B.y, B.x) * sg;
	return vec3(ang / span, r - R, R * span);
}

// Un tronçon droit de m1 jusqu'à tip (un affluent, une source) ; au-delà de
// tip, un bout rond.
vec3 river_spoke(vec2 p, vec2 m1, vec2 tip, out vec2 T, out vec2 B) {
	vec2 v = tip - m1;
	float L = max(length(v), 1e-3);
	T = v / L;
	B = vec2(T.y, -T.x);
	float a = dot(p - m1, T);
	float across = dot(p - m1, B);
	if (a > L) {
		across = length(p - tip) * (across >= 0.0 ? 1.0 : -1.0);
	}
	return vec3(a / L, across, L);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_base = st_albedo(COLOR.rgb);
	v_center = UV;
	// Coordonnées axiales entières de la case : la graine ne dépend pas des
	// arrondis du centre.
	vec2 qr;
	qr.y = floor(UV.y / 1.5 + 0.5);
	qr.x = floor(UV.x / ST_SQRT3 - qr.y * 0.5 + 0.5);
	v_tile = vec3(st_hash21(qr), st_hash22(qr + 17.0));
	v_kind = UV2;
}

void fragment() {
	// --- Tout ce qui dérive d'abord, hors de toute branche. -----------------
	float px = st_px(wpos.xz);
	vec2 p = wpos.xz - v_center;
	float t;
	vec2 en;
	float h = st_hex(p, t, en);
	// Le genre de point et l'occupation (l'empiècement) : x = genre + 4 × occ.
	float kraw = floor(v_kind.x + 0.5);
	float occ = floor(kraw * 0.25);
	float kind = kraw - 4.0 * occ;
	// L'empiècement : un hexagone d'apothème PATCH_H au milieu de la case
	// (bord antialiasé ; 0 hors des cases occupées).
	float ap = occ * st_step(PATCH_H - h, px);
	float ky = floor(v_kind.y + 0.5);
	float coast = mod(ky, 2.0);
	float route = floor(ky * 0.5 + 0.25);      // 0 hors rivière, sinon 1 + code
	vec3 base = v_base;
	const vec3 UP = vec3(0.0, 1.0, 0.0);
	const vec3 AX = vec3(1.0, 0.0, 0.0);
	const vec3 AZ = vec3(0.0, 0.0, 1.0);
	vec3 Te = vec3(-en.y, 0.0, en.x);   // le long de l'arête la plus proche
	vec3 Be = vec3(en.x, 0.0, en.y);    // vers l'arête (sortant)

	// Les rangs ondulent : la main de la brodeuse, propre à chaque pièce (la
	// phase glisse d'un rang à l'autre avec z).
	float wave = 0.020 * sin(wpos.x * 2.3 + wpos.z * 0.7 + v_tile.x * ST_TAU)
		+ 0.011 * sin(wpos.x * 9.5 + wpos.z * 2.1 + v_tile.y * ST_TAU);
	// Des traînées de fil plus clair ou plus sombre, allongées dans le sens
	// des rangs : une broderie n'est jamais teinte d'un seul bain. Le seul
	// bruit du shader (4 hash), effacé vers 0,5 s'il devient fin. Assez
	// discrètes pour que l'écart d'une pièce à l'autre (le patchwork) domine.
	float mot = mix(0.5, st_vnoise(vec2(wpos.x * 2.2, wpos.z * 6.5) + v_tile.xy * 37.0), st_fade(0.15, px));
	// Les traînées claires tirent vers l'or, les sombres vers l'olive (l'hiver,
	// seulement la valeur).
	base *= 1.0 + (mot - 0.5) * mix(vec3(0.34, 0.31, 0.24), vec3(0.32), g_snow);
	// La toile sous les fils : plus sombre que le fil, olive-brun.
	vec3 under = base * g_terrain_under;
	// Le fil des petits points (semis) : un brun de terre, gris l'hiver.
	vec3 dot_col = mix(base * vec3(0.46, 0.41, 0.34), st_albedo(ST_BRUN), 0.3);
	dot_col = mix(dot_col, base * vec3(0.62, 0.64, 0.66), g_snow * 0.6);

	// LE SENS DU POINT change d'une pièce à l'autre (la cible : chaque case
	// est brodée dans son propre sens) : six biais, de -55° à +55°, tirés du
	// hasard de la case (uniforme sur la pièce : dérivées sûres).
	float ang = (floor(v_tile.x * 6.0) - 2.5) * 0.38;
	vec2 cs0 = vec2(cos(ang), sin(ang));
	vec2 ruv = vec2(dot(p, cs0), dot(p, vec2(-cs0.y, cs0.x)));
	vec3 RT = vec3(cs0.x, 0.0, cs0.y);
	vec3 RB = vec3(-cs0.y, 0.0, cs0.x);
	// Les petits motifs : couleurs des touffes (olive sombre), des fleurettes
	// (crème, cœur ocre) et des arcs (brun).
	vec3 tuft_col = mix(base * vec3(0.52, 0.56, 0.42), st_albedo(ST_SAPIN), 0.35);
	tuft_col = mix(tuft_col, base * vec3(0.66, 0.68, 0.70), g_snow * 0.7);
	vec3 flo_col = st_albedo(ST_CREME) * 0.95;
	vec3 heart_col = st_albedo(ST_OCRE);
	float mw;
	float mh;
	float mc;

	vec3 col;
	vec3 n;
	if (kind < 0.5) {
		// PLAINE (et berge de rivière) : la toile de lin, couverte de rangs de
		// fil couché serrés, dans le sens propre à la pièce, semée de touffes,
		// de fleurettes et de petits arcs.
		const float W = 0.040;
		StThread s = rows(vec2(ruv.x, ruv.y + wave), W, 0.36, v_tile.z, 0.30, 0.09, 0.40, 0.22, px);
		s.cover *= mix(0.86, st_band(s.u * 0.5 * W, 0.44 * W, px), st_fade(W, px));
		vec2 lt;
		float lin = st_linen(wpos.xz, 0.018, px, lt);
		vec3 ground = under * (1.0 + (lin - 0.5) * 0.5);
		col = st_paint(ground, strand(base, s, W, px), s);
		n = st_bend(UP, RT, RB, s.tilt * s.cover + lt * (1.0 - s.cover));
		mc = motif(wpos.xz, 0.30, 3.0, 0.85, 0.55, 0.22, px, mw, mh);
		mc *= (1.0 - smoothstep(0.70, 0.76, h)) * (1.0 - ap);
		vec3 mcol = mw < 0.5 ? tuft_col : (mw < 1.5 ? mix(flo_col, heart_col, mh) : dot_col);
		col = mix(col, mcol, mc);
	} else if (kind < 1.5) {
		// FORÊT (le sol) : rangs de satin serrés, dans le sens de la pièce ;
		// quelques touffes sombres entre les arbres.
		StThread s = rows(vec2(ruv.x, ruv.y + wave), 0.044, 0.34, v_tile.z, 0.38, 0.10, 0.38, 0.22, px);
		col = st_paint(under, strand(base, s, 0.044, px), s);
		n = st_bend(UP, RT, RB, s.tilt * s.cover);
		mc = motif(wpos.xz, 0.32, 5.0, 0.65, 0.85, 0.0, px, mw, mh);
		mc *= (1.0 - smoothstep(0.70, 0.76, h)) * (1.0 - ap);
		col = mix(col, mw < 0.5 ? tuft_col * 0.85 : dot_col, mc);
	} else if (kind < 2.5) {
		// COLLINES : des rangs couchés qui ondulent amplement, comme des
		// courbes de niveau, dans le sens de la pièce ; petits arcs bruns
		// (des mottes) et quelques touffes.
		float cw = 0.050 * sin(ruv.x * 1.6 + v_tile.x * ST_TAU)
			+ 0.024 * sin(ruv.x * 3.7 + ruv.y * 1.2 + v_tile.y * ST_TAU);
		StThread s = rows(vec2(ruv.x, ruv.y + wave * 0.5 + cw), 0.046, 0.40, v_tile.z, 0.30, 0.07, 0.30, 0.14, px);
		col = st_paint(under, strand(base, s, 0.046, px), s);
		n = st_bend(UP, RT, RB, s.tilt * s.cover);
		mc = motif(wpos.xz, 0.32, 7.0, 0.75, 0.30, 0.0, px, mw, mh);
		mc *= (1.0 - smoothstep(0.70, 0.76, h)) * (1.0 - ap);
		col = mix(col, mw < 0.5 ? tuft_col : dot_col, mc);
	} else {
		// MONTAGNE : rangs couchés en léger biais, d'un fil taupe où passent
		// quelques rangs crème (le satin crème et gris de la direction), à
		// peine contrastés ; le versant nord-ouest (au soleil) un rien plus
		// clair. Les pics brodés (décors) font la montagne.
		const float A = 0.16;   // ~9°
		vec2 cs = vec2(cos(A), sin(A));
		vec2 uv = vec2(dot(p, cs), dot(p, vec2(-cs.y, cs.x)) + wave);
		const float W = 0.05;
		StThread s = rows(uv, W, 0.44, v_tile.z, 0.30, 0.07, 0.30, 0.10, px);
		float band = step(0.66, fract(floor(uv.y / W) * 0.6180339 + v_tile.y));
		float lit = smoothstep(-0.35, 0.35, dot(p, vec2(-0.7071, -0.7071)) + wave * 2.0);
		float cream = mix(0.34, band, st_fade(W * 2.0, px)) * 0.6 + lit * 0.4;
		vec3 thread = mix(base * vec3(0.94, 0.93, 0.91), mix(base, st_albedo(ST_CREME), 0.24), cream);
		col = st_paint(under, strand(thread, s, W, px), s);
		n = st_bend(UP, vec3(cs.x, 0.0, cs.y), vec3(-cs.y, 0.0, cs.x), s.tilt * s.cover);
	}

	// --- Le capitonnage : la pièce s'arrondit vers la couture. ---------------
	float roll = smoothstep(0.60, SEAM_H, h);
	n = st_bend(n, Be, Te, vec2(0.55 * roll * roll, 0.0));
	col *= 1.0 - 0.12 * smoothstep(0.70, SEAM_H, h);

	// --- L'EMPIÈCEMENT sous une pièce compacte : la toile, sans motifs, tire
	// vers le brun du contour (à peine sur la montagne : la roche d'une mine
	// s'y fondrait) ; son épaisseur porte une ombre fine sur la toile autour ;
	// un point devant brun le borde. Branche uniforme sur la case (occ est
	// plat) : seules les cases occupées la paient. ----------------------------
	if (occ > 0.5) {
		float dark = kind > 2.5 ? PATCH_DARK_MOUNTAIN : (kind > 0.5 && kind < 1.5 ? PATCH_DARK_FOREST : PATCH_DARK);
		// Sous la neige, le coupon tire vers le taupe du cordon d'hiver, et
		// moins fort : pas une flaque de boue sur la neige.
		dark *= 1.0 - 0.45 * g_snow;
		vec3 patch_tone = mix(st_albedo(ST_BRUN), st_albedo(vec3(0.58, 0.52, 0.42)), 0.6 * g_snow);
		col = mix(col, mix(col, patch_tone, dark), ap);
		col *= 1.0 - PATCH_SHADOW * st_band(h - PATCH_H - 0.024, 0.014, px);
		StThread pe = st_hex_running_ht(h, t, PATCH_H, PATCH_ST_LEN, PATCH_ST_GAP, PATCH_ST_W, px);
		col = st_paint(col, st_albedo(ST_BRUN) * 0.9, pe);
		n = normalize(mix(n, st_bend(UP, Te, Be, pe.tilt), pe.cover));
	}

	// --- La couture : un sillon sombre, et au bord de l'eau un contour brun. -
	// Le sillon garde au moins ~1 px de large (0,6 px de chaque côté) : de
	// loin, quand le point devant a fondu, c'est lui qui dessine la grille.
	float groove = st_band(h - SEAM_H, max(0.015, 0.6 * px), px);
	col *= 1.0 - 0.30 * groove * (1.0 - coast);
	float ol = st_band(h - (SEAM_H - 0.012), 0.012, px) * coast;
	col = mix(col, st_albedo(ST_BRUN), ol * 0.9);

	// --- Le CORDON CRÈME couché à cheval sur la couture (la cible : un gros
	// fil crème bombé, bien visible, qui dessine la grille). Chaque pièce en
	// coud la moitié (across < 0 de son côté) : le rond se raccorde. Une ombre
	// portée fine le détache de la pièce. Pas au bord de l'eau : la côte a
	// son contour brun, et l'eau coud son propre liseré. ----------------------
	const float CORD_HW = 0.032;
	float cord_x = h - SEAM_H;
	float cord_sh = st_band(cord_x + CORD_HW + 0.012, 0.012, px) * (1.0 - coast);
	col *= 1.0 - 0.22 * cord_sh;
	StThread e = st_couched(t, cord_x, CORD_HW, 0.075, 0.0, px);
	e.tie = 0.0;
	e.cover *= 1.0 - coast;
	vec3 crem = st_albedo(ST_CREME) * 0.90;
	// Teinté de sa case (la préselection en donne la part).
	crem = mix(crem, v_base * 0.90, g_terrain_cord_mix);
	crem = mix(crem, st_albedo(vec3(0.58, 0.52, 0.42)), g_snow * 0.75);
	// Le rond : un cœur clair, des flancs ombrés (il se lit bombé même de
	// loin, avant la lumière).
	crem *= 1.06 - 0.30 * e.u * e.u;
	col = st_paint(col, crem, e);
	n = normalize(mix(n, st_bend(UP, Te, Be, e.tilt), e.cover));

	// --- La nuit : la lune bleuit la lumière ; une toile jaune sous une
	// lumière bleue vire au gris vert. Le fil perd donc une part de sa teinte
	// (vers un gris à peine froid) et un peu de valeur : la lune le bleuit et
	// l'assombrit sans le verdir. ------------------------------------------
	// (SkyRig donne déjà à la lune R < G < B : une part modeste suffit, plus
	// forte la toile vire à l'outremer ; mesuré : plaine ≈ #5F6774, forêt ≈
	// #3E4757, la teinte des coupons se devine encore.)
	col = mix(col, vec3(st_luma(col)) * vec3(0.97, 0.99, 1.03), 0.30 * g_night);
	col *= 1.0 - 0.04 * g_night;

	// --- Le cordon de rivière, par-dessus tout (il passe sur les coutures et
	// se raccorde à celui de la case voisine au milieu de l'arête). ----------
	if (route > 0.5) {
		float code = route - 1.0;
		// Le tracé : p1-p2 l'arc principal, p3 un affluent ; 7 = aucune.
		float r1 = mod(code, 8.0);
		float r2 = mod(floor(code / 8.0), 8.0);
		float r3 = mod(floor(code / 64.0), 8.0);
		float mouth1 = step(511.5, code);
		float source = step(6.5, r2);
		vec2 T;
		vec2 B;
		vec3 f;
		if (source > 0.5) {
			// Une source : le cordon part de l'arête et s'arrête au centre.
			f = river_spoke(p, SEAM_H * dirn(r1), vec2(0.0), T, B);
		} else {
			f = river_arc(p, r1, r2, T, B);
		}
		float sc = clamp(f.x, 0.0, 1.0);
		// Le méandre : nul et à plat aux deux bouts (les cases se raccordent).
		float mea = 0.07 * f.z * sin(ST_TAU * sc) * sin(ST_PI * sc) * (mod(code, 2.0) * 2.0 - 1.0) * (1.0 - source);
		float across = f.y - mea;
		float along = f.x * f.z;
		float hw = RIVER_HW;
		// L'embouchure s'évase vers la mer ; la source s'amincit.
		hw *= 1.0 + 0.7 * mouth1 * (1.0 - smoothstep(0.0, 0.35, sc));
		hw *= mix(1.0, 0.6 + 0.4 * (1.0 - smoothstep(0.5, 1.0, f.x)), source);
		// Un affluent rejoint l'arc au plus près du centre.
		if (r3 < 6.5) {
			vec2 Td;
			vec2 Bd;
			vec3 fm = river_arc(vec2(0.0), r1, r2, Td, Bd);
			vec2 T3;
			vec2 B3;
			vec3 f3 = river_spoke(p, SEAM_H * dirn(r3), -Bd * fm.y, T3, B3);
			float hw3 = RIVER_HW * 0.85;
			if (abs(f3.y) - hw3 < abs(across) - hw) {
				f = f3;
				across = f3.y;
				along = f3.x * f3.z;
				hw = hw3;
				T = T3;
				B = B3;
			}
		}
		// La torsade tombe juste aux deux bouts (les fixations en travers ne
		// sont pas cousues : elles faisaient un tuyau à segments).
		float tie_p = f.z / max(floor(f.z / 0.22 + 0.5), 1.0);
		float tw_p = f.z / max(floor(f.z / 0.11 + 0.5), 1.0);
		// Une ombre douce sur la berge (le cordon est posé sur la toile), sans
		// liseré : la cible n'en a pas.
		float bank_sh = 1.0 - smoothstep(hw, hw + 0.06, abs(across));
		col *= 1.0 - 0.12 * bank_sh;
		// Un liseré crème le long de chaque rive (la cible : le cordon est
		// bordé d'un fil clair qui le détache de la toile), filtré.
		col = mix(col, st_albedo(ST_CREME) * 0.9, st_band(abs(across) - hw - 0.006, 0.008, px) * 0.35);
		StThread cd = st_couched(along, across, hw, tw_p, tie_p, px);
		cd.tie = 0.0;
		vec3 rc = st_albedo(mix(RIVER_COL, RIVER_ICE, g_snow));
		rc = mix(rc, vec3(st_luma(rc)) * vec3(0.92, 0.98, 1.08), 0.5 * g_night);
		// Le cordon rond : le cœur plus clair que les flancs (un bleu plus
		// soutenu au bord, jamais brun), un reflet de soie discret.
		vec3 cord = rc * (1.08 - 0.36 * cd.u * cd.u);
		cord *= 1.0 + 0.12 * st_sheen(cd.u, -0.35, 0.5) * st_fade(hw * 2.0, px);
		col = st_paint(col, cord, cd);
		// Le fil qui le tient : un point devant clair au milieu du cordon (la
		// cible : des tirets crème bleuté qui courent le long de la rivière).
		float dp = f.z / max(floor(f.z / 0.125 + 0.5), 1.0);   // un tiret centré sur chaque arête
		StThread cm = st_running(along, across + 0.012, dp * 0.6, dp * 0.4, 0.022, px);
		cm.cover *= cd.cover;
		col = st_paint(col, mix(rc * 1.4, st_albedo(ST_CREME), 0.45), cm);
		n = normalize(mix(n, st_bend(UP, vec3(T.x, 0.0, T.y), vec3(B.x, 0.0, B.y), cd.tilt), cd.cover));
	}

	// --- L'ourlet (les pièces qui bordent l'eau) : un liseré de fil brun. ----
	if (COLOR.a < 0.5) {
		col = base;
		n = wnorm;
	}

	ALBEDO = col;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = 0.8;
	SPECULAR = 0.15;
}
