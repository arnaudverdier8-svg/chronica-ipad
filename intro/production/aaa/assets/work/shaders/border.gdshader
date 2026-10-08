shader_type spatial;
// Les frontières (direction tapisserie, docs/CIBLE_TAPISSERIE.png) : un gros
// cordon de POINT DEVANT à la couleur du peuple, cousu CONTRE l'arête, dans
// chaque case du territoire : les grains colorés sur un fil de dessous (crème
// sous un peuple sombre, brun sous l'or), entre deux liserés bruns, avec une
// ombre portée courte vers le bas-droite. Le liseré extérieur couvre la
// couture : deux peuples voisins cousent deux cordons côte à côte, de part et
// d'autre de l'arête. Ce sont les fils les plus épais de la carte après la
// sélection : ils structurent la carte.
//
// Données (view/meshes.gd, Meshes.borders) : UV = position relative au
// centre de la case ; UV2.x = masque des arêtes frontières (bit d =
// Hex.DIRS[d]), UV2.y = celles qui touchent un autre peuple ; COLOR = le ton
// du fil (Meshes.border_tone, sRGB).
//
// Le tracé : la distance au territoire. On mesure la distance aux SEGMENTS
// d'arête frontières (celle du secteur et ses deux voisines) : le cordon
// suit l'arête, se coupe en onglet aux coins saillants et tourne en arc aux
// coins rentrants (le raccord se coud à moitié dans chacune des deux cases
// du peuple) : la ligne se lit d'un trait, sans brèche aux coins.
//
// La nuit, le fil luit à peine (glow) pour rester lisible.
// COÛT par pixel : 0 hash ; st_hex, 3 distances à un segment, 1 point devant,
// 1 torsade (1 cos, 1 sin).

render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;

#include "res://view/shaders/stitch.gdshaderinc"

uniform float glow = 0.0;

// L'arête d'une case (apothème).
const float EDGE = 0.8660254;
// L'axe du cordon (Meshes.BORDER_RING) et sa distance à l'arête.
const float RING = 0.814;
const float D0 = EDGE - RING;
// Le cordon : épaisseur des grains, liseré brun de chaque bord, et le liseré
// posé au-delà de l'arête, sur la couture (Meshes.BORDER_OUT le contient).
const float W = 0.08;
const float OW = 0.009;
const float OVER = 0.012;
// Les grains : 5 par arête (un nombre entier : les arêtes se raccordent
// proprement), deux fois plus longs que larges, comme sur la cible. L'espace
// (0,037) reste au-dessus du seuil anti-moiré au zoom de la cible : le fil
// de dessous (crème ou brun) s'y lit encore entre les grains.
const float PER = 0.2;
const float DASH = 0.163;
// L'ombre portée : vers le bas-droite de l'écran (+x, +z), courte ; et
// jusqu'où elle déborde de l'arête quand le voisin n'a pas de cordon.
const vec2 SHADOW_OFS = vec2(0.02, 0.028);
const float SHADOW_OUT = 0.04;

varying vec3 wpos;
varying vec2 lp;
varying vec3 v_col;
// 1 pour un peuple clair (l'or), qui coud sur un fil brun.
varying float v_light;
// Les masques d'arêtes (frontières, peuple étranger), entiers.
varying flat vec2 v_mask;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	lp = UV;
	v_col = st_albedo(COLOR.rgb);
	v_light = step(0.45, st_luma(COLOR.rgb));
	v_mask = floor(UV2 + 0.5);
}

// Le bit d (0..5) d'un masque.
float bit(float m, float d) {
	return mod(floor(m / exp2(d) + 1e-3), 2.0);
}

// Distance SIGNÉE (positive dans la case) au segment de l'arête de normale n
// (demi-longueur 0,5) ; q : son point le plus proche ; t : abscisse le long
// de l'arête (non bornée, même sens que le t de st_hex).
float side_dist(vec2 p, vec2 n, out vec2 q, out float t) {
	vec2 T = vec2(-n.y, n.x);
	t = dot(p, T);
	q = EDGE * n + clamp(t, -0.5, 0.5) * T;
	return length(p - q) * (dot(p, n) <= EDGE ? 1.0 : -1.0);
}

// Poser une couche (couleur c, couverture a) PAR-DESSUS l'accumulé (non
// prémultiplié).
void over(inout vec4 acc, vec3 c, float a) {
	float oa = a + acc.a * (1.0 - a);
	acc.rgb = (c * a + acc.rgb * acc.a * (1.0 - a)) / max(oa, 1e-4);
	acc.a = oa;
}

void fragment() {
	// --- Dérivées et repères d'abord, hors de toute branche. -----------------
	float px = st_px(wpos.xz);
	float t0;
	vec2 en;
	float h = st_hex(lp, t0, en);
	float dir = st_hex_dir(en);
	// Les arêtes voisines : tournée de +60° = Hex.DIRS[d - 1], de -60° = [d + 1].
	vec2 np = vec2(0.5 * en.x - 0.8660254 * en.y, 0.8660254 * en.x + 0.5 * en.y);
	vec2 nm = vec2(0.5 * en.x + 0.8660254 * en.y, -0.8660254 * en.x + 0.5 * en.y);
	float b0 = bit(v_mask.x, dir);
	float bp = bit(v_mask.x, mod(dir + 5.0, 6.0));
	float bm = bit(v_mask.x, mod(dir + 1.0, 6.0));
	float foreign = bit(v_mask.y, dir);

	// --- La distance au territoire : la plus courte aux arêtes frontières. ---
	vec2 q0;
	vec2 qp;
	vec2 qm;
	float ta;
	float tp;
	float tm;
	float d0 = side_dist(lp, en, q0, ta);
	float dp = side_dist(lp, np, qp, tp);
	float dm = side_dist(lp, nm, qm, tm);
	d0 = b0 > 0.5 ? d0 : 1e3;
	dp = bp > 0.5 ? dp : 1e3;
	dm = bm > 0.5 ? dm : 1e3;
	float D = d0;
	vec2 q = q0;
	vec2 n = en;
	float along = ta;
	if (dp < D) {
		D = dp;
		q = qp;
		n = np;
		along = tp;
	}
	if (dm < D) {
		D = dm;
		q = qm;
		n = nm;
		along = tm;
	}
	// En travers : 0 sur l'axe du cordon, > 0 vers le centre de la case ; g :
	// la direction « en travers » (vers le centre), droite le long d'une
	// arête, rayonnante autour du sommet d'un coin rentrant.
	float x = D - D0;
	vec2 diff = lp - q;
	float dl = length(diff);
	vec2 g = dl > 1e-4 ? diff / dl * sign(D) : -n;

	// --- Les couches : ombre, liserés bruns, fil de dessous, grains. ---------
	vec3 brun = st_albedo(ST_BRUN);
	vec4 acc = vec4(brun, 0.0);
	// L'ombre portée du cordon entier (liserés compris).
	float xs = x - dot(SHADOW_OFS, g);
	over(acc, brun, st_band(xs, 0.5 * W + OW, px) * 0.32);
	// Les liserés : du dessus de la couture (au-delà de l'arête) jusqu'au bord
	// intérieur du cordon.
	float lo = -D0 - OVER;
	float hi = 0.5 * W + OW;
	over(acc, brun, st_band(x - 0.5 * (lo + hi), 0.5 * (hi - lo), px) * 0.9);
	// Le fil de dessous, qui se lit entre les grains : un or bruni sous l'or
	// (des grains d'or serrés, comme sur la cible), crème sous un peuple
	// sombre (des piqûres claires dans le cordon).
	vec3 gap_col = v_light > 0.5 ? mix(brun, v_col, 0.4) : st_albedo(ST_CREME) * 0.9;
	// Au loin, quand les grains fondent en un trait (anti-moiré), le fil de
	// dessous prend la couleur du peuple : le trait reste franc au lieu de
	// tourner au gris (un rouge moyenné de crème se lit mal sur le lin).
	gap_col = mix(v_col, gap_col, st_fade(2.0 * (PER - DASH), px));
	over(acc, gap_col, st_band(x, 0.5 * W, px));
	// Les grains, à la couleur du peuple : cinq par arête, centrés sur
	// -0,5 + PER/2 + k·PER (un demi-espace à chaque sommet).
	StThread s = st_running(along + 0.5 - 0.5 * PER, x, DASH, PER - DASH, W, px);
	vec3 thread = v_col * s.shade * (1.0 + 0.14 * st_sheen(s.u, -0.35, 0.5) * st_fade(W, px));
	// Chaque grain est un fil retors : une torsade en biais (de près
	// seulement ; effacée dès qu'elle tombe sous ~2 pixels).
	const float TWIST = 0.042;
	vec3 tw = st_twist(along / TWIST, s.u, 0.5);
	float vis_tw = st_fade(TWIST, px) * st_fade(W, px);
	thread *= 1.0 + (tw.x - 0.5) * 0.18 * vis_tw;
	over(acc, thread, s.cover);

	// Rognage : rien au-delà d'une arête intérieure au territoire (la voisine
	// coud sa part du raccord) ; au-delà d'une arête frontière, le liseré sur
	// la couture et, si le voisin n'a pas de cordon, l'ombre portée.
	float out_max = b0 * mix(SHADOW_OUT, OVER, foreign);
	float keep = st_step(EDGE + out_max - h, px);

	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 T3 = vec3(-g.y, 0.0, g.x);
	vec3 B3 = vec3(g.x, 0.0, g.y);
	vec3 nn = st_bend(up, T3, B3, (s.tilt + tw.yz * 0.2 * vis_tw) * s.cover);
	ALBEDO = acc.rgb;
	ALPHA = acc.a * keep;
	EMISSION = v_col * glow * 0.22 * s.cover;
	NORMAL = normalize((VIEW_MATRIX * vec4(nn, 0.0)).xyz);
	ROUGHNESS = 0.8;
	SPECULAR = 0.15;
}
