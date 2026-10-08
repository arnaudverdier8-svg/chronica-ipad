shader_type spatial;
// La SÉLECTION vue à travers les pièces : le cordon de overlay.gdshader
// (mode 4) simplifié (un cordon uni cerné de brun, sans torsade), pâli, et
// dessiné SANS test de profondeur. Il passe AVANT le vrai cordon (Overlays :
// priorité de rendu plus basse) : là où le sol se voit, le vrai cordon le
// recouvre tout entier ; il ne reste visible que là où le vrai est caché
// (les murs d'une ville, une futaie) : la sélection reste évidente sur
// iPad, même sous une ville. Il ne passe PAS sur les figurines en carte
// brodée (pochoir, bit 4, écrit par figure.gdshader) : debout et couchée
// vers le nord, la carte de l'unité choisie croise le bord nord de sa case,
// et le fantôme lui barrait le visage.
// COÛT par pixel : 0 hash ; st_hex et deux bandes. Un appel de dessin, et
// seulement quand une case est choisie.

render_mode unshaded, blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, shadows_disabled, fog_disabled;
stencil_mode read, compare_not_equal, 4;

#include "res://view/shaders/stitch.gdshaderinc"

global uniform float g_night;
uniform float alpha = 0.5;
instance uniform vec4 tint : source_color = vec4(1.0);
// La distance-apothème du cordon (la même que celle du vrai : Overlays.select).
instance uniform float ring_r = 0.70;

// La demi-largeur du cordon (overlay.gdshader, mode 4) et son liseré.
const float HW = 0.056;
const float OL = 0.02;

varying vec3 wpos;
varying flat vec3 v_o;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_o = MODEL_MATRIX[3].xyz;
}

void fragment() {
	float px = st_px(wpos.xz);
	vec2 p = wpos.xz - v_o.xz;
	float t;
	vec2 en;
	float h = st_hex(p, t, en);
	float ol = st_band(h - ring_r, HW + OL, px);
	float c = st_band(h - ring_r, HW, px);
	vec3 col = mix(st_albedo(ST_BRUN), tint.rgb, clamp(c / max(ol, 1e-4), 0.0, 1.0));
	ALBEDO = col * mix(1.0, 0.72, g_night);
	ALPHA = ol * alpha;
}
