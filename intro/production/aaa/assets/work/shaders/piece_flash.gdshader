shader_type spatial;
// L'éclair d'un coup reçu : une surimpression (material_overlay) posée sur
// la figurine le temps de l'éclair, dessinée avec la même projection oblique
// que la pièce (stitch_pieces) pour la recouvrir exactement. Elle ajoute la
// couleur de l'éclair ; `flash.a` va de 1 à 0. La coque du contour cuite
// dans le maillage (UV2 non nul, Models.merged) n'en prend pas : ses
// triangles sont réduits à un point, rien n'est tracé.

render_mode skip_vertex_transform, unshaded, blend_add, depth_draw_never, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"

uniform vec4 flash = vec4(0.0);

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX = (VIEW_MATRIX * vec4(pc_shear(w, 1.0), 1.0)).xyz;
	NORMAL = normalize((VIEW_MATRIX * vec4(pc_shear_normal(normalize(MODEL_NORMAL_MATRIX * NORMAL), 1.0), 0.0)).xyz);
	if (pc_is_hull(UV2) > 0.5) {
		VERTEX = vec3(0.0, 0.0, -1.0);
	}
}

void fragment() {
	ALBEDO = st_albedo(flash.rgb) * flash.a * 0.75;
}
