// ============================================================================
// stitch.gdshaderinc : la bibliothèque de BRODERIE de Chronica.
//
// Direction « tapisserie » (docs/DIRECTION_TAPISSERIE.md) : une carte brodée
// sur du lin, vue presque d'en haut. Tout ce qui est fil, point ou toile se
// calcule ici, pour que le terrain, l'eau, les frontières, les nuages et les
// pièces parlent la même langue. Bibliothèque GELÉE : on l'inclut, on ne la
// modifie pas.
//
//     #include "res://view/shaders/stitch.gdshaderinc"
//
// (dans un shader spatial, après `shader_type` et `render_mode`). Tout porte
// le préfixe st_ / ST_ / St pour ne jamais heurter les noms de l'hôte.
//
// PORTABILITÉ : arithmétique pure, aucune texture, aucune boucle, aucun sin()
// dans les hash. Valide en gl_compatibility (WebGL2, iPad Safari) comme en
// Forward+. Seules dFdx / dFdy / fwidth servent (anti-moiré).
//
// ----------------------------------------------------------------------------
// CONVENTIONS
// ----------------------------------------------------------------------------
// - UNITÉS : les longueurs de motif sont en UNITÉS DU MONDE (une case a un
//   rayon de 1,0 ; Hex.SIZE). Un pas de point est une longueur, jamais un
//   nombre de répétitions : le fil garde sa taille d'une pièce à l'autre.
// - `px` : l'EMPREINTE D'UN PIXEL, en unités monde, sur la surface dessinée
//   (st_px). Tout motif se compare à px pour s'effacer : c'est la règle
//   anti-moiré (ci-dessous). px se calcule dans fragment(), AVANT toute
//   branche (une dérivée dans une branche non uniforme est indéfinie).
// - REPÈRE D'UN FIL : `along` = abscisse le long du fil, `across` = distance
//   signée en travers (0 sur l'axe), toutes deux en unités monde.
// - `tilt` : INCLINAISON DE LA NORMALE dans le repère du motif, x = le long,
//   y = en travers. La normale bombée s'obtient par st_bend :
//       n' = normalize(n + tilt.x * T + tilt.y * B)
//   (T : tangente monde du fil, B : direction monde « en travers »). Un tilt
//   positif penche la normale vers +T / +B : le flanc droit d'un fil rond
//   (across > 0) a tilt.y > 0. tilt = 0 au loin (motif effacé).
// - `shade` : ombre PEINTE multiplicative, de MOYENNE 1 sur un point entier
//   (rainures, bouts qui plongent, torsion, valeur propre au point) : quand
//   elle s'efface (shade → 1) la teinte moyenne ne bouge pas.
// - `cover` : part du pixel couverte par le fil (0..1), déjà filtrée.
//
// ----------------------------------------------------------------------------
// COULEUR : LE PIÈGE DES DEUX RENDERERS (mesuré, Godot 4.7)
// ----------------------------------------------------------------------------
// gl_compatibility prend ALBEDO pour une valeur sRGB (d'affichage) : en
// unshaded, ALBEDO = 0,5 s'affiche 128/255 ; éclairé, le moteur la linéarise,
// la multiplie par l'éclairement et repasse en sRGB, PASSE PAR PASSE (le
// soleil à ombres a sa propre passe). Une couleur de sommet ou un uniform
// `source_color` n'y est pas converti. Forward+ prend ALBEDO pour une valeur
// linéaire (0,5 → 188/255) et convertit les uniforms `source_color`. Donc :
//   - une couleur de palette (Vis, sRGB) venue d'une couleur de sommet (COLOR),
//     d'un uniform SANS source_color ou d'une constante ST_* → st_albedo(c) ;
//   - un uniform AVEC `source_color` est déjà dans le bon espace : tel quel ;
//   - JAMAIS st_srgb_to_linear() sur un albédo : en Compatibility (l'iPad),
//     il assombrit et sature tout (c'était l'aspect « néon » du diorama).
// Avec la lumière de Vis.PHASE_LIGHT (un aplat horizontal reçoit ≈ 1 en plein
// jour), un albédo de palette s'affiche à sa couleur de palette. Les sombres
// sortent un peu plus sombres (le repassage en sRGB par passe écrase le
// pied de courbe) : ne pas les assombrir encore « pour compenser » la nuit.
// EMISSION s'affiche telle quelle en Compatibility (mesuré : 0,5 → 128/255),
// en linéaire en Forward+ : même règle, une couleur de palette passe par
// st_albedo avant EMISSION.
//
// ----------------------------------------------------------------------------
// RÈGLE ANTI-MOIRÉ (non négociable)
// ----------------------------------------------------------------------------
// Un motif plus fin que ~2 pixels scintille au moindre glissé. Chaque détail
// est donc pondéré par st_fade(sa_taille, px) : 1 tant qu'il fait plus de
// ST_FADE_HI pixels, 0 dès qu'il tombe sous ST_FADE_LO pixels. Ce qui
// s'efface retombe sur sa MOYENNE (shade → 1, tilt → 0, cover → couverture
// moyenne), jamais sur le fil nu ni sur un trou. Une LIGNE isolée (contour,
// liseré) n'est pas un motif périodique : sa couverture est filtrée
// exactement (st_band) et, plus fine qu'un pixel, elle pâlit en proportion
// (elle ne grossit pas, elle ne crépite pas). Toutes les fonctions st_* de
// motif appliquent déjà ces règles ; l'hôte n'a qu'à fournir px.
//
// ----------------------------------------------------------------------------
// COÛT PAR PIXEL (budget iPad : ≤ 6 appels de hash ou de bruit, ≤ 4 tours de
// boucle, aucune texture lue)
// ----------------------------------------------------------------------------
//   st_hash11 / 21 / 22 / 31  1 appel de hash chacun (~8-12 ALU)
//   st_vnoise                 4 appels de hash (!) — à réserver à un seul usage
//   st_px                     2 dérivées (dFdx, dFdy)
//   st_fade / st_band / st_step / st_bend / st_round / st_sheen : 0 hash, < 15 ALU
//   st_linen                  0 hash, ~30 ALU
//   st_running                0 hash, ~45 ALU (1 sqrt)
//   st_hex_running            0 hash, ~70 ALU (st_hex + st_running)
//   st_hex_running_ht         0 hash, ~45 ALU (st_running ; h et t fournis)
//   st_satin                  1 hash, ~60 ALU
//   st_seed                   1 hash, ~60 ALU (1 cos, 1 sin, 1 sqrt)
//   st_couched                0 hash, ~70 ALU (1 cos, 1 sin)
//   st_twist                  0 hash (1 cos, 1 sin)
//   st_spiral                 0 hash (1 atan, 1 length)
//   st_scatter                1 hash
//   st_hex / st_hex_center / st_hex_axial / st_hex_dir : 0 hash, < 30 ALU
//   st_rim                    1 fwidth
//   st_silk (dans light())    1 pow ; st_lobe_exp : 1 division
//   st_albedo                 0 en Compatibility, 3 pow en Forward+ (faire au
//                             vertex() quand la couleur vient d'un sommet)
// Aucune boucle dans toute la bibliothèque.
//
// ----------------------------------------------------------------------------
// SOMMAIRE (signature → rôle ; le détail est au-dessus de chaque fonction)
// ----------------------------------------------------------------------------
//  Palette (sRGB, = Vis)    ST_LIN ST_CREME ST_OCRE ST_OR ST_DENIM ST_NUIT
//                           ST_BRIQUE ST_BRIQUE_VIF ST_SAPIN ST_SAPIN_CLAIR ST_BRUN
//  Couleur
//    vec3  st_srgb_to_linear(vec3 c)        conversion exacte sRGB → linéaire
//    vec3  st_linear_to_srgb(vec3 c)        l'inverse
//    vec3  st_albedo(vec3 srgb)             palette sRGB → espace du renderer
//    float st_luma(vec3 c)                  luminance (Rec. 709)
//  Hash et bruit
//    float st_hash11(float p)   float st_hash21(vec2 p)
//    vec2  st_hash22(vec2 p)    float st_hash31(vec3 p)
//    float st_vnoise(vec2 p)                bruit de valeur lissé, 0..1
//  Anti-moiré
//    float st_px(vec2 p)                    empreinte d'un pixel (fragment)
//    float st_px_axis(vec2 dpx, vec2 dpy, vec2 axis)  empreinte selon un axe
//    float st_fade(float size, float px)    1 = détail visible, 0 = effacé
//    float st_band(float x, float hw, float px)  couverture filtrée de |x| < hw
//    float st_step(float d, float px)       couverture filtrée de d > 0
//  Géométrie
//    vec2  st_rot(vec2 v, float a)          rotation (radians)
//    vec3  st_bend(vec3 n, vec3 t, vec3 b, vec2 tilt)  normale bombée
//    float st_round(float u)                pente d'un fil rond, u ∈ [-1, 1]
//    vec3  st_twist(float s, float u, float lean)  torsade (crête, tilt.xy)
//    float st_hex(vec2 p, out float t, out vec2 n)   repère d'hexagone
//    float st_hex_dir(vec2 n)               index Hex.DIRS d'une arête
//    vec2  st_hex_axial(vec2 xz)            case (q, r) sous un point du monde
//    vec2  st_hex_center(vec2 xz)           centre monde de cette case
//    vec2  st_spiral(vec2 p, float pitch)   repère (along, across) d'une spirale
//    vec2  st_scatter(vec2 p, float cell, float seed, out vec2 local)  semis
//  Toile et points
//    float    st_linen(vec2 p, float pitch, float px, out vec2 tilt)  lin
//    StThread st_running(float along, float across, float len, float gap,
//                        float width, float px)          point devant
//    StThread st_hex_running(vec2 p, float ring, float len, float gap,
//                        float width, float px)          point devant en hexagone
//    StThread st_hex_running_ht(float h, float t, float ring, float len,
//                        float gap, float width, float px)   le même, h et t donnés
//    StThread st_satin(vec2 uv, float w, float len, float seed, float bump,
//                        float jitter, float px)         satin long-and-short
//    StThread st_seed(vec2 p, float cell, float len, float width,
//                        float density, float seed, float px)  semis de points
//    StThread st_couched(float along, float across, float hw, float twist_pitch,
//                        float tie_pitch, float px)      cordon couché + fixations
//    vec3  st_paint(vec3 under, vec3 thread, StThread s)   poser un fil
//    vec3  st_paint_tie(vec3 col, vec3 tie_col, StThread s)  poser les fixations
//  Contour et soie
//    float st_outline(float d, float hw, float px)  contour de demi-largeur hw
//    float st_rim(vec3 N, vec3 V, float width)      bord de silhouette (pièces)
//    float st_sheen(float u, float center, float width)  reflet peint en travers
//    float st_silk(vec3 T, vec3 H, float shin)      reflet anisotrope (light())
//    float st_lobe_exp(float tilt, float px_per, float e_max)  exposant borné
//
// ----------------------------------------------------------------------------
// RECETTE (un shader de terrain brodé, en résumé)
// ----------------------------------------------------------------------------
//   varying vec3 wpos; varying vec3 v_base;
//   void vertex() {
//       wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
//       v_base = st_albedo(COLOR.rgb);          // une fois par sommet
//   }
//   void fragment() {
//       float px = st_px(wpos.xz);               // d'abord, hors branche
//       vec2 lt; float lin = st_linen(wpos.xz, 0.03, px, lt);
//       vec3 col = st_albedo(ST_LIN) * (0.8 + 0.4 * (lin - 0.5));
//       vec2 uv = vec2(wpos.x, wpos.z);         // rangées horizontales
//       StThread s = st_satin(uv, 0.05, 0.3, 0.37, 0.3, 0.05, px);
//       col = st_paint(col, v_base, s);
//       vec3 n = st_bend(vec3(0, 1, 0), vec3(1, 0, 0), vec3(0, 0, 1), s.tilt * s.cover);
//       vec2 p = wpos.xz - st_hex_center(wpos.xz);   // relatif au centre de la case
//       StThread e = st_hex_running(p, 0.80, 0.10, 0.06, 0.025, px);
//       col = st_paint(col, st_albedo(ST_CREME), e);
//       n = normalize(mix(n, st_bend(vec3(0, 1, 0), …), e.cover));
//       ALBEDO = col;
//       NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);  // monde → vue
//   }
// Dans le repère (along, across) d'une rangée horizontale à l'écran, T = +X
// monde et B = +Z monde (le sud, vers le bas de l'écran). Pour un repère
// d'arête (st_hex : t, h), T = (-n.y, 0, n.x) et B = (n.x, 0, n.y).
// StThread est une struct : variable locale, argument, valeur de retour ;
// jamais un varying (passer ses champs utiles un à un vers light()).
//
// VÉRIFIÉE (Godot 4.7, gl_compatibility, Xvfb/llvmpipe) : chaque fonction a
// été compilée et rendue sur le plateau, aux zooms 7, 13 et 30, de jour, à
// l'aube, la nuit et en hiver, sans moiré visible.
// ============================================================================

#ifndef CHRONICA_STITCH_GDSHADERINC
#define CHRONICA_STITCH_GDSHADERINC

const float ST_PI = 3.14159265;
const float ST_TAU = 6.28318531;
const float ST_SQRT3 = 1.7320508;

// Seuils anti-moiré, en PIXELS : un détail de taille ≤ ST_FADE_LO pixels est
// effacé (remplacé par sa moyenne) ; ≥ ST_FADE_HI pixels, il est entier.
// Réglés par la préselection de couleurs (view/palettes.gd, « st_fade » :
// uniform global g_st_fade, défaut 2,0 / 4,5 ; project.godot).
global uniform vec2 g_st_fade;
#define ST_FADE_LO g_st_fade.x
#define ST_FADE_HI g_st_fade.y

// Couverture moyenne d'un rang de satin (les trous minuscules où l'aiguille
// traverse la toile, au bout des points) : la valeur vers laquelle st_satin
// fond `cover` au loin.
const float ST_SATIN_COVER = 0.95;


// ---------------------------------------------------------------------------
// PALETTE (sRGB, mêmes valeurs que view/vis.gd ; passer par st_albedo)
// ---------------------------------------------------------------------------
// Des uniforms globaux (project.godot, [shader_globals]), posés par la
// préselection de couleurs (Vis.use_palette) ; leurs valeurs par défaut sont
// celles de « tapisserie » (entre parenthèses).

global uniform vec3 g_st_lin;
global uniform vec3 g_st_creme;
global uniform vec3 g_st_ocre;
global uniform vec3 g_st_or;
global uniform vec3 g_st_denim;
global uniform vec3 g_st_nuit;
global uniform vec3 g_st_brique;
global uniform vec3 g_st_brique_vif;
global uniform vec3 g_st_sapin;
global uniform vec3 g_st_sapin_clair;
global uniform vec3 g_st_brun;
// lin / parchemin (#C8AD81), crème (#E8D8BB), ocre doré (#A38654), or
// (#B49248), bleu denim (#364751), bleu nuit (#27353F), rouge brique
// (#722815), brique vif (#9B3B24), sapin (#373D2A), sapin clair (#5E6B3A),
// fil brun des contours (#3B2711).
#define ST_LIN g_st_lin
#define ST_CREME g_st_creme
#define ST_OCRE g_st_ocre
#define ST_OR g_st_or
#define ST_DENIM g_st_denim
#define ST_NUIT g_st_nuit
#define ST_BRIQUE g_st_brique
#define ST_BRIQUE_VIF g_st_brique_vif
#define ST_SAPIN g_st_sapin
#define ST_SAPIN_CLAIR g_st_sapin_clair
#define ST_BRUN g_st_brun


// ---------------------------------------------------------------------------
// LE FIL : sortie commune des fonctions de point
// ---------------------------------------------------------------------------

struct StThread {
	float cover;  // part du pixel couverte par le fil principal, 0..1 (filtrée)
	float tie;    // part couverte par un fil posé DESSUS (points de fixation
	              // du cordon couché) ; 0 pour les autres points
	float shade;  // ombre peinte multiplicative, moyenne 1 ; 1 au loin
	vec2 tilt;    // inclinaison de normale (x le long, y en travers) ; 0 au loin
	float u;      // position en travers du fil, -1..1 (0 sur l'axe)
	float rnd;    // hasard propre au point, 0..1, constant sur tout le point
};


// ---------------------------------------------------------------------------
// COULEUR
// ---------------------------------------------------------------------------

// Conversion exacte sRGB → linéaire (par composante). 3 pow.
vec3 st_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}

// Conversion exacte linéaire → sRGB. 3 pow.
vec3 st_linear_to_srgb(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}

// Une couleur de PALETTE (sRGB, comme Vis et les ST_*) → l'espace où le
// renderer calcule l'éclairage : telle quelle en gl_compatibility (l'iPad),
// linéarisée en Forward+ / Mobile. À employer pour toute couleur de sommet,
// tout uniform sans `source_color` et toute constante ST_* avant ALBEDO.
vec3 st_albedo(vec3 srgb) {
#if defined(CURRENT_RENDERER) && CURRENT_RENDERER == RENDERER_COMPATIBILITY
	return srgb;
#else
	return st_srgb_to_linear(srgb);
#endif
}

// Luminance (coefficients Rec. 709), pour comparer deux valeurs de fil.
float st_luma(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}


// ---------------------------------------------------------------------------
// HASH ET BRUIT (Dave Hoskins : stables en précision GPU, sans sin)
// ---------------------------------------------------------------------------
// Entrées : des INDICES (entiers) de cellule, de rang, de case. Ne jamais
// hasher une valeur interpolée non arrondie (un varying n'est jamais tout à
// fait entier : le hash amplifie l'erreur et la cellule grésille) ; arrondir
// d'abord avec floor(x + 0.5). Sorties dans [0, 1[.

float st_hash11(float p) {
	p = fract(p * 0.1031);
	p *= p + 33.33;
	p *= p + p;
	return fract(p);
}

float st_hash21(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// Deux nombres indépendants pour le prix d'un.
vec2 st_hash22(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

float st_hash31(vec3 p) {
	vec3 p3 = fract(p * 0.1031);
	p3 += dot(p3, p3.zyx + 31.32);
	return fract((p3.x + p3.y) * p3.z);
}

// Bruit de valeur lissé (C1), 0..1, période de cellule 1. COÛTE 4 HASH :
// un seul par shader, et à effacer comme un motif (st_fade(1.0 / fréquence,
// px) vers 0,5) s'il est fin.
float st_vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 w = f * f * (3.0 - 2.0 * f);
	return mix(mix(st_hash21(i), st_hash21(i + vec2(1.0, 0.0)), w.x),
			mix(st_hash21(i + vec2(0.0, 1.0)), st_hash21(i + vec2(1.0, 1.0)), w.x), w.y);
}


// ---------------------------------------------------------------------------
// ANTI-MOIRÉ
// ---------------------------------------------------------------------------

// Empreinte d'un pixel, en unités de p : de combien p bouge, au pire, d'un
// pixel au suivant. p doit être CONTINU sur la surface (wpos.xz, une position
// locale…), jamais un fract() ni un indice. FRAGMENT SEULEMENT, hors branche.
float st_px(vec2 p) {
	return max(max(length(dFdx(p)), length(dFdy(p))), 1e-6);
}

// Empreinte selon un axe unitaire, à partir de dérivées déjà calculées
// (dpx = dFdx(p), dpy = dFdy(p)) : sert quand un motif est très allongé et
// qu'on veut l'effacer selon chacune de ses directions.
float st_px_axis(vec2 dpx, vec2 dpy, vec2 axis) {
	return max(abs(dot(dpx, axis)) + abs(dot(dpy, axis)), 1e-6);
}

// Visibilité d'un détail de taille `size` (même unité que px) : 0 sous
// ST_FADE_LO pixels, 1 au-delà de ST_FADE_HI pixels, lisse entre les deux.
//     valeur = mix(moyenne, détail, st_fade(taille, px));
float st_fade(float size, float px) {
	return smoothstep(ST_FADE_LO, ST_FADE_HI, size / max(px, 1e-6));
}

// Couverture EXACTE (filtre boîte d'un pixel) d'une bande |x| < hw : la part
// de [x - px/2, x + px/2] qui tombe dans la bande. Plus fine qu'un pixel, la
// bande pâlit en proportion (2·hw / px) au lieu de crépiter.
float st_band(float x, float hw, float px) {
	float a = max(x - 0.5 * px, -hw);
	float b = min(x + 0.5 * px, hw);
	return clamp((b - a) / max(px, 1e-6), 0.0, 1.0);
}

// Couverture filtrée du demi-plan d > 0 (d : distance signée, positive
// dedans, en unités de px). Bord antialiasé sur un pixel.
float st_step(float d, float px) {
	return clamp(d / max(px, 1e-6) + 0.5, 0.0, 1.0);
}


// ---------------------------------------------------------------------------
// GÉOMÉTRIE
// ---------------------------------------------------------------------------

// Rotation d'un vecteur du plan, angle en radians (sens trigonométrique).
vec2 st_rot(vec2 v, float a) {
	float c = cos(a);
	float s = sin(a);
	return vec2(c * v.x - s * v.y, s * v.x + c * v.y);
}

// Normale bombée : n (unitaire) penchée de tilt.x vers t et de tilt.y vers b
// (t, b : tangente du fil et direction « en travers », même espace que n).
vec3 st_bend(vec3 n, vec3 t, vec3 b, vec2 tilt) {
	return normalize(n + t * tilt.x + b * tilt.y);
}

// Pente d'un fil rond (cylindre) à la position u ∈ [-1, 1] en travers : 0 au
// sommet, ±2,5 aux bords (écrêtée : la vraie pente d'un cylindre est infinie
// au bord). C'est le tilt.y d'un fil de section ronde, avant amplitude.
float st_round(float u) {
	return u * inversesqrt(max(1.0 - u * u, 0.16));
}

// La torsade d'un fil retors : une crête hélicoïdale. s = abscisse le long
// du fil EN TOURS (1 = une torsade ; s = along / pas), u ∈ [-1, 1] en
// travers, lean = inclinaison de l'hélice (0,5 : diagonales franches ; le
// signe donne le sens de torsion ; lean·|u| donne un chevron, le point de
// chaînette). Rend x = hauteur de crête 0..1 (moyenne 0,5), yz = tilt (le
// long, en travers) d'amplitude 1, à multiplier par un relief et par
// st_fade(pas, px) : la torsade est le premier détail qui doit disparaître.
vec3 st_twist(float s, float u, float lean) {
	float ph = ST_TAU * (s + lean * u);
	float sn = sin(ph);
	return vec3(0.5 + 0.5 * cos(ph), sn, sn * lean);
}

// Repère d'hexagone POINTE EN HAUT (comme Hex : coins à -30° + 60°·i dans le
// plan xz, le nord vers -z). p = position relative au centre de la case
// (unités monde). Rend h, la distance « apothème » : 0 au centre, 0,866·R
// sur les arêtes d'un hexagone de rayon R (les lignes h = constante sont des
// hexagones concentriques : rangs de contour, liserés). Sorties :
//   t : abscisse le long de l'arête la plus proche, 0 au milieu de l'arête,
//       sens trigonométrique (de -h/√3 à +h/√3) ;
//   n : normale sortante de cette arête (unitaire, plan xz).
float st_hex(vec2 p, out float t, out vec2 n) {
	const vec2 N1 = vec2(0.5, 0.8660254);
	const vec2 N2 = vec2(-0.5, 0.8660254);
	vec3 a = vec3(p.x, dot(p, N1), dot(p, N2));
	vec3 aa = abs(a);
	float h;
	if (aa.x >= aa.y && aa.x >= aa.z) {
		h = aa.x;
		n = vec2(a.x >= 0.0 ? 1.0 : -1.0, 0.0);
	} else if (aa.y >= aa.z) {
		h = aa.y;
		n = N1 * (a.y >= 0.0 ? 1.0 : -1.0);
	} else {
		h = aa.z;
		n = N2 * (a.z >= 0.0 ? 1.0 : -1.0);
	}
	t = dot(p, vec2(-n.y, n.x));
	return h;
}

// L'index dans Hex.DIRS du voisin que regarde l'arête de normale n (sortie de
// st_hex) : 0 = est, 1 = nord-est, 2 = nord-ouest, 3 = ouest, 4 = sud-ouest,
// 5 = sud-est (à l'écran ; le nord est en haut). Rend un float entier 0..5.
float st_hex_dir(vec2 n) {
	float k = floor(-atan(n.y, n.x) / (ST_PI / 3.0) + 0.5);
	return mod(k + 6.0, 6.0);
}

// Coordonnées axiales (q, r) ENTIÈRES de la case sous un point du monde xz
// (inverse de Hex.to_world, arrondi cubique). Bonne graine de hash par case.
vec2 st_hex_axial(vec2 xz) {
	float r = xz.y / 1.5;
	float q = xz.x / ST_SQRT3 - r * 0.5;
	vec3 c = vec3(q, r, -q - r);
	vec3 rc = floor(c + 0.5);
	vec3 d = abs(rc - c);
	if (d.x > d.y && d.x > d.z) {
		rc.x = -rc.y - rc.z;
	} else if (d.y > d.z) {
		rc.y = -rc.x - rc.z;
	}
	return rc.xy;
}

// Centre (monde xz) de la case sous un point du monde xz.
vec2 st_hex_center(vec2 xz) {
	vec2 qr = st_hex_axial(xz);
	return vec2(ST_SQRT3 * (qr.x + qr.y * 0.5), 1.5 * qr.y);
}

// Spirale d'Archimède centrée en 0, `pitch` = écart entre deux tours (même
// unité que p). Rend (along, across) pour y coudre un point devant
// (st_running) : along ≈ longueur d'arc depuis le centre, across = distance
// signée au bras le plus proche. Calculer px sur p (st_px(p)), PAS sur along :
// along saute d'un bras à l'autre. Sert aux piqûres des nuages capitonnés.
vec2 st_spiral(vec2 p, float pitch) {
	float r = length(p);
	float a = atan(p.y, p.x) / ST_TAU + 0.5;   // 0..1
	float k = floor(r / pitch - a + 0.5);
	float turns = a + k;                         // tours depuis le centre
	float across = r - pitch * turns;
	float along = 0.5 * ST_TAU * pitch * turns * turns;
	return vec2(along, across);
}

// Semis régulier jitté : p tombe dans une cellule carrée de côté `cell` ; on
// rend deux nombres 0..1 propres à la cellule (1 hash) et, dans `local`, la
// position de p relative à un centre décalé au hasard dans la cellule (de
// ±0,25·cell). De quoi poser un motif par cellule (vaguelette, poisson,
// touffe) : il doit tenir dans un rayon de 0,25·cell autour de son centre.
// seed : un entier (arrondi ici) pour décorréler deux semis.
vec2 st_scatter(vec2 p, float cell, float seed, out vec2 local) {
	vec2 c = floor(p / cell);
	vec2 h = st_hash22(c + floor(seed + 0.5) * vec2(17.0, 59.0));
	vec2 jit = fract(h * vec2(7.13, 5.71) + vec2(0.31, 0.77)) - 0.5;
	local = p - (c + 0.5 + 0.5 * jit) * cell;
	return h;
}


// ---------------------------------------------------------------------------
// TOILE DE LIN
// ---------------------------------------------------------------------------

// Armure toile (un fil dessus, un dessous, en damier) : le fond de tout. p
// en unités monde, pitch = largeur d'un fil. Rend la hauteur de la toile,
// moyenne 0,5 (0,5 ± 0,27 de près), déjà effacée vers 0,5 sous ~2 px ; tilt
// reçoit l'inclinaison de normale (effacée aussi), d'amplitude ~0,5. Paraboles
// plutôt que sinus. Emploi :  col *= 1.0 + (h - 0.5) * 0.4;
float st_linen(vec2 p, float pitch, float px, out vec2 tilt) {
	vec2 q = p / pitch;
	vec2 c = floor(q);
	vec2 f = fract(q);
	float odd = mod(c.x + c.y, 2.0);
	vec2 b = 4.0 * f * (1.0 - f);          // bombé : 0 aux bords, 1 au milieu
	vec2 db = 4.0 - 8.0 * f;               // sa dérivée (par fil)
	float hw = b.x * (0.6 + 0.4 * b.y);    // fil de chaîne dessus
	float hf = b.y * (0.6 + 0.4 * b.x);    // fil de trame dessus
	vec2 gw = vec2(db.x * (0.6 + 0.4 * b.y), b.x * 0.4 * db.y);
	vec2 gf = vec2(b.y * 0.4 * db.x, db.y * (0.6 + 0.4 * b.x));
	float vis = st_fade(pitch, px);
	tilt = -mix(gw, gf, odd) * 0.125 * vis;
	// 0,578 : moyenne de la hauteur brute sur un motif entier.
	return 0.5 + (mix(hw, hf, odd) - 0.578) * vis;
}


// ---------------------------------------------------------------------------
// POINT DEVANT (tirets cousus le long d'une ligne)
// ---------------------------------------------------------------------------

// Une suite de points de longueur `len` séparés de `gap`, centrés sur la
// ligne across = 0 et d'épaisseur `width` (unités monde). Le point k occupe
// along ∈ [k·(len+gap) - len/2, k·(len+gap) + len/2] : ajouter un décalage à
// along pour faire glisser la couture. Bouts arrondis ; le fil est rond en
// travers et plonge dans la toile aux deux bouts. gap = 0 : un trait continu
// (couché, contour) de couverture filtrée.
// Rend cover (filtrée exactement en travers et le long), tilt (rond en
// travers : ±~1 ; bouts : ±~0,6), shade (moyenne 1 en travers), u, rnd
// (propre au point, sans hash). Au loin : les tirets fondent en un trait de
// couverture moyenne len / (len + gap) ; le trait lui-même pâlit sous 1 px.
StThread st_running(float along, float across, float len, float gap, float width, float px) {
	StThread s;
	float period = max(len + gap, 1e-5);
	float k = floor(along / period + 0.5);
	float a = along - k * period;                     // 0 au milieu du point
	float hl = 0.5 * len;
	float hw = 0.5 * width;
	float vis_dash = st_fade(min(len, gap) * 2.0, px); // les tirets se séparent
	float vis_shape = st_fade(width * 2.0, px);       // le rond du fil se voit
	// Bouts arrondis : la demi-largeur se resserre sur le dernier hw.
	float e = clamp((abs(a) - (hl - hw)) / max(hw, 1e-6), 0.0, 1.0);
	float hw_e = hw * mix(1.0, sqrt(max(1.0 - e * e, 0.0)), vis_dash * vis_shape);
	float c_across = st_band(across, hw_e, px);
	float c_along = mix(len / period, st_band(a, hl, px), vis_dash);
	s.cover = c_across * c_along;
	s.tie = 0.0;
	s.u = clamp(across / max(hw_e, 1e-6), -1.0, 1.0);
	float ve = vis_dash * vis_shape;
	s.tilt = vec2(sign(a) * e * 0.6 * ve, st_round(s.u) * 0.4 * vis_shape);
	s.shade = 1.0 + (0.12 * (0.3333 - s.u * s.u) - 0.15 * e * e) * vis_shape;
	s.rnd = fract(k * 0.6180339 + 0.31);
	return s;
}

// Point devant qui suit le contour d'un hexagone, à la distance-apothème
// `ring` de son centre (une case a ses arêtes à 0,866 : ring = 0,80 coud un
// peu en retrait). p = position relative au centre de la case. Le nombre de
// points par côté est ENTIER (le pas réel s'ajuste au plus près de
// len + gap), et chaque côté commence et finit par un demi-espace : les six
// côtés se raccordent proprement aux coins. Mêmes sorties que st_running ;
// pour savoir quel côté on coud (frontières), st_hex(p, t, n) et st_hex_dir(n).
// st_hex_running_ht : le même, sur le h et le t qu'un shader a déjà tirés de
// st_hex(p, t, n) pour le même p (il épargne un second st_hex).
StThread st_hex_running_ht(float h, float t, float ring, float len, float gap, float width, float px) {
	float side = ring * 1.1547005;                      // côté de l'anneau : 2·ring / √3
	float count = max(floor(side / max(len + gap, 1e-5) + 0.5), 1.0);
	float per = side / count;
	float len_e = per * len / max(len + gap, 1e-5);
	float along = t + 0.5 * side - 0.5 * per;           // points centrés sur k·per
	return st_running(along, h - ring, len_e, per - len_e, width, px);
}

StThread st_hex_running(vec2 p, float ring, float len, float gap, float width, float px) {
	float t;
	vec2 n;
	float h = st_hex(p, t, n);
	return st_hex_running_ht(h, t, ring, len, gap, width, px);
}


// ---------------------------------------------------------------------------
// SATIN « LONG AND SHORT » (remplissage orienté)
// ---------------------------------------------------------------------------

// Des rangées parallèles de points couchés le long de uv.x, posées côte à
// côte en travers (uv.y), décalées comme des briques et de longueurs
// inégales (les bouts ne s'alignent jamais) : l'opus anglicanum, la
// tapisserie de Bayeux.
//   uv     : (le long, en travers) dans le repère du fil, unités monde ;
//            orienter avec st_rot (ex. uv = st_rot(p, -angle)).
//   w      : largeur d'un fil (pas des rangées) ; len : longueur moyenne
//            d'un point (±25 % selon le rang).
//   seed   : graine de la pièce, 0..1 (quantifiée au 1/256 : stable même
//            interpolée).
//   bump   : relief du fil (0,3 : bombé discret ; inclinaison max ≈ 1,1·bump).
//   jitter : écart de valeur d'un point à l'autre (±, dans shade ; 0,05).
// Rend cover (les trous minuscules au bout des points ; moyenne 0,95 =
// ST_SATIN_COVER, vers laquelle elle fond au loin), shade (rainures entre
// rangs, bouts qui plongent, valeur propre au point : moyenne 1), tilt
// (cylindre en travers, plongée aux bouts), u, rnd (propre au point).
// Coût : 1 hash.
StThread st_satin(vec2 uv, float w, float len, float seed, float bump, float jitter, float px) {
	StThread s;
	float sq = floor(seed * 256.0 + 0.5);
	float sv = uv.y / w;
	float j = floor(sv);
	float hr = st_hash11(j + sq * 7.0);                // propre au rang
	float L = len * (0.75 + 0.5 * fract(hr * 13.7));   // long and short
	float off = 0.5 * mod(j, 2.0) + (hr - 0.5) * 0.45;
	float tt = uv.x / L + off;
	float i = floor(tt);
	vec2 cell = vec2(sv - j, tt - i);                  // x en travers, y le long (0..1)
	float vis_row = st_fade(w * 0.6, px);              // rondeur et rainures
	float vis_end = st_fade(L * 0.36, px);             // plongée aux bouts
	float vis_gap = st_fade(L * 0.25, px) * vis_row;   // trous au bout des points
	float u = cell.x * 2.0 - 1.0;
	float au = abs(u);
	// Bouts : le fil plonge dans la toile sur 18 % de sa longueur.
	float s0 = clamp(cell.y / 0.18, 0.0, 1.0);
	float s1 = clamp((1.0 - cell.y) / 0.18, 0.0, 1.0);
	float end_h = smoothstep(0.0, 1.0, s0) * smoothstep(0.0, 1.0, s1);
	float end_slope = 1.5 * (s0 * (1.0 - s0) - s1 * (1.0 - s1));
	s.tilt = vec2(-end_slope * bump * vis_end, u * (0.6 + 0.5 * au * au) * bump * vis_row);
	// Ombres peintes, chacune de moyenne nulle (0,073 et 0,154 : moyennes des
	// profils sur un point entier) : la teinte au loin est celle du fil.
	float d_side = 1.0 - smoothstep(0.0, 0.4, 1.0 - au * au * au);
	float d_end = 1.0 - smoothstep(0.0, 0.8, end_h);
	s.rnd = fract(hr * 7.31 + i * 0.6180339);
	float val = (s.rnd - 0.5) * 2.0 * jitter * vis_end + (hr - 0.5) * 0.02 * vis_row;
	s.shade = (1.0 - 0.10 * (d_side - 0.073) * vis_row) * (1.0 - 0.22 * (d_end - 0.154) * vis_end) + val;
	float holes = smoothstep(0.0, 0.05, cell.y) * smoothstep(0.0, 0.05, 1.0 - cell.y);
	s.cover = mix(ST_SATIN_COVER, holes, vis_gap);
	s.tie = 0.0;
	s.u = u;
	return s;
}


// ---------------------------------------------------------------------------
// SEMIS (seed stitch : petits points droits épars)
// ---------------------------------------------------------------------------

// Au plus un petit point droit par cellule carrée de côté `cell`, présent
// avec la probabilité `density` (0..1), de longueur `len` et d'épaisseur
// `width`, orienté et placé au hasard dans sa cellule (il n'en déborde
// jamais). p en unités monde ; seed : un entier (arrondi ici). Le point de
// semis des plaines de lin. Au loin, cover fond vers la couverture moyenne
// (density · aire du point / cell²) : une légère teinte, jamais un grésillement.
// Coût : 1 hash, 1 cos, 1 sin.
StThread st_seed(vec2 p, float cell, float len, float width, float density, float seed, float px) {
	StThread s;
	vec2 c = floor(p / cell);
	vec2 h = st_hash22(c + floor(seed + 0.5) * vec2(23.0, 41.0));
	float ang = h.x * ST_PI;
	vec2 dir = vec2(cos(ang), sin(ang));
	float room = max(cell - len - width, 0.0);
	vec2 jit = (fract(h * vec2(7.13, 5.71) + vec2(0.31, 0.77)) - 0.5) * room;
	vec2 q = p - (c + 0.5) * cell - jit;
	float along = dot(q, dir);
	float across = dot(q, vec2(-dir.y, dir.x));
	float present = step(fract((h.x + h.y) * 9.73), density);
	float hl = 0.5 * len;
	float hw = 0.5 * width;
	float vis = st_fade(cell, px) * st_fade(len, px);
	float vis_shape = st_fade(width * 2.0, px) * vis;
	float e = clamp((abs(along) - (hl - hw)) / max(hw, 1e-6), 0.0, 1.0);
	float hw_e = hw * sqrt(max(1.0 - e * e, 0.0));
	float near_cover = st_band(across, hw_e, px) * st_band(along, hl, px) * present;
	float mean_cover = density * (len * width - 0.8584 * hw * hw) / (cell * cell);
	s.cover = mix(mean_cover, near_cover, vis);
	s.tie = 0.0;
	s.u = clamp(across / max(hw_e, 1e-6), -1.0, 1.0);
	// Le repère du point tourne : tilt est rendu dans le repère MONDE du plan
	// (x, y = axes de p), pas le long / en travers.
	vec2 tl = vec2(sign(along) * e * 0.6, st_round(s.u) * 0.4) * vis_shape * present;
	s.tilt = dir * tl.x + vec2(-dir.y, dir.x) * tl.y;
	s.shade = 1.0 + (0.12 * (0.3333 - s.u * s.u) - 0.15 * e * e) * vis_shape;
	s.rnd = fract(h.y * 3.17 + h.x * 0.53);
	return s;
}


// ---------------------------------------------------------------------------
// CORDON COUCHÉ (couching : un gros fil posé, tenu par des points de fixation)
// ---------------------------------------------------------------------------

// Un cordon retors de demi-largeur `hw`, posé le long de across = 0, et
// maintenu tous les `tie_pitch` par un petit point de fixation en travers
// (un fil fin posé dessus, un rien plus large que le cordon). twist_pitch :
// pas de la torsade (0 = cordon lisse). Les rivières, les liserés d'or, les
// frontières riches.
// Rend cover (le cordon), tie (part couverte par une fixation : la peindre
// par-dessus, st_paint_tie), shade (torsade, moyenne 1), tilt (rond du
// cordon, stries de torsade ; rond de la fixation là où elle passe), u, rnd
// (propre à l'intervalle entre deux fixations). Au loin : cordon uni,
// fixations fondues en leur couverture moyenne.
StThread st_couched(float along, float across, float hw, float twist_pitch, float tie_pitch, float px) {
	StThread s;
	s.cover = st_band(across, hw, px);
	s.u = clamp(across / max(hw, 1e-6), -1.0, 1.0);
	float vis_round = st_fade(hw * 2.0, px);
	float tp = max(twist_pitch, 1e-5);
	float vis_tw = st_fade(tp, px) * vis_round * step(1e-5, twist_pitch);
	vec3 tw = st_twist(along / tp, s.u, 0.55);
	s.tilt = vec2(tw.y * 0.25 * vis_tw, st_round(s.u) * 0.45 * vis_round + tw.z * 0.25 * vis_tw);
	s.shade = 1.0 + (tw.x - 0.5) * 0.24 * vis_tw - 0.10 * (s.u * s.u - 0.3333) * vis_round;
	// Les fixations : un fil fin (0,35·hw de large) en travers, tous les tie_pitch.
	float k = floor(along / max(tie_pitch, 1e-5) + 0.5);
	float a = along - k * tie_pitch;
	float thw = 0.18 * hw;
	float vis_tie = st_fade(tie_pitch, px) * st_fade(thw * 4.0, px);
	float near_tie = st_band(a, thw, px) * st_band(across, hw * 1.15, px);
	float mean_tie = (2.0 * thw / max(tie_pitch, 1e-5)) * st_band(across, hw * 1.15, px);
	s.tie = mix(mean_tie, near_tie, vis_tie);
	float ut = clamp(a / max(thw, 1e-6), -1.0, 1.0);
	s.tilt = mix(s.tilt, vec2(st_round(ut) * 0.4, s.u * 0.3) * vis_tie, clamp(near_tie * vis_tie, 0.0, 1.0));
	s.rnd = fract(k * 0.6180339 + 0.17);
	return s;
}

// Poser un fil sur ce qui est dessous : la couleur du fil, ombrée, là où il
// couvre. under et thread dans l'espace du renderer (st_albedo).
vec3 st_paint(vec3 under, vec3 thread, StThread s) {
	return mix(under, thread * s.shade, s.cover);
}

// Poser les points de fixation d'un cordon couché (après st_paint).
vec3 st_paint_tie(vec3 col, vec3 tie_col, StThread s) {
	return mix(col, tie_col, s.tie);
}


// ---------------------------------------------------------------------------
// CONTOUR (le fil brun autour de tout) ET SOIE
// ---------------------------------------------------------------------------

// Contour de demi-largeur hw le long de l'iso-ligne d = 0 d'une distance
// (signée ou non), filtré : st_band(d, hw, px). Peindre avec ST_BRUN. Pour
// un contour posé à l'intérieur d'une forme de distance signée d (> 0 dedans),
// passer d - hw.
float st_outline(float d, float hw, float px) {
	return st_band(d, hw, px);
}

// Bord de silhouette d'une pièce en relief (le contour brun des figurines,
// des bâtiments) : 1 là où la surface fuit le regard, 0 de face. N, V : la
// normale et la direction de vue, même espace (NORMAL et VIEW dans
// fragment()). width : épaisseur en 1 - N·V (0,25 : liseré net ; 0,4 :
// large). Antialiasé par fwidth : à appeler HORS de toute branche. Emploi :
//     ALBEDO = mix(ALBEDO, st_albedo(ST_BRUN), st_rim(NORMAL, VIEW, 0.3) * 0.85);
float st_rim(vec3 N, vec3 V, float width) {
	float ndv = clamp(dot(N, V), 0.0, 1.0);
	float fw = max(fwidth(ndv), 0.01);
	return 1.0 - smoothstep(width - fw, width + fw, ndv);
}

// Reflet de soie PEINT (dans fragment(), sans light()) : une bande claire en
// travers d'un fil, centrée en u = center (-1..1 ; -0,3 : côté lumière),
// de demi-largeur width (en unités de u). Rend 0..1 (profil (1 - x²)²).
// À multiplier par une intensité et par st_fade(largeur du fil, px) : un
// reflet de 1 px rampe et paillette quand la caméra glisse.
float st_sheen(float u, float center, float width) {
	float x = clamp((u - center) / max(width, 1e-4), -1.0, 1.0);
	float y = 1.0 - x * x;
	return y * y;
}

// Reflet anisotrope de Kajiya-Kay (dans light()) : T = tangente du fil, H =
// demi-vecteur normalize(LIGHT + VIEW), même espace (vue). Le reflet s'étale
// EN TRAVERS du fil et glisse avec la vue : c'est l'éclat du satin. shin :
// finesse (60 à 150). Emploi dans light() :
//     float k = st_silk(v_T, normalize(LIGHT + VIEW), 120.0);
//     SPECULAR_LIGHT += LIGHT_COLOR * ATTENUATION * k * 0.1;
float st_silk(vec3 T, vec3 H, float shin) {
	float th = dot(T, H);
	return pow(max(1.0 - th * th, 0.0), shin * 0.5);
}

// Exposant maximal d'un filet de lumière (N·H)^e sur un fil bombé, pour qu'il
// reste large d'au moins ~3 pixels (sinon il crépite en mouvement).
//   tilt   : inclinaison maximale de la normale sur la largeur d'un fil
//   px_per : px / largeur du fil (fils par pixel)
//   e_max  : l'exposant voulu de près.
float st_lobe_exp(float tilt, float px_per, float e_max) {
	float e = 0.155 / max(tilt * tilt * px_per * px_per, 0.000001);
	return clamp(e, 6.0, e_max);
}

#endif
