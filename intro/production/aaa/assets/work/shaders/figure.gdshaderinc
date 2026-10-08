// ============================================================================
// figure.gdshaderinc : la CARTE BRODÉE d'une figurine (view/figures.gd), la
// géométrie que partagent la carte (figure.gdshader) et son éclair de coup
// reçu (figure_flash.gdshader) : les deux doivent tomber sur les mêmes pixels
// et la même profondeur, au bit près (la surimpression passe en GEQUAL).
//
// Inclus APRÈS stitch.gdshaderinc et stitch_pieces.gdshaderinc. Préfixe
// fig_ / FIG_.
//
// LA CARTE DEBOUT. Le maillage (Figures.mesh) est un quad VERTICAL, face au
// sud, posé sur le pied de la figurine (l'origine du nœud), en unités monde.
// Il est cisaillé comme toutes les pièces (pc_shear) : sa hauteur se couche
// vers le nord, il a la profondeur d'une pièce DEBOUT (le décor au nord reste
// derrière lui, ce qui est au sud passe devant) ; une carte tournée face à la
// caméra serait presque couchée et un sapin du nord la traverserait.
//
// SES PROPORTIONS. Debout et cisaillée, une hauteur h de la carte s'affiche
// h × (cos i + PC_SHEAR × sin i) (i : inclinaison de la caméra, 64° à 76°),
// soit ≈ 1,19 h : la figurine serait étirée. fig_position divise donc la
// hauteur de la carte par ce facteur, lu sur la caméra (INV_VIEW_MATRIX) :
// à tout zoom, la figurine s'affiche dans les proportions où elle est brodée,
// et un pixel de la carte reste carré à l'écran (pas de filtrage anisotrope).
//
// SON PIED. Le cordon des semelles (et la hampe d'une lance) descend un peu
// sous le pied : le dessus de la case le mangerait (figurine qui s'enfonce).
// Le bas de la carte prend la profondeur d'un point soulevé de FIG_DEPTH_LIFT
// (la position à l'écran ne bouge pas) : il passe devant le sol de sa case.
// ============================================================================

#ifndef CHRONICA_FIGURE_GDSHADERINC
#define CHRONICA_FIGURE_GDSHADERINC

const float FIG_DEPTH_LIFT = 0.03;

// L'étirement vertical d'une carte debout cisaillée, vu par la caméra
// (son haut d'écran dans le monde : INV_VIEW_MATRIX[1]).
float fig_aspect(mat4 inv_view) {
	vec3 up = normalize(inv_view[1].xyz);
	return max(up.y - PC_SHEAR * up.z, 0.3);
}

// La position de découpe d'un sommet de la carte (à écrire dans POSITION) ;
// vp rend sa position dans la vue (à écrire dans VERTEX : le voile, VIEW).
vec4 fig_position(vec3 v, mat4 model, mat4 view, mat4 inv_view, mat4 proj, out vec3 vp) {
	vec3 lv = vec3(v.x, v.y / fig_aspect(inv_view), v.z);
	vp = (view * vec4(pc_shear((model * vec4(lv, 1.0)).xyz, 1.0), 1.0)).xyz;
	vec4 c = proj * vec4(vp, 1.0);
	// La profondeur : celle du même point, soulevé au-dessus du pied.
	vec3 ld = vec3(lv.x, max(lv.y, FIG_DEPTH_LIFT), lv.z);
	vec4 cd = proj * (view * vec4(pc_shear((model * vec4(ld, 1.0)).xyz, 1.0), 1.0));
	return vec4(c.xy, cd.z / cd.w * c.w, c.w);
}

#endif
