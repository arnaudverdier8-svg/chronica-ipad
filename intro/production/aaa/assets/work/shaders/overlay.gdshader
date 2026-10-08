shader_type spatial;
// Les SURLIGNAGES du plateau, cousus (docs/DIRECTION_TAPISSERIE.md) : pas
// d'anneau lumineux, des fils et des points posés sur la toile.
//   mode 0  VOILE      cases atteignables, territoire d'une ville : un voile
//                      de gaze à peine teinté et, au bord de la zone, un fin
//                      point devant à la couleur de la case (COLOR) : DISCRET,
//                      cousu SOUS les frontières ;
//   mode 1  ANNEAU     cibles d'attaque, chantier : un cordon couché à la
//                      couleur de la case, cerné de brun, fixations brunes ;
//   mode 2  DANGER     la zone des gobelins la nuit : hachures de points
//                      devant brique en biais, continues d'une case à l'autre ;
//   mode 3  CHEMIN     un segment de chemin : point devant qui avance, cerné ;
//   mode 4  SÉLECTION  un gros cordon d'or retors (tint), cerné de brun, qui
//                      tourne doucement : évident d'un coup d'œil ;
//   mode 5  SURVOL     un point devant crème autour de la case ;
//   mode 6  ARRIVÉE    le bout du chemin : une croix de point de croix et un
//                      cercle de points devant (tint).
// Chaque fil a son contour brun (ST_BRUN) et une ombre portée courte vers le
// bas-droite : il est posé SUR la toile, lisible sur le lin comme sur l'eau.
// Unshaded : la lumière est peinte (le fil rond s'éclaire côté haut-gauche,
// comme le soleil de Vis.PHASE_LIGHT) ; la nuit l'assombrit sans l'éteindre.
//
// Données : MultiMesh → COLOR = couleur de palette (sRGB) ; une pièce seule
// (sélection, survol) → instance uniform `tint`. Repère : l'origine de
// l'instance est le centre de la case ; le chemin (mode 3) est un ruban
// VERTEX.x ∈ [0, 1] (le long, mis à l'échelle du segment), VERTEX.z ∈
// [-0,5, 0,5] (en travers, mis à l'échelle de la largeur).
//
// COÛT : 0 hash ; st_hex ×2, st_running / st_couched ×1-2 selon le mode ;
// aucune boucle, aucune texture. Dérivées prises avant toute branche (le
// mode est un uniform : branche uniforme).

render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"

global uniform float g_night;
// Le tulle des cases atteignables (mode 0) : couverture du voile = x + y ×
// le filet (view/palettes.gd, shader.tulle).
global uniform vec2 g_tulle;
uniform int mode = 0;
uniform float pulse = 0.0;
uniform float alpha = 1.0;
instance uniform vec4 tint : source_color = vec4(1.0);
// Sélection : la distance-apothème du cordon (Overlays.select : en retrait
// sur une case nue, contre l'arête sur une ville, dont les murs cacheraient
// un anneau intérieur).
instance uniform float ring_r = 0.70;

varying vec3 wpos;
varying flat vec3 v_o;      // centre de la case (origine de l'instance)
varying vec3 v_col;         // couleur du fil, espace du renderer
varying vec2 v_seg;         // chemin : (le long, en travers) en unités monde
varying flat float v_len;   // chemin : longueur du segment
varying flat float v_mask;  // voile, danger : arêtes au bord de la zone (0..63) ;
                            // anneau : 63 = case nue, moins = une ville

// La couture d'une case (apothème de l'arête).
const float SEAM = 0.8660254;

// L'ombre portée : vers le bas-droite de l'écran (+x, +z), courte.
const vec2 SHADOW_OFS = vec2(0.022, 0.03);
// La lumière peinte vient du haut-gauche de l'écran.
const vec2 LIGHT_DIR = vec2(-0.7071, -0.7071);

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_o = MODEL_MATRIX[3].xyz;
	v_col = st_albedo(COLOR.rgb);
	v_mask = floor(COLOR.a * 63.0 + 0.5);
	v_len = length(MODEL_MATRIX[0].xyz);
	v_seg = vec2(VERTEX.x * v_len, VERTEX.z * length(MODEL_MATRIX[2].xyz));
}

// Poser une couche (couleur c, couverture a) PAR-DESSUS l'accumulé (non
// prémultiplié).
void over(inout vec4 acc, vec3 c, float a) {
	float oa = a + acc.a * (1.0 - a);
	acc.rgb = (c * a + acc.rgb * acc.a * (1.0 - a)) / max(oa, 1e-4);
	acc.a = oa;
}

// Le masque des arêtes au bord de la zone (bit d = Hex.DIRS[d], COLOR.a =
// masque / 63) : 1 si l'arête de normale n donne hors de la zone.
float edge_open(vec2 n) {
	float d = st_hex_dir(n);
	return mod(floor(v_mask / exp2(d) + 1e-3), 2.0);
}

// Un tulle : filet de fils fins dans trois directions (0°, 60°, 120°), pas
// S, demi-largeur hw. Rend la couverture (filtrée ; au loin, la moyenne).
float tulle(vec2 w, float S, float hw, float px) {
	vec2 n1 = vec2(0.0, 1.0);
	vec2 n2 = vec2(0.8660254, 0.5);
	vec2 n3 = vec2(-0.8660254, 0.5);
	float d1 = (fract(dot(w, n1) / S + 0.5) - 0.5) * S;
	float d2 = (fract(dot(w, n2) / S + 0.5) - 0.5) * S;
	float d3 = (fract(dot(w, n3) / S + 0.5) - 0.5) * S;
	float c = 1.0 - (1.0 - st_band(d1, hw, px)) * (1.0 - st_band(d2, hw, px)) * (1.0 - st_band(d3, hw, px));
	float m = 1.0 - pow(1.0 - 2.0 * hw / S, 3.0);
	return mix(m, c, st_fade(S, px));
}

// Le point de chaînette : une suite de boucles (ellipses de demi-axes
// 0,55·L le long et hw en travers), fil de demi-largeur tw. Au loin, les
// boucles fondent en leur couverture moyenne.
float chain(float along, float across, float L, float hw, float tw, float px) {
	float a = (fract(along / L + 0.5) - 0.5) * L;
	vec2 q = vec2(a / (0.55 * L), across / hw);
	float d = (length(q) - 1.0) * min(0.55 * L, hw);
	float c = st_band(d, tw, px);
	float m = st_band(across, hw, px) * 0.45;
	return mix(m, c, st_fade(L * 0.5, px));
}

// La lumière peinte d'un fil : tilt (le long, en travers) dans le repère
// (T, B) du plan monde.
float lit(vec2 tilt, vec2 T, vec2 B) {
	return 1.0 + 0.5 * dot(tilt.x * T + tilt.y * B, LIGHT_DIR);
}

void fragment() {
	// --- Dérivées et repères d'abord, hors de toute branche. -----------------
	float px = st_px(wpos.xz);
	vec2 p = wpos.xz - v_o.xz;
	float t;
	vec2 en;
	float h = st_hex(p, t, en);
	float ts;
	vec2 ens;
	float hs = st_hex(p - SHADOW_OFS, ts, ens);
	vec2 Te = vec2(-en.y, en.x);
	vec3 thread = v_col * tint.rgb;
	vec3 brun = st_albedo(ST_BRUN);
	vec4 acc = vec4(thread, 0.0);
	float pul = 0.5 + 0.5 * sin(TIME * 3.0);

	if (mode == 0) {
		// VOILE (DISCRET : sous les frontières dans la hiérarchie) : un tulle
		// léger (filet hexagonal de fils fins) à la couleur de la case, continu
		// d'une case à l'autre, et, au bord de la zone seulement (masque
		// d'arêtes), un fin point devant en retrait de la couture (la grille y
		// coud déjà ses tirets crème), avec une ombre courte pour tenir sur le
		// lin. Une frontière cousue au même endroit le recouvre.
		const float ZR = 0.775;
		float inside = 1.0 - st_step(h - SEAM, px);
		float net = tulle(wpos.xz, 0.09, 0.0055, px);
		over(acc, thread, inside * (g_tulle.x + g_tulle.y * net));
		float open = edge_open(en);
		float hs_open = edge_open(ens);
		StThread zs = st_hex_running(p - SHADOW_OFS, ZR, 0.1, 0.05, 0.032, px);
		over(acc, brun, zs.cover * hs_open * 0.32);
		StThread z = st_hex_running(p, ZR, 0.1, 0.05, 0.026, px);
		over(acc, thread * z.shade * lit(z.tilt, Te, en), z.cover * open);
	} else if (mode == 1) {
		// ANNEAU : cordon couché à la couleur de la case, en retrait de
		// l'arête comme la sélection (la frontière court contre elle) ; sur
		// une ville (alpha < 1, Overlays.show_rings), contre l'arête : ses
		// murs cacheraient un anneau intérieur.
		float RING = v_mask > 47.0 ? 0.72 : 0.80;
		const float HW = 0.032;
		over(acc, brun, st_band(hs - RING, HW + 0.01, px) * 0.35);
		over(acc, brun, st_band(h - RING, HW + 0.014, px) * 0.9);
		StThread c = st_couched(t - TIME * 0.05 * pulse, h - RING, HW, 0.07, 0.16, px);
		vec3 cc = thread * c.shade * lit(c.tilt, Te, en) * (1.0 + 0.12 * pulse * (pul - 0.5));
		over(acc, cc, c.cover);
		over(acc, brun * 1.2, c.tie);
	} else if (mode == 2) {
		// DANGER : hachures de points devant brique en biais (monde :
		// continues d'une case à l'autre), et des tirets brique sur la
		// couture, au bord de la zone seulement. Le danger se montre au
		// crépuscule et la nuit : le fil brique est relevé pour y tenir.
		const float S = 0.17;
		thread = min(thread * 1.5, vec3(1.0));
		vec2 d1 = vec2(0.7071, -0.7071);
		vec2 d2 = vec2(0.7071, 0.7071);
		float along = dot(wpos.xz, d1);
		float across = (fract(dot(wpos.xz, d2) / S + 0.5) - 0.5) * S;
		float keep = 1.0 - st_step(h - SEAM, px);
		StThread hzo = st_running(along, across, 0.075, 0.05, 0.046, px);
		over(acc, brun, hzo.cover * keep * 0.5);
		StThread hz = st_running(along, across, 0.075, 0.05, 0.026, px);
		over(acc, thread * hz.shade * lit(hz.tilt, d1, d2), hz.cover * keep * 0.9);
		float open = edge_open(en);
		StThread eo = st_hex_running(p, SEAM, 0.09, 0.05, 0.07, px);
		over(acc, brun, eo.cover * open * 0.85);
		StThread e = st_hex_running(p, SEAM, 0.09, 0.05, 0.042, px);
		over(acc, thread * e.shade * lit(e.tilt, Te, en), e.cover * open);
	} else if (mode == 3) {
		// CHEMIN : point devant qui avance de case en case.
		float along = v_seg.x - TIME * 0.12;
		StThread sh = st_running(along, v_seg.y - SHADOW_OFS.y, 0.12, 0.07, 0.07, px);
		over(acc, brun, sh.cover * 0.35);
		StThread ol = st_running(along, v_seg.y, 0.12, 0.07, 0.075, px);
		over(acc, brun, ol.cover * 0.9);
		StThread s = st_running(along, v_seg.y, 0.12, 0.07, 0.045, px);
		// (Repère du ruban : le long ≈ l'axe du segment ; la lumière peinte
		// se contente du rond du fil, côté haut.)
		over(acc, thread * s.shade * (1.0 - 0.2 * s.tilt.y), s.cover);
		// Pas sous la pièce de départ ni d'arrivée : le fil part du bord.
		acc.a *= smoothstep(0.22, 0.32, v_seg.x) * smoothstep(0.22, 0.32, v_len - v_seg.x);
	} else if (mode == 4) {
		// SÉLECTION : un gros cordon d'or retors, cerné de brun, cousu en
		// retrait de l'arête (ring_r ; le cordon des frontières court contre
		// elle : on lit les deux, et la sélection ne se confond pas avec la
		// frontière d'or du joueur). Sur une ville, contre l'arête, par-dessus
		// la frontière.
		float RING = ring_r;
		const float HW = 0.056;
		over(acc, brun, st_band(hs - RING, HW + 0.02, px) * 0.45);
		over(acc, brun, st_band(h - RING, HW + 0.02, px));
		StThread c = st_couched(t + TIME * 0.06 * pulse, h - RING, HW, 0.1, 0.25, px);
		vec3 cc = thread * c.shade * lit(c.tilt, Te, en);
		// Le reflet de la soie, côté lumière (effacé si le cordon est fin).
		cc *= 1.0 + 0.25 * st_sheen(c.u, -0.35, 0.45) * st_fade(HW * 2.0, px);
		over(acc, cc, c.cover);
		over(acc, brun * 1.3, c.tie);
		// Un voile d'or pâle dedans : la case choisie se lit même sous une pièce.
		over(acc, thread, (1.0 - st_step(h - (RING - HW - 0.02), px)) * 0.12);
	} else if (mode == 5) {
		// SURVOL : un anneau de point de chaînette crème sur un liseré brun,
		// en retrait de l'arête (sous la sélection, hors de la frontière).
		const float RING = 0.72;
		over(acc, brun, st_band(h - RING, 0.04, px) * 0.55);
		float ch = chain(t, h - RING, 0.1, 0.032, 0.009, px);
		over(acc, thread, ch);
	} else {
		// ARRIVÉE : une croix de point de croix et un cercle de points devant.
		float r = length(p);
		const float CR = 0.34;
		vec2 rd = p / max(r, 1e-4);
		float ang = atan(p.y, p.x);
		// 13 points tout rond (le pas tombe juste : pas de raccord boiteux).
		float ca = ang / ST_TAU * 13.0 * 0.16;
		StThread ring_ol = st_running(ca, r - CR, 0.1, 0.06, 0.06, px);
		over(acc, brun, ring_ol.cover * 0.85);
		StThread ring = st_running(ca, r - CR, 0.1, 0.06, 0.035, px);
		over(acc, thread * ring.shade * lit(ring.tilt, vec2(-rd.y, rd.x), rd), ring.cover);
		// La croix : deux points droits croisés (point de croix), le second
		// par-dessus ; bouts arrondis, cernés de brun.
		vec2 a1 = vec2(0.7071, 0.7071);
		vec2 a2 = vec2(0.7071, -0.7071);
		const float L = 0.17;
		float u1 = dot(p, a1);
		float v1 = dot(p, a2);
		float o1 = st_band(v1, 0.04, px) * st_band(u1, L + 0.03, px);
		float o2 = st_band(u1, 0.04, px) * st_band(v1, L + 0.03, px);
		float c1 = st_band(v1, 0.024, px) * st_band(u1, L, px);
		float c2 = st_band(u1, 0.024, px) * st_band(v1, L, px);
		float sh = st_band(dot(p - SHADOW_OFS, a2), 0.04, px) * st_band(dot(p - SHADOW_OFS, a1), L + 0.03, px);
		sh = max(sh, st_band(dot(p - SHADOW_OFS, a1), 0.04, px) * st_band(dot(p - SHADOW_OFS, a2), L + 0.03, px));
		over(acc, brun, sh * 0.35);
		over(acc, brun, o1 * 0.9);
		float r1 = clamp(v1 / 0.024, -1.0, 1.0);
		over(acc, thread * (1.0 + 0.12 * (0.3333 - r1 * r1)) * lit(vec2(0.0, st_round(r1) * 0.4), a1, a2), c1);
		over(acc, brun, o2 * 0.9);
		float r2 = clamp(u1 / 0.024, -1.0, 1.0);
		over(acc, thread * (1.0 + 0.12 * (0.3333 - r2 * r2)) * lit(vec2(0.0, st_round(r2) * 0.4), a2, a1), c2);
	}

	ALBEDO = acc.rgb * mix(1.0, 0.72, g_night);
	ALPHA = acc.a * alpha;
}
