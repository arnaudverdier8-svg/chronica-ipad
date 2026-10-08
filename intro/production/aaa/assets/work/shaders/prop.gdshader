shader_type spatial;
// Les décors brodés en relief (sapins, feuillus, buissons, rochers, collines,
// monts), en MultiMesh. Même broderie que les pièces (stitch_pieces :
// projection oblique, éclairage de broderie couchée, satin par facette) ;
// le contour brun est cousu dans le maillage (Props, Models.Merge : la coque,
// UV2 non nul) et tracé dans le même appel de dessin (pc_outline).
//
// Convention de couleur de sommet (view/props.gd) :
//   a = 1     feuillage caduc : couleur de saison `leaf` × nuance (r)
//   a = 0,75  neige des sommets : crème × nuance (r), en toute saison
//   a = 0,5   aiguilles : `pine` × nuance (r)
//   a = 0,25  sol de colline : entre l'ocre et l'olive (g : part d'olive) ×
//             valeur (r) ; le satin y suit les COURBES DE NIVEAU (rangs
//             horizontaux empilés en hauteur : les rangs de contour de la cible)
//   a = 0     bois ou pierre : rgb = couleur de palette (sRGB)
// UV.x (les pics) : 1 sur une arête, 0 au creux du versant : une ARÊTE CLAIRE
// (un fil crème couché) y est cousue sur la roche ; ailleurs UV = 0, rien.
// L'hiver, la neige (crème, jamais blanche) couvre ce qui regarde le ciel.
// Coût : 1 hash (le satin), 1 fwidth, aucune boucle, aucune texture.

render_mode skip_vertex_transform, diffuse_lambert, specular_disabled, shadows_disabled;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"

uniform vec3 leaf : source_color = vec3(0.43, 0.48, 0.26);
uniform vec3 pine : source_color = vec3(0.22, 0.24, 0.16);
uniform vec3 ground : source_color = vec3(0.64, 0.53, 0.33);
uniform float snow = 0.0;
// Le contour (la coque) : épaisseur visée en unités monde, bornée en pixels.
uniform float width_world = 0.02;
uniform float width_min = 1.2;
uniform float width_max = 2.4;
uniform float ref_h = 1200.0;

global uniform float g_night;
global uniform vec4 g_veil;

// Pas des rangs de contour des collines (plus fin que le satin des décors :
// quatre à cinq rangs sur un monticule).
const float CONTOUR_W = 0.034;
// Demi-largeur de l'arête claire, en part de UV (1 sur l'arête, 0 au creux).
const float RIDGE_HW = 0.15;

varying vec3 v_q;
varying vec3 v_nm;
varying vec3 v_nw;
varying vec3 v_col;
varying float v_ridge;
varying flat float v_cat;
varying flat float v_hull;  // 1 sur la coque

void vertex() {
	v_hull = pc_is_hull(UV2);
	if (v_hull > 0.5) {
		vec3 nv;
		VERTEX = pc_outline(VERTEX, NORMAL, UV2, MODEL_MATRIX, MODEL_NORMAL_MATRIX, VIEW_MATRIX, PROJECTION_MATRIX,
				width_world, width_min, width_max, ref_h, nv);
		NORMAL = nv;
		v_q = vec3(0.0);
		v_nm = vec3(0.0, 1.0, 0.0);
		v_nw = v_nm;
		v_col = vec3(0.0);
		v_ridge = 0.0;
		v_cat = 0.0;
	} else {
		vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		vec3 nw = normalize(MODEL_NORMAL_MATRIX * NORMAL);
		v_q = VERTEX * length(MODEL_MATRIX[0].xyz);
		v_nm = NORMAL;
		v_nw = nw;
		v_ridge = UV.x;
		// La couleur du fil, une fois par sommet (uniform source_color : tel quel ;
		// couleur de palette du sommet : st_albedo).
		float a = COLOR.a;
		float r = COLOR.r;
		v_cat = a;
		vec3 c = st_albedo(COLOR.rgb);
		if (a > 0.875) {
			c = leaf * (0.6 + r * 0.34);
		} else if (a > 0.625) {
			c = st_albedo(vec3(0.87, 0.83, 0.75)) * (0.92 + r * 0.14);
		} else if (a > 0.375) {
			c = pine * (0.8 + r * 0.45);
		} else if (a > 0.125) {
			// Les monticules : des bandes d'ocre doré et d'olive en alternance (g),
			// tirées du sol de colline de la saison, plus claires vers le sommet (r).
			// L'hiver, le sol pâle de la saison domine (la neige tient sur les
			// replats, voir fragment()).
			vec3 ochre = mix(ground, st_albedo(ST_OR), 0.55 * (1.0 - 0.6 * snow));
			vec3 olive = mix(ground, st_albedo(mix(ST_SAPIN_CLAIR, ST_BRUN, 0.55)), 0.75 * (1.0 - 0.55 * snow)) * mix(0.80, 0.9, snow);
			c = mix(ochre, olive, COLOR.g) * (0.78 + r * 0.34);
		}
		v_col = c;
		VERTEX = (VIEW_MATRIX * vec4(pc_shear(w, 1.0), 1.0)).xyz;
		NORMAL = normalize((VIEW_MATRIX * vec4(pc_shear_normal(nw, 1.0), 0.0)).xyz);
	}
}

void fragment() {
	// Dérivées d'abord, hors de toute branche.
	float px = pc_px(v_q);
	float fw = max(fwidth(v_ridge), 1e-5);
	float rim = st_rim(NORMAL, VIEW, 0.16);

	if (v_hull > 0.5) {
		// La coque : le fil brun, ni éclairé ni voilé (voir piece.gdshader).
		ALBEDO = vec3(0.0);
		EMISSION = pc_hull_color(g_night);
		FOG = vec4(0.0);
	} else {
		vec3 nm = normalize(v_nm);
		vec3 nw = normalize(v_nw);
		vec3 T;
		vec3 B;
		vec2 uv = pc_uv(nm, v_q, T, B);
		// Les monticules de colline : le fil suit les courbes de niveau (le long
		// de l'horizontale de la facette), les rangs s'empilent en hauteur.
		float contour = step(0.125, v_cat) * step(v_cat, 0.375);
		vec3 th = vec3(-nm.z, 0.0, nm.x);
		float lh = length(th);
		if (contour > 0.5 && lh > 0.25) {
			T = th / lh;
			B = normalize(cross(nm, T));
			uv = vec2(dot(v_q, T), v_q.y);
		}
		float sw = mix(PC_PROP_W, CONTOUR_W, contour);
		StThread s = st_satin(uv, sw, PC_PROP_LEN, 0.61, 0.4, 0.07, px);

		vec3 base = v_col;
		// L'arête claire des pics : un fil crème couché sur la roche, filtré (il
		// pâlit s'il devient plus fin qu'un pixel, il ne crépite pas).
		float ridge = st_band(1.0 - v_ridge, RIDGE_HW, fw) * step(v_cat, 0.125) * step(1e-3, v_ridge);
		base = mix(base, st_albedo(ST_CREME) * 0.9, ridge * 0.85);
		// Une facette est enneigée ou ne l'est pas (transition courte : pas de
		// rose sur les toits ni de gris sale) ; la neige est un fil crème, terni
		// pour rester sous le blanc une fois éclairé.
		float sn = snow * smoothstep(0.8, 0.86, nw.y);
		base = mix(base, st_albedo(vec3(0.83, 0.815, 0.77)), sn);

		vec3 col = st_paint(base * 0.62, base, s);
		col += base * st_sheen(s.u, -0.3, 0.6) * 0.22 * st_fade(sw, px);
		col = mix(col, st_albedo(ST_BRUN), rim * 0.6);
		ALBEDO = col;

		vec3 Tw = normalize(mat3(MODEL_MATRIX) * T);
		vec3 Bw = normalize(mat3(MODEL_MATRIX) * B);
		vec3 nl = pc_relief(st_bend(nw, Tw, Bw, s.tilt * s.cover));
		NORMAL = normalize((VIEW_MATRIX * vec4(nl, 0.0)).xyz);
		// Le voile de la veille (écrire FOG remplace celui du moteur).
		FOG = pc_veil(VERTEX, g_veil);
	}
}
