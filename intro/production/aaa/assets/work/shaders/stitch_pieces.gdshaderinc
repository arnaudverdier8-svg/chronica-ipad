// ============================================================================
// stitch_pieces.gdshaderinc : la broderie EN RELIEF (stumpwork) des pièces et
// des décors (figurines, colonies, bâtiments, aménagements, arbres, monts).
//
// Inclus par piece.gdshader, prop.gdshader et piece_outline.gdshader, APRÈS
// stitch.gdshaderinc. Préfixe pc_ / PC_.
//
// TROIS IDÉES
//
// 1. LA PROJECTION OBLIQUE. La caméra regarde la carte presque d'en haut
//    (64° à 76°) : un objet debout s'y lit par son toit, comme une tache.
//    Sur la tapisserie, chaque chose est brodée EN ÉLÉVATION sur un plan
//    (la perspective cavalière des vieilles cartes). On l'obtient par un
//    cisaillement du monde, au vertex :  z -= (y - PC_Y0) · PC_SHEAR.
//    Le pied d'une pièce (y ≈ PC_Y0) ne bouge pas : elle reste posée sur sa
//    case, elle ne flotte pas ; sa hauteur se couche vers le nord, c'est-à-dire
//    vers le HAUT de l'écran, et se lit comme une silhouette de profil. Tant
//    que PC_SHEAR < tan(inclinaison) (2,0 au plus près), le haut reste plus
//    proche de la caméra que le bas : les recouvrements restent justes. Les
//    ombres portées suivent (la passe d'ombre exécute le même vertex()).
//
// 2. L'ÉCLAIRAGE DE LA BRODERIE COUCHÉE. Une pièce brodée en relief est
//    posée À PLAT sur la toile : sa face avant regarde le ciel. Le soleil
//    vient du nord-ouest : les faces vraiment tournées vers la caméra (le sud)
//    seraient dans l'ombre. On éclaire donc avec une normale tournée de
//    PC_RELIEF autour de l'axe est-ouest (l'avant vers le haut, le dessus vers
//    le nord) : l'avant s'affiche presque à sa couleur de palette, le flanc
//    gauche (ouest) est clair, le flanc droit (est) sombre : le modelé de la
//    cible. Les pièces ne reçoivent pas d'ombre (render_mode
//    shadows_disabled) : elles en portent sur la toile.
//
// 3. LE CONTOUR BRUN. Une coque inversée poussée de quelques pixels d'écran
//    le long de la normale : le fil brun autour de chaque silhouette et de
//    chaque partie qui en recouvre une autre (bouclier, tête, toit). Elle
//    est CUITE DANS LE MAILLAGE (Models.merged, Props) : les mêmes triangles,
//    sommets dans l'ordre inverse, marqués par leur UV2 (la normale lissée,
//    jamais nulle) ; avec cull_back, la coque inversée ne se montre que
//    derrière la pièce. Un seul appel de dessin pour la pièce et son contour
//    (l'iPad en WebGL2 n'en tient que quelques centaines par image) :
//    pc_outline() au vertex(), pc_hull_fragment au fragment(). Le vieux
//    chemin en passe suivante (piece_outline.gdshader) ne sert plus qu'aux
//    pièces d'une seule matière (projectiles).
//
// Le satin de remplissage suit la plus grande pente de chaque facette (droit
// sur une face debout, le long du versant sur un toit ou un mont, en biais
// sur un dessus plat) : chaque facette d'un modèle à facettes est une pièce
// de satin, comme les aplats de la cible.
//
// COÛT par pixel : pc_* = 0 hash ; le satin (st_satin) = 1 hash.
// ============================================================================

#ifndef CHRONICA_STITCH_PIECES_GDSHADERINC
#define CHRONICA_STITCH_PIECES_GDSHADERINC

// Cisaillement oblique (= Models.SHEAR) et hauteur du pied (= Vis.GROUND_Y).
const float PC_SHEAR = 0.9;
const float PC_Y0 = 0.06;
// Rotation de la normale d'éclairage (radians) : 1,40 ≈ 80°.
const float PC_RELIEF = 1.40;

// Le satin : pas des rangs, longueur moyenne d'un point (monde). Gros fil
// de laine sur les décors (environ cinq bandes sur un sapin, comme la
// cible : elles se lisent encore au zoom de partie), plus fin sur les pièces.
const float PC_SATIN_W = 0.032;
const float PC_SATIN_LEN = 0.1;
const float PC_PROP_W = 0.05;
const float PC_PROP_LEN = 0.14;

// Cisaille un point du monde (oblique est 0..1 : 0 = pièce plate, non
// cisaillée, comme un pont).
vec3 pc_shear(vec3 w, float oblique) {
	return vec3(w.x, w.y, w.z - (w.y - PC_Y0) * PC_SHEAR * oblique);
}

// La normale du monde cisaillé (transposée inverse du cisaillement).
vec3 pc_shear_normal(vec3 n, float oblique) {
	return normalize(vec3(n.x, n.y + PC_SHEAR * oblique * n.z, n.z));
}

// La normale d'éclairage de la broderie couchée (voir l'en-tête).
vec3 pc_relief(vec3 n) {
	float c = cos(PC_RELIEF);
	float s = sin(PC_RELIEF);
	return vec3(n.x, n.y * c + n.z * s, n.z * c - n.y * s);
}

// ----------------------------------------------------------------------------
// LE CONTOUR (la coque)
// ----------------------------------------------------------------------------
// Un sommet de coque porte dans UV2 la normale LISSÉE (codage octaédrique dans
// [0,25 ; 0,75], Models.smooth_uv2) ; un sommet de la pièce elle-même, UV2 nul.
float pc_is_hull(vec2 e2) {
	return step(0.1, e2.x);
}

// La normale lissée rangée dans UV2 ; UV2 nul (maillage non préparé) : la
// vraie normale n.
vec3 pc_hull_normal(vec2 e2, vec3 n) {
	vec2 e = (e2 - 0.5) * 4.0;
	vec3 o = vec3(e.x, 1.0 - abs(e.x) - abs(e.y), e.y);
	float t = clamp(-o.y, 0.0, 1.0);
	o.x += o.x >= 0.0 ? -t : t;
	o.z += o.z >= 0.0 ? -t : t;
	return step(0.1, e2.x) > 0.5 ? normalize(o) : n;
}

// La position (repère de la vue) d'un sommet de coque : cisaillé comme la
// pièce, puis poussé dans le plan de l'écran le long de sa normale lissée
// d'une épaisseur visée en unités monde (ww), bornée en pixels (wmin, wmax ;
// ref_h : hauteur de référence de l'image, 1200, l'iPad en 4:3). nv rend la
// normale dans la vue.
//
// Mesuré en gl_compatibility (Godot 4.7) : VIEWPORT_SIZE n'est pas utilisable
// au vertex() et PROJECTION_MATRIX[1][1] peut être négatif (y retourné) ;
// d'où ref_h et abs(). Pas d'extrusion en projection orthographique (la passe
// d'ombre du soleil : la coque y aurait des kilomètres) ; un déport borné
// ailleurs.
vec3 pc_outline(vec3 vtx, vec3 nrm, vec2 e2, mat4 model, mat3 model_n, mat4 view, mat4 proj,
		float ww, float wmin, float wmax, float ref_h, out vec3 nv) {
	vec3 w = pc_shear((model * vec4(vtx, 1.0)).xyz, 1.0);
	vec3 nw = pc_shear_normal(normalize(model_n * pc_hull_normal(e2, nrm)), 1.0);
	vec3 vp = (view * vec4(w, 1.0)).xyz;
	nv = (view * vec4(nw, 0.0)).xyz;
	// Direction de la normale dans le plan de l'écran (focale serrée :
	// presque orthographique, le plan xy de la vue est celui de l'écran).
	float ln = length(nv.xy);
	vec2 dir = nv.xy / max(ln, 1e-6) * step(1e-6, ln);
	// Taille d'un pixel, en unités monde, à cette profondeur.
	float pxw = 2.0 * max(-vp.z, 1e-3) / max(abs(proj[1][1]) * ref_h, 1e-6);
	float wpx = clamp(ww / pxw, wmin, wmax);
	float persp = 1.0 - clamp(proj[3][3], 0.0, 1.0);
	return vp + vec3(dir * min(wpx * pxw, 0.045) * persp, 0.0);
}

// Le fil brun du contour (avant le voile de la nuit : la coque n'en prend pas).
vec3 pc_hull_color(float night) {
	return st_albedo(ST_BRUN) * (1.0 - 0.25 * night);
}

// Le voile de la veille (SkyRig, g_veil : couleur linéaire, densité), tel que
// le moteur le calcule pour un brouillard de profondeur (début 0, fin 0,5,
// courbe 1) : un shader qui écrit FOG le remplace, et doit le refaire pour
// tout ce qui n'est pas la coque (celle-ci écrit FOG = 0, comme une passe
// fog_disabled).
vec4 pc_veil(vec3 vertex, vec4 veil) {
	return vec4(veil.rgb, veil.a * smoothstep(0.0, 0.5, length(vertex)));
}

// Empreinte d'un pixel sur une surface quelconque, pour une position 3D
// continue (unités monde). FRAGMENT SEULEMENT, hors branche.
float pc_px(vec3 q) {
	return max(max(length(dFdx(q)), length(dFdy(q))), 1e-6);
}

// Le repère du fil sur une facette de normale n (monde, non cisaillée) pour
// une position q relative à la pièce : T le long du point (plus grande
// pente ; un biais fixe sur un dessus plat), B en travers. Rend uv = (le
// long, en travers) en unités monde, pour st_satin.
vec2 pc_uv(vec3 n, vec3 q, out vec3 T, out vec3 B) {
	vec3 t = vec3(0.0, 1.0, 0.0) - n * n.y;
	float lt = length(t);
	float flat_top = 1.0 - step(0.3, lt);
	vec3 tf = vec3(0.8, 0.0, -0.6);
	T = normalize(mix(t / max(lt, 1e-4), tf, flat_top));
	B = normalize(cross(n, T));
	// Les rangs se posent côte à côte selon l'axe horizontal le plus en
	// travers de la facette (x sur une face avant, z sur un flanc) ; en biais
	// sur un dessus plat.
	float across = mix(mix(q.x, q.z, step(abs(n.z), abs(n.x))), dot(q, vec3(0.6, 0.0, 0.8)), flat_top);
	return vec2(dot(q, T), across);
}

// ----------------------------------------------------------------------------
// LES ARMES : le meuble brodé sur l'écu des figurines (matière « blazon »)
// ----------------------------------------------------------------------------
// Repère de l'écu : p = (x, y) normalisés, demi-largeur 1, y vers le haut
// (posé dans les UV de la face avant par tools/blender/kit.py, Part.blazon).
// Distances signées APPROCHÉES (négatives dedans), assez justes pour un bord
// antialiasé et un liseré brun. 0 hash ; le soleil coûte un atan.

float pc_box(vec2 p, vec2 h) {
	vec2 d = abs(p) - h;
	return length(max(d, vec2(0.0))) + min(max(d.x, d.y), 0.0);
}

float pc_circ(vec2 p, vec2 c, float r) {
	return length(p - c) - r;
}

// charge : 1 croix, 2 soleil (huit rais), 3 sautoir, 4 fleur de lis ; autre :
// écu plein (rend une distance très grande).
float pc_charge(vec2 p, int charge) {
	if (charge == 1) {
		vec2 q = p - vec2(0.0, 0.02);
		return min(pc_box(q + vec2(0.0, 0.08), vec2(0.2, 0.78)), pc_box(q - vec2(0.0, 0.22), vec2(0.7, 0.19)));
	} else if (charge == 2) {
		vec2 q = p - vec2(0.0, 0.05);
		float r = length(q);
		float sec = ST_PI * 0.25;
		float s = mod(atan(q.y, q.x) + sec * 0.5, sec) - sec * 0.5;
		float w = 0.16 * clamp((0.82 - r) / 0.46, 0.0, 1.0);
		float ray = max(abs(s) * r - w, max(0.38 - r, r - 0.82));
		return min(r - 0.34, ray);
	} else if (charge == 3) {
		vec2 a = st_rot(p, 0.785);
		vec2 b = st_rot(p, -0.785);
		return max(min(pc_box(a, vec2(0.17, 0.95)), pc_box(b, vec2(0.17, 0.95))), length(p) - 0.86);
	} else if (charge == 4) {
		vec2 q = vec2(abs(p.x), p.y);
		float c = max(max(pc_circ(p, vec2(0.62, 0.08), 0.86), pc_circ(p, vec2(-0.62, 0.08), 0.86)), -p.y - 0.2);
		float pt = max(pc_circ(q, vec2(0.42, 0.08), 0.40), -pc_circ(q, vec2(0.66, -0.06), 0.34));
		pt = max(pt, max(-p.y - 0.32, 0.12 - q.x));
		float band = pc_box(p + vec2(0.0, 0.3), vec2(0.48, 0.1));
		float f = max(max(pc_circ(p, vec2(0.25, -0.62), 0.32), pc_circ(p, vec2(-0.25, -0.62), 0.32)), p.y + 0.36);
		float f2 = max(pc_circ(q, vec2(0.34, -0.52), 0.16), p.y + 0.38);
		return min(min(c, pt), min(band, min(f, f2)));
	}
	return 1e3;
}

#endif
