shader_type spatial;
// Le contour brun en PASSE SUIVANTE : une coque inversée (on ne dessine que
// ses faces arrière), poussée de quelques PIXELS dans le plan de l'écran le
// long de la normale. Elle ne sert plus qu'aux pièces d'une seule matière
// (Models.mat : projectiles) ; les pièces et les décors portent leur coque
// dans leur maillage (pc_outline, stitch_pieces.gdshaderinc), un appel de
// dessin de moins par surface. Portable (gl_compatibility) : rien que du
// vertex.

render_mode skip_vertex_transform, unshaded, cull_front, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"

// Épaisseur visée en unités monde, bornée en pixels : net de près, jamais
// plus épais que width_max, jamais sous width_min (il pâlirait en tirets).
uniform float width_world = 0.02;
uniform float width_min = 1.2;
uniform float width_max = 2.4;
// Hauteur de référence de l'image, en pixels : 1200 (l'iPad en 4:3).
uniform float ref_h = 1200.0;

global uniform float g_night;

void vertex() {
	vec3 nv;
	VERTEX = pc_outline(VERTEX, NORMAL, UV2, MODEL_MATRIX, MODEL_NORMAL_MATRIX, VIEW_MATRIX, PROJECTION_MATRIX,
			width_world, width_min, width_max, ref_h, nv);
	NORMAL = nv;
}

void fragment() {
	ALBEDO = pc_hull_color(g_night);
}
