shader_type spatial;
// L'eau brodée (direction tapisserie, docs/DIRECTION_TAPISSERIE.md).
//   - La mer et les lacs : une toile de rangs couchés bleu denim, semée de
//     vaguelettes en point devant crème posées en rangées ; le quadrillage
//     des cases en point devant crème fin ; le long des côtes, l'eau
//     s'assombrit contre la pièce de terre et un point devant crème l'ourle.
//   - Les cases de rivière ne sont pas ici : ce sont des pièces de terre
//     (Meshes.terrain), où terrain.gdshader couche le cordon bleu clair. La
//     côte s'ouvre là où une rivière se jette (embouchure).
//   - L'hiver, les lacs gèlent (couleurs de la saison) : les vagues
//     deviennent des fêlures droites.
// Aucune texture : tout vient des sommets (view/meshes.gd, Meshes.water) ;
// voir là-bas le sens de UV, UV2 et COLOR.
// Coût par pixel : 2 hash (satin + semis de vagues), aucune boucle ; toutes
// les dérivées avant la moindre branche.

render_mode cull_back, diffuse_lambert, specular_schlick_ggx;

#include "res://view/shaders/stitch.gdshaderinc"

// Couleurs de palette de la saison (sRGB, Vis.TERRAIN_COLORS) : sans
// source_color, donc passées par st_albedo.
uniform vec3 sea_col = vec3(0.212, 0.278, 0.318);
uniform vec3 lake_col = vec3(0.243, 0.322, 0.369);
// (Board règle encore river_col et bank_col : les rivières sont brodées par
// terrain.gdshader, ces deux couleurs ne servent plus ici.)
// 1 l'hiver : lacs pris par la glace.
uniform float ice = 0.0;
// 0 le jour, 1 la nuit.
uniform float night = 0.0;

varying vec3 wpos;
varying vec2 lp;
varying vec2 v_data;
varying vec3 v_info;

const float APO = 0.8660254;   // distance-apothème des arêtes (case de rayon 1)
const vec3 UP = vec3(0.0, 1.0, 0.0);
const vec3 AX = vec3(1.0, 0.0, 0.0);
const vec3 AZ = vec3(0.0, 0.0, 1.0);
// Les réglages de la préselection (uniforms globaux posés par
// Vis.use_palette ; défauts de « tapisserie » dans project.godot) :
// le fil de l'eau, × sea_col / lake_col (« tapisserie » : 1,30 ; 1,22 ; 1,17,
// mesuré sur la cible, #415054 entre les vagues : le denim de la palette, un
// rien plus gris et plus clair ; 1 : la couleur de palette est celle du fil) ;
// la toile sous ses rangs, × la couleur (0,8) ; la marbrure lente (0,07).
global uniform vec3 g_water_tint;
global uniform float g_water_under;
global uniform float g_water_mott;
#define WATER_TINT g_water_tint

// Le bit d (0..5) d'un masque entier porté par un float déjà arrondi.
float bit(float m, float d) {
	return mod(floor(m / exp2(d)), 2.0);
}

// La normale sortante de l'arête qui regarde Hex.DIRS[d] (plan xz).
vec2 dirn(float d) {
	float a = -d * (ST_PI / 3.0);
	return vec2(cos(a), sin(a));
}

// Des rangs de fil couché longs et plats (le satin de la bibliothèque, aux
// bouts adoucis : de longs rangs, pas un mur de briques), chaque rang de sa
// valeur. Moyennes inchangées.
StThread rows(vec2 uv, float w, float len, float seed, float bump, float jit, float px) {
	StThread s = st_satin(uv, w, len, seed, bump, jit, px);
	float f = st_fade(w, px);
	s.shade = 1.0 + (s.shade - 1.0) * 0.5;
	s.tilt.x *= 0.4;
	s.cover = 1.0 - (1.0 - s.cover) * 0.3;
	s.shade *= 1.0 - 0.28 * (s.u * s.u - 0.3333) * f;
	float row = floor(uv.y / w);
	s.shade *= 1.0 + (fract(row * 0.6180339 + seed * 7.0) - 0.5) * 0.12 * f;
	return s;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	lp = UV;
	v_data = UV2;
	v_info = COLOR.rgb;
}

void fragment() {
	// --- Tout ce qui dérive d'abord, hors de toute branche. ----------------
	float px = st_px(wpos.xz);
	vec2 p = lp;
	float et;
	vec2 en;
	float h = st_hex(p, et, en);
	float side = st_hex_dir(en);
	float kind = floor(v_info.g * 2.0 + 0.5);          // 0 mer, 1 lac
	float outer = step(0.5, v_info.b);
	float frozen = step(0.5, v_info.r) * ice;
	float hem = floor(v_data.x + 0.5);
	float code = floor(v_data.y + 0.5);
	float on_hem = bit(hem, side);
	vec3 Te = vec3(-en.y, 0.0, en.x);   // le long de l'arête la plus proche
	vec3 Be = vec3(en.x, 0.0, en.y);    // vers l'arête (sortant)
	vec3 col;
	vec3 n;

	// ================= LA MER, UN LAC =================
	vec3 wcol = st_albedo(kind > 0.5 ? lake_col : sea_col);
	// Une marbrure lente (deux ondes, sans hash) : la teinte du fil
	// change d'un écheveau à l'autre.
	float mott = sin(wpos.x * 0.37 + sin(wpos.z * 0.29) * 1.7) * sin(wpos.z * 0.43 - wpos.x * 0.11);
	// Les rangs ondulent un peu (la main de la brodeuse) ; des points
	// assez courts pour que leurs bouts donnent du grain à la laine.
	float wob = 0.012 * sin(wpos.x * 3.1 + wpos.z * 0.9) + 0.006 * sin(wpos.x * 11.0 - wpos.z * 2.3);
	vec3 thread = wcol * mix(WATER_TINT, vec3(1.05), frozen) * (1.0 + g_water_mott * mott);
	// D'un rang à l'autre, le fil n'est pas du même bain : un plus bleu,
	// un plus gris (moyenne 1, effacé au loin).
	float rv = fract(floor((wpos.z + wob) / 0.044) * 0.7548777 + 0.3);
	thread *= mix(vec3(1.0), mix(vec3(0.92, 0.96, 1.03), vec3(1.08, 1.04, 0.97), rv), st_fade(0.044, px));
	StThread s = rows(vec2(wpos.x, wpos.z + wob), 0.044, 0.36, 0.71, 0.3, 0.07, px);
	s.shade *= 1.0 - 0.12 * (s.u * s.u - 0.3333) * st_fade(0.044, px);
	col = st_paint(wcol * g_water_under, thread, s);
	vec2 tilt = s.tilt * s.cover;
	// La houle : un reflet très lent qui passe sur l'eau libre.
	tilt.y += 0.06 * sin(dot(wpos.xz, vec2(0.42, 0.23)) - TIME * 0.35) * (1.0 - frozen);
	n = st_bend(UP, AX, AZ, tilt);

	// La côte : distance à la plus proche arête ourlée (six arêtes, sans
	// boucle) ; une embouchure ouvre la côte autour du milieu de l'arête.
	float e0 = p.x;
	float e1 = 0.5 * p.x - APO * p.y;
	float e2 = -0.5 * p.x - APO * p.y;
	float dc = 9.0;
	dc = min(dc, mix(9.0, APO - e0, bit(hem, 0.0)));
	dc = min(dc, mix(9.0, APO - e1, bit(hem, 1.0)));
	dc = min(dc, mix(9.0, APO - e2, bit(hem, 2.0)));
	dc = min(dc, mix(9.0, APO + e0, bit(hem, 3.0)));
	dc = min(dc, mix(9.0, APO + e1, bit(hem, 4.0)));
	dc = min(dc, mix(9.0, APO + e2, bit(hem, 5.0)));
	float mouth = (1.0 - outer) * bit(code, side);
	float open = mouth * (1.0 - smoothstep(0.19, 0.25, abs(et)));

	// Les vaguelettes : en rangées décalées (une cellule de 0,72 × 0,27,
	// une rangée sur deux glissée d'une demi-cellule), un trait ondulé
	// par cellule, présent un peu plus d'une fois sur deux : trois ondes,
	// six arcs de point devant crème (un point par crête ou par creux).
	vec2 cell = vec2(0.72, 0.27);
	vec2 q = wpos.xz / cell;
	float rowi = floor(q.y);
	q.x += 0.5 * mod(rowi, 2.0);
	vec2 ci = floor(q);
	vec2 wh = st_hash22(ci + vec2(85.0, 295.0));
	vec2 lw = (q - ci - 0.5 - (wh - 0.5) * vec2(0.22, 0.2)) * cell;
	float wl = 0.17 + 0.06 * fract(wh.x * 7.3);    // demi-longueur
	float lam = wl / 1.5;                           // trois ondes
	float amp = mix(0.017, 0.0, frozen) * (step(0.5, wh.y) * 2.0 - 1.0);
	float acr = lw.y - amp * sin(ST_TAU * (lw.x + wl) / lam);
	StThread w = st_running(lw.x + wl - 0.25 * lam, acr, lam * 0.42, lam * 0.08, 0.023, px);
	w.cover *= step(fract(wh.x * 3.1 + wh.y * 1.7), 0.56) * st_band(lw.x, wl, px)
		* smoothstep(0.24, 0.34, dc);
	vec3 wave_col = mix(st_albedo(ST_CREME) * 0.93, wcol * 0.7, frozen);
	col = st_paint(col, wave_col * (1.0 + 0.12 * night), w);
	n = normalize(mix(n, st_bend(UP, AX, AZ, w.tilt), w.cover));

	// Le quadrillage des cases : point devant crème fin. Chaque case coud
	// sa moitié du fil, la voisine l'autre ; en haute mer, seulement les
	// arêtes qui touchent la carte (son bord est cousu, le large est nu).
	StThread gr = st_hex_running(p, APO, 0.075, 0.05, 0.022, px);
	gr.cover *= (1.0 - on_hem) * mix(1.0, bit(code, side), outer) * 0.75;
	col = st_paint(col, st_albedo(ST_CREME) * 0.86, gr);

	// L'ourlet : l'eau s'assombrit contre la pièce de terre rembourrée,
	// puis un point devant crème court le long de la côte.
	float shore = (1.0 - smoothstep(0.0, 0.14, dc)) * (1.0 - open);
	col *= 1.0 - 0.28 * shore;
	StThread hm = st_hex_running(p, APO - 0.075, 0.085, 0.045, 0.026, px);
	hm.cover *= on_hem * (1.0 - open);
	col = st_paint(col, st_albedo(ST_CREME) * 0.82, hm);
	n = normalize(mix(n, st_bend(UP, Te, Be, hm.tilt), hm.cover));
	// La nuit, la lune bleuit déjà tout : l'eau perd un peu de sa
	// couleur pour ne pas virer au bleu électrique.
	col = mix(col, st_luma(col) * vec3(1.06, 1.0, 0.9), 0.6 * night);

	ALBEDO = col;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = 0.8;
	METALLIC = 0.0;
	SPECULAR = 0.2;
}
