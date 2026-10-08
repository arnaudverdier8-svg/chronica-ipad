shader_type spatial;
// Les PARTICULES de la tapisserie (view/fx.gd) : pas de lueur additive, des
// brins de fil, des touffes de laine et des points de croix qui volent.
//   shape 0  TOUFFE  une touffe de laine (fumée, poussière, nuage, neige) :
//                    disque doux aux bords fibreux ;
//   shape 1  BRIN    un brin de fil coupé, un peu courbe (étincelles, coups,
//                    feuilles mortes) : rond en travers, bouts effilés ;
//   shape 2  CROIX   un petit point de croix (or, chantier achevé).
// Les brins et les croix sont cernés de brun (ST_BRUN), comme tout fil.
// Billboard des particules (l'équivalent de BILLBOARD_PARTICLES : la
// rotation de la particule est dans INSTANCE_CUSTOM.x). COLOR = couleur de
// palette (sRGB) et opacité de la rampe. Unshaded, assombri la nuit.
// COÛT : 0 hash, aucune texture (la forme est calculée sur UV).

render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"

global uniform float g_night;
uniform int shape = 0;

varying vec4 v_col;

void vertex() {
	mat4 mw = mat4(normalize(INV_VIEW_MATRIX[0]), normalize(INV_VIEW_MATRIX[1]), normalize(INV_VIEW_MATRIX[2]), MODEL_MATRIX[3]);
	float a = INSTANCE_CUSTOM.x;
	mw = mw * mat4(vec4(cos(a), -sin(a), 0.0, 0.0), vec4(sin(a), cos(a), 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * mw;
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0), vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
	v_col = vec4(st_albedo(COLOR.rgb), COLOR.a);
}

void fragment() {
	vec2 q = UV * 2.0 - 1.0;
	float fw = max(fwidth(q.x), 1e-3);
	vec3 col = v_col.rgb;
	vec3 brun = st_albedo(ST_BRUN);
	float a;
	if (shape == 0) {
		// TOUFFE : bord fibreux (la laine s'effiloche), cœur un peu plus clair.
		float r = length(q);
		float ang = atan(q.y, q.x);
		float fib = 0.82 + 0.12 * sin(ang * 7.0 + 1.3) + 0.06 * sin(ang * 17.0);
		a = 1.0 - smoothstep(0.35 * fib, 0.95 * fib, r);
		col *= 1.0 + 0.10 * (1.0 - r);
	} else if (shape == 1) {
		// BRIN : un fil courbe, effilé aux deux bouts, rond en travers.
		float y = q.y + 0.3 * q.x * q.x - 0.15;
		float hw = 0.2 * (1.0 - 0.5 * q.x * q.x);
		float body = 1.0 - smoothstep(hw - fw, hw + fw, abs(y));
		float ends = 1.0 - smoothstep(0.85 - fw, 0.85 + fw, abs(q.x));
		float edge = 1.0 - smoothstep(hw + 0.08 - fw, hw + 0.08 + fw, abs(y));
		float u = clamp(y / max(hw, 1e-3), -1.0, 1.0);
		col *= 1.0 + 0.18 * (0.3333 - u * u) - 0.15 * u;
		col = mix(brun, col, body);
		a = max(body, edge * 0.8) * ends;
	} else {
		// CROIX : deux points droits croisés, le second par-dessus.
		float d1 = abs(q.x - q.y) * 0.7071;
		float d2 = abs(q.x + q.y) * 0.7071;
		float box = 1.0 - smoothstep(0.72 - fw, 0.72 + fw, max(abs(q.x), abs(q.y)));
		float b1 = 1.0 - smoothstep(0.15 - fw, 0.15 + fw, d1);
		float b2 = 1.0 - smoothstep(0.15 - fw, 0.15 + fw, d2);
		float o = 1.0 - smoothstep(0.24 - fw, 0.24 + fw, min(d1, d2));
		col = mix(brun, col * (1.0 + 0.1 * (1.0 - d2 * 6.0)), max(b1, b2));
		a = max(o * 0.85, max(b1, b2)) * box;
	}
	ALBEDO = col * mix(1.0, 0.7, g_night);
	ALPHA = a * v_col.a;
}
