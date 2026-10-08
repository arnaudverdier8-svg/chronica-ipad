shader_type spatial;
// Le COUVERCLE de la nappe (view/board.gd) : la même nappe que fog.gdshader
// (na_fill, au pixel près), redessinée dans la passe transparente APRÈS les
// cartouches des villes (view/city_labels.gd), mais seulement sur les cases
// de nuage voisines d'une ville connue. Un cartouche se dessine sans test de
// profondeur (il passe par-dessus le décor) : sans couvercle, celui d'une
// ville au bord du brouillard passerait aussi par-dessus les nuages. Le
// couvercle, lui, a le test de profondeur : un arbre ou une figurine devant
// le nuage le cache encore, et il ne recouvre le cartouche que là où le nuage
// est devant. Levé de NU_LID_LIFT au-dessus de la nappe (il gagne le test
// contre elle, perd contre tout ce qui la cachait) ; il écrit la profondeur
// (les bourrelets du couvercle passent dessous, comme dans l'opaque).

render_mode blend_mix, depth_draw_always, diffuse_lambert, specular_disabled, cull_back;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_nuages.gdshaderinc"
#include "res://view/shaders/nuages_astra.gdshaderinc"

global uniform float g_night;
global uniform float g_snow;

varying vec3 wpos;
varying float v_in;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += NU_LID_LIFT;
	v_in = COLOR.r;
}

void fragment() {
	// Dérivées d'abord, hors de toute branche.
	vec3 col = na_fill(wpos.xz);
	col = nu_season(col, g_snow);
	ALBEDO = nu_night(col, g_night);
	ROUGHNESS = 1.0;
	EMISSION = nu_night_glow(col, g_night);
	ALPHA = 1.0;
}
