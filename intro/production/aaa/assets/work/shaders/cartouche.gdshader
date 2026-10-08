shader_type spatial;
// La PLAQUE du cartouche d'une colonie (view/city_labels.gd), son corps et
// ses points : view/shaders/cartouche.gdshaderinc. Ce shader-ci la dessine au
// POCHOIR : pas sur les pixels qu'une figurine en carte brodée a marqués
// (bit 4, figure.gdshader). Une unité qui se tient dans l'emprise du
// cartouche (les bouts de la plaque, les pointes, l'onglet du rang) passe
// donc devant lui, découpée à sa silhouette exacte. La place du nom, elle,
// est redessinée par-dessus sans pochoir (cartouche_nom.gdshader, part = 2) :
// le nom reste entier.

render_mode blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, specular_disabled, shadows_disabled;
stencil_mode read, compare_not_equal, 4;

#include "res://view/shaders/cartouche.gdshaderinc"
