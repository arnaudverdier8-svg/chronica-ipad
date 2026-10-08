shader_type spatial;
// La NAPPE du brouillard : la toile matelassée d'Astra (cloud_fill,
// assets/ui/table/clouds/ ; nuages_astra.gdshaderinc), répétée en
// coordonnées monde sur les terres inconnues, SOUS les bouffées de la
// lisière (cloud.gdshader ; disposition : view/quilt.gd). Plate.
//
// COÛT par pixel : un échantillon de texture.

render_mode diffuse_lambert, specular_disabled, cull_back;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_nuages.gdshaderinc"
#include "res://view/shaders/nuages_astra.gdshaderinc"

global uniform float g_night;
global uniform float g_snow;

varying vec3 wpos;
varying float v_in;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_in = COLOR.r;
}

void fragment() {
	// Dérivées d'abord, hors de toute branche.
	vec3 col = na_fill(wpos.xz);
	col = nu_season(col, g_snow);
	ALBEDO = nu_night(col, g_night);
	ROUGHNESS = 1.0;
	EMISSION = nu_night_glow(col, g_night);
}
