shader_type spatial;
// Les routes (direction tapisserie) : un point devant brun, discret, qui
// serpente d'un centre de case à l'autre sur un chemin à peine foulé
// (view/meshes.gd, Meshes.roads : une bande par lien, du centre jusqu'au
// milieu de l'arête ; la case voisine coud l'autre moitié).
//   UV : (le long depuis le centre, en travers) ; UV2 : (longueur, graine) ;
//   COLOR.a : 1 un lien, 0 le nœud d'une route isolée.
// Coût par pixel : 0 hash.

render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;

#include "res://view/shaders/stitch.gdshaderinc"

// Le fil de chemin : un brun moyen, plus clair que le contour (ST_BRUN).
const vec3 ROAD = vec3(0.400, 0.290, 0.165);
// Les points : longueur, espace (un point tombe pile sur l'arête), épaisseur.
const float LEN = 0.075;
const float GAP = 0.0427;
const float W = 0.04;
// Le carrefour reste nu (une ville, un chantier s'y posent).
const float START = 0.16;

varying vec3 wpos;
varying vec2 v_uv;
varying vec2 v_aux;
varying float v_link;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_uv = UV;
	v_aux = UV2;
	v_link = COLOR.a;
}

void fragment() {
	float px = st_px(wpos.xz);
	float L = max(v_aux.x, 1e-3);
	float s = clamp(v_uv.x / L, 0.0, 1.0);
	// Le méandre : nul et à plat au centre comme à l'arête.
	float mea = 0.055 * sin(ST_TAU * s) * sin(ST_PI * s) * (v_aux.y * 2.0 - 1.0);
	float along = v_uv.x - START;
	float across = v_uv.y - mea;
	float from_center = st_step(v_uv.x - (START - 0.05), px);
	if (v_link < 0.5) {
		// Une route isolée : un petit anneau de points.
		vec2 q = vec2(v_uv.x - 0.22, v_uv.y);
		along = atan(q.y, q.x) * 0.14 + 0.44;
		across = length(q) - 0.14;
		from_center = 1.0;
	}
	StThread d = st_running(along, across, LEN, GAP, W, px);
	d.cover *= from_center;
	// Le chemin foulé : une bande de lin à peine plus sombre sous les points.
	float trod = st_band(across, 0.07, px) * 0.16 * from_center;
	vec3 col = st_albedo(ROAD) * d.shade;
	float a = max(d.cover, trod);
	col = mix(st_albedo(ROAD) * 0.75, col, clamp(d.cover / max(a, 1e-4), 0.0, 1.0));
	vec3 up = vec3(0.0, 1.0, 0.0);
	ALBEDO = col;
	ALPHA = a * 0.92;
	NORMAL = normalize((VIEW_MATRIX * vec4(st_bend(up, vec3(1.0, 0.0, 0.0), vec3(0.0, 0.0, 1.0), d.tilt * 0.6), 0.0)).xyz);
	ROUGHNESS = 0.9;
	SPECULAR = 0.05;
}
