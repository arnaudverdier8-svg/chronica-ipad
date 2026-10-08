shader_type spatial;
// L'éclair d'un coup reçu sur une figurine en carte brodée : une
// surimpression (material_overlay) posée le temps de l'éclair. Même géométrie
// que la carte (figure.gdshaderinc : mêmes pixels, même profondeur, la
// surimpression passe en GEQUAL), même découpe alpha (rien hors de la
// silhouette). Elle ajoute la couleur de l'éclair ; `flash.a` va de 1 à 0.
// Une matière neuve par coup (Figures.flash_material) : sa couleur s'anime.

render_mode skip_vertex_transform, unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"
#include "res://view/shaders/figure.gdshaderinc"

uniform sampler2D albedo_tex : filter_linear_mipmap, repeat_disable;
uniform vec4 flash = vec4(0.0);

void vertex() {
	vec3 vp;
	POSITION = fig_position(VERTEX, MODEL_MATRIX, VIEW_MATRIX, INV_VIEW_MATRIX, PROJECTION_MATRIX, vp);
	VERTEX = vp;
}

void fragment() {
	// (UV x > 1,5 : l'écu flottant, qui ne s'éclaire pas)
	if (UV.x > 1.5 || texture(albedo_tex, UV).a < 0.5) {
		discard;
	}
	ALBEDO = st_albedo(flash.rgb) * flash.a * 0.75;
}
