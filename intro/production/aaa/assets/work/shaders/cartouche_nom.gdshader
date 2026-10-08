shader_type spatial;
// Le NOM du cartouche d'une colonie (view/city_labels.gd ; corps commun :
// view/shaders/cartouche.gdshaderinc), SANS pochoir : les lettres (part = 1)
// et la place du nom (part = 2 : la plaque, sur la hauteur de la plaque et la
// largeur du texte seulement, redessinée par-dessus la plaque au pochoir).
// Une tête d'unité qui entre dans la ligne du nom passe dessous : le nom de
// la ville reste lisible.

render_mode blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, specular_disabled, shadows_disabled;

#include "res://view/shaders/cartouche.gdshaderinc"
