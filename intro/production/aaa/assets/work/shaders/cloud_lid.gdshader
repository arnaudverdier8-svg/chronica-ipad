shader_type spatial;
// Le COUVERCLE des bouffées (view/board.gd) : les mêmes bouffées que
// cloud.gdshader (na_puff, au pixel près), redessinées dans la passe
// transparente APRÈS les cartouches des villes, autour des villes connues
// seulement : voir fog_lid.gdshader. Levées de NU_LID_LIFT ; elles écrivent
// la profondeur (le détourage tranche net : discard), si bien qu'entre elles
// la plus haute l'emporte, comme dans l'opaque.

render_mode blend_mix, depth_draw_always, diffuse_lambert, specular_disabled, cull_back;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_nuages.gdshaderinc"
#include "res://view/shaders/nuages_astra.gdshaderinc"

global uniform float g_night;
global uniform float g_snow;

varying vec3 wpos;
varying flat vec3 v_c;
varying flat float v_r;
varying flat vec4 v_k;
varying flat vec2 v_l2;
varying flat vec4 v_ns;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += NU_LID_LIFT;
	v_c = MODEL_MATRIX[3].xyz;
	v_r = max(length(MODEL_MATRIX[0].xyz) * 0.5, 1e-3);
	v_k = INSTANCE_CUSTOM;
	v_l2 = COLOR.rg;
	v_ns = vec4(cos(v_k.z * ST_TAU), sin(v_k.z * ST_TAU), cos(v_l2.x * ST_TAU), sin(v_l2.x * ST_TAU));
}

void fragment() {
	// Une bouffée d'Astra, posée À PLAT par-dessus le bord de la nappe ; son
	// détourage tranche net (seuil d'alpha) : elle écrit la profondeur, et
	// la plus haute (étages Y_PUFF) passe devant ses voisines.
	vec4 p = na_puff(wpos.xz, v_c.xz, v_r, v_k.r);
	vec3 col = nu_season(p.rgb, g_snow);
	ALBEDO = nu_night(col, g_night);
	ROUGHNESS = 1.0;
	EMISSION = nu_night_glow(col, g_night);
	if (p.a < 0.5) {
		discard;
	}
	ALPHA = 1.0;
}
