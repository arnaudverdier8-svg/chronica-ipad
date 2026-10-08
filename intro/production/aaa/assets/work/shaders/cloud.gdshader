shader_type spatial;
// Les BOUFFÉES de la lisière du brouillard (disposition : view/quilt.gd) :
// les nuages matelassés peints d'Astra (assets/ui/table/clouds/, atlas de
// huit bouffées : tools/ui_table/clouds.py ; nuages_astra.gdshaderinc). Chaque
// bouffée est un carré PLAT (MultiMesh) posé À PLAT au-dessus du bord de la
// nappe (fog.gdshader) : leurs bosses couvrent le bord droit de la nappe, et
// la lisière entière est une guirlande de nuages de tailles inégales.
// L'image est choisie et retournée par la graine de l'instance
// (INSTANCE_CUSTOM.r) ; le reste des données d'instance (bords de la nappe)
// ne sert plus qu'à la disposition.
//
// COÛT par pixel : un échantillon de texture, seuil d'alpha. Pas d'ombre
// portée.

render_mode diffuse_lambert, specular_disabled, cull_back;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_nuages.gdshaderinc"
#include "res://view/shaders/nuages_astra.gdshaderinc"

global uniform float g_night;
global uniform float g_snow;

varying vec3 wpos;
varying flat vec3 v_c;      // centre du disque (monde)
varying flat float v_r;     // rayon du disque (monde)
varying flat vec4 v_k;      // INSTANCE_CUSTOM
varying flat vec2 v_l2;     // le second bord de la nappe (couleur d'instance)
varying flat vec4 v_ns;     // les normales des deux bords (calculées par sommet)

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_c = MODEL_MATRIX[3].xyz;
	v_r = max(length(MODEL_MATRIX[0].xyz) * 0.5, 1e-3);
	v_k = INSTANCE_CUSTOM;
	v_l2 = COLOR.rg;
	// (cos / sin des deux bords une fois par sommet, pas par pixel)
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
	ALPHA = p.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
