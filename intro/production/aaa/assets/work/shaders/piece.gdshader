shader_type spatial;
// Les pièces (figurines, colonies, bâtiments, aménagements) : de la broderie
// EN RELIEF (stumpwork) posée sur la carte de lin.
//
// UN APPEL DE DESSIN PAR PIÈCE. Models.merged fond toutes les matières
// Blender d'un maillage en une seule surface, et y coud la coque du contour :
//   COLOR.rgb  la couleur de palette de la matière (sRGB, Models.PALETTE) ;
//   COLOR.a    son code : genre × 16 + rôle (Models.code). Genre : 0 plein,
//              1 fenêtre (s'allume la nuit), 2 feu, 3 fil d'argent (métal),
//              4 eau, 5 blason (l'écu d'une figurine : le champ à la couleur
//              du peuple, le meuble `charge` brodé dessus, cerné de brun ;
//              voir pc_charge). Rôle : 0 la couleur du sommet, 1 le peuple
//              (team), 2 le peuple assombri (team_dark), 3 le champ du blason,
//              4 les cultures (crop), 5 le feuillage (leaf), 6 à 13 les
//              toits des maisons (roofs[rôle - 6], Models.ROOF_NAMES : chaque
//              ville permute les paires frais / vieilli et nuance l'éclat
//              selon sa case, au sommet : aucun coût au pixel), 14 les toits
//              civiques (tours, chapelle, porte : un matériau par ville) ;
//   UV2        nul sur la pièce ; la normale lissée sur sa coque (le fil brun
//              qui la cerne, poussé de quelques pixels : pc_outline).
// Ce qui dépend du peuple (team, blason), de la saison (crop, leaf) ou de
// l'état (neige, dégâts, figurine) est porté par la MATIÈRE, une par ton de
// peuple et par état, partagée.
//
// Une matière d'un seul tenant (`solid` : projectiles, Models.mat) prend sa
// couleur et son genre dans `albedo` et `kind`, sans coque (son contour est
// la passe suivante, piece_outline.gdshader).
//
// Projection oblique, éclairage de broderie couchée et satin par facette :
// voir view/shaders/stitch_pieces.gdshaderinc.

render_mode skip_vertex_transform, diffuse_lambert, specular_disabled, shadows_disabled;

#include "res://view/shaders/stitch.gdshaderinc"
#include "res://view/shaders/stitch_pieces.gdshaderinc"

uniform bool solid = false;
uniform vec3 albedo : source_color = vec3(0.8);
uniform int kind = 0;
// Les fils de la matière.
uniform vec3 team : source_color = vec3(0.8);
uniform vec3 team_dark : source_color = vec3(0.56);
uniform vec3 crop : source_color = vec3(0.494, 0.541, 0.282);
uniform vec3 leaf : source_color = vec3(0.431, 0.478, 0.259);
// Les toits des maisons (rôles 6 à 13), en sRGB comme les couleurs de sommet
// (pas de source_color : ils passent par st_albedo). Models._roof_colors.
uniform vec3 roofs[8];
// Le blason (genre 5) : le meuble (pc_charge : 0 plein, 1 croix, 2 soleil,
// 3 sautoir, 4 fleur de lis) et sa couleur. Les UV de la face avant portent le
// repère de l'écu (tools/blender/kit.py, Part.blazon).
uniform int charge = 0;
uniform vec3 charge_col : source_color = vec3(0.91, 0.85, 0.73);

// L'état de la pièce, porté par la MATIÈRE (Models en garde une par état) :
// la neige tient-elle (pas sur les figurines), dégâts (brûlé). Pas d'uniform
// d'instance : en gl_compatibility leur tampon est plafonné (4096 cases ici,
// moins sur iPad) et une partie avancée le remplit. L'éclair de coup reçu
// est une matière de surimpression (piece_flash.gdshader).
uniform float snowy = 1.0;
uniform float damage = 0.0;
// Une figurine (Models.FIGURE) : la nuit, ses fils gardent un peu de leur
// couleur (comme sous une lanterne) ; les unités restent les pièces les plus
// lisibles de la carte quand la toile bleuit.
uniform float figure = 0.0;

// Le contour (la coque) : épaisseur visée en unités monde, bornée en pixels
// (les figurines : Models.FIG_OUTLINE, plus gros).
uniform float width_world = 0.02;
uniform float width_min = 1.2;
uniform float width_max = 2.4;
uniform float ref_h = 1200.0;

global uniform float g_night;
global uniform float g_snow;
global uniform vec4 g_veil;

varying vec3 v_q;    // position dans le repère du modèle, à l'échelle du monde
varying vec3 v_nm;   // normale dans le repère du modèle
varying vec3 v_nw;   // normale du monde, NON cisaillée (éclairage, neige)
varying vec3 v_wp;   // position du monde, non cisaillée (le feu)
varying flat vec3 v_col;    // la couleur du fil (déjà dans l'espace du renderer)
varying flat float v_kind;  // le genre
varying flat float v_hull;  // 1 sur la coque
// -1 sur une pièce posée en miroir (un bâtiment à gauche de la place) : le
// fil y est couché et éclairé comme sur un modèle non retourné de même forme
// (sans cela le reflet de soie passe du côté de l'ombre).
varying flat float v_mirror;
varying flat float v_roof;  // 1 sur ce que la neige ne fait que saupoudrer :
                            // un toit (la ville) ou un fil du peuple (à qui)

void vertex() {
	v_hull = solid ? 0.0 : pc_is_hull(UV2);
	v_roof = 0.0;
	v_mirror = determinant(mat3(MODEL_MATRIX)) < 0.0 ? -1.0 : 1.0;
	if (v_hull > 0.5) {
		vec3 nv;
		VERTEX = pc_outline(VERTEX, NORMAL, UV2, MODEL_MATRIX, MODEL_NORMAL_MATRIX, VIEW_MATRIX, PROJECTION_MATRIX,
				width_world, width_min, width_max, ref_h, nv);
		NORMAL = nv;
		v_q = vec3(0.0);
		v_nm = vec3(0.0, 1.0, 0.0);
		v_nw = v_nm;
		v_wp = vec3(0.0);
		v_col = vec3(0.0);
		v_kind = 0.0;
	} else {
		vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		vec3 nw = normalize(MODEL_NORMAL_MATRIX * NORMAL);
		vec3 mir = vec3(v_mirror, 1.0, 1.0);
		v_q = VERTEX * mir * length(MODEL_MATRIX[0].xyz);
		v_nm = NORMAL * mir;
		v_nw = nw;
		v_wp = w;
		// La couleur du fil, une fois par sommet : celle du sommet (palette
		// sRGB : st_albedo) ou celle que la matière porte pour son rôle
		// (uniform source_color : tel quel).
		int code = int(COLOR.a * 255.0 + 0.5);
		int role = code % 16;
		vec3 c = st_albedo(COLOR.rgb);
		if (role == 1 || role == 3) {
			c = team;
			v_roof = 1.0;
		} else if (role == 2) {
			c = team_dark;
			v_roof = 1.0;
		} else if (role == 4) {
			c = crop;
		} else if (role == 5) {
			c = leaf;
		} else if (role >= 6 && role <= 14 && !solid) {
			// (une matière d'un seul tenant n'a pas de couleur de sommet : COLOR
			// vaut 1, son code 255 ; elle n'est pas un toit)
			// Un toit de maison : sa ville (la case sous l'origine de la pièce,
			// la même pour toute la ville) permute chaque paire frais / vieilli
			// à pile ou face, et nuance l'éclat de ±5 %. Jamais au sommet près
			// (v_col est plat : une face se fendrait en deux tons).
			vec2 cell = st_hex_axial(MODEL_MATRIX[3].xz);
			int i = min(role - 6, 8);
			int j = i;
			if (i == 8) {
				// Les toits civiques : tuile (40 %), ardoise (30 %), vieille
				// tuile (15 %) ou plomb (15 %), un seul pour toute la ville.
				float hc = st_hash21(cell + vec2(29.0, 7.0));
				j = hc < 0.4 ? 0 : (hc < 0.7 ? 4 : (hc < 0.85 ? 1 : 6));
			} else if (i < 6 && st_hash21(cell + vec2(float(i / 2) * 17.0, 3.0)) > 0.5) {
				j = i + 1 - 2 * (i % 2);
			}
			c = st_albedo(roofs[j]) * (0.95 + 0.1 * st_hash21(cell + vec2(float(j) * 5.0, 11.0)));
			v_roof = 1.0;
		}
		v_col = solid ? albedo : c;
		v_kind = solid ? float(kind) : float(code / 16);
		VERTEX = (VIEW_MATRIX * vec4(pc_shear(w, 1.0), 1.0)).xyz;
		NORMAL = normalize((VIEW_MATRIX * vec4(pc_shear_normal(nw, 1.0), 0.0)).xyz);
	}
}

void fragment() {
	// D'abord, hors de toute branche : l'empreinte du pixel et le bord de
	// silhouette (NORMAL est encore la vraie normale, cisaillée, en vue).
	float px = pc_px(v_q);
	float rim = st_rim(NORMAL, VIEW, 0.16);
	// Le repère de l'écu (le glTF retourne v) et l'empreinte d'un pixel dedans.
	vec2 bp = vec2(UV.x, 1.0 - UV.y);
	float bpx = max(max(length(dFdx(bp)), length(dFdy(bp))), 1e-6);

	if (v_hull > 0.5) {
		// La coque : le fil brun, ni éclairé ni voilé (ce qu'était la passe
		// unshaded et fog_disabled du contour). Sans albédo, la lumière n'y
		// ajoute rien ; l'émission porte le fil.
		ALBEDO = vec3(0.0);
		EMISSION = pc_hull_color(g_night);
		FOG = vec4(0.0);
	} else {
		vec3 nm = normalize(v_nm);
		vec3 nw = normalize(v_nw);
		vec3 T;
		vec3 B;
		vec2 uv = pc_uv(nm, v_q, T, B);
		float metal = step(2.5, v_kind) * step(v_kind, 3.5);
		// Le fil d'argent est plus fin et plus serré que la laine.
		float w = PC_SATIN_W * (1.0 - 0.3 * metal);
		StThread s = st_satin(uv, w, PC_SATIN_LEN, 0.37, 0.35, 0.05, px);

		vec3 base = v_col;
		// Le blason : le meuble crème (ou brique) sur le champ, puis son liseré
		// brun. Quand l'écu tombe sous une dizaine de pixels, le meuble se fond
		// dans le champ (sa part moyenne) au lieu de grésiller.
		float b_line = 0.0;
		if (v_kind > 4.5) {
			float d = pc_charge(bp, charge);
			float has = step(0.5, float(charge));
			float vis = 1.0 - smoothstep(0.16, 0.36, bpx);
			float cov = mix(0.24 * step(abs(bp.x), 1.5), st_step(-d, bpx), vis) * has;
			base = mix(base, charge_col, cov);
			b_line = st_band(d, 0.05, bpx) * vis * has;
		}
		// La neige : un fil crème sur ce qui regarde le ciel (pas les fenêtres).
		// (une facette l'est ou ne l'est pas : pas de toits roses).
		float sn = g_snow * snowy * smoothstep(0.56, 0.62, nw.y) * step(v_kind, 0.5);
		// (un toit, un fil du peuple ne sont que saupoudrés : leur couleur dit
		// encore la ville et à qui elle est)
		sn *= 1.0 - 0.65 * v_roof;
		base = mix(base, st_albedo(vec3(0.83, 0.815, 0.77)), sn);
		// Brûlé : plus sombre et terne.
		float lum = st_luma(base);
		base = mix(base, vec3(lum) * 0.35, damage * 0.8);

		// Le fil sur sa toile (le fond entre les points est le même fil, à l'ombre).
		vec3 col = st_paint(base * 0.62, base, s);
		col = mix(col, st_albedo(ST_BRUN), b_line * 0.85);
		// Le reflet de soie, peint du côté de la lumière (la gauche), effacé de
		// loin ; plus vif sur le fil d'argent, éteint la nuit.
		float vis = st_fade(w, px);
		col += base * st_sheen(s.u, -0.3, 0.6) * (0.14 + 0.22 * metal) * vis * (1.0 - 0.7 * g_night);
		// Le contour intérieur : là où la surface fuit le regard, le fil brun.
		col = mix(col, st_albedo(ST_BRUN), rim * 0.6);

		ALBEDO = col;

		// L'éclairage de la broderie couchée, bombé par le fil.
		vec3 mir = vec3(v_mirror, 1.0, 1.0);
		vec3 Tw = normalize(mat3(MODEL_MATRIX) * (T * mir));
		vec3 Bw = normalize(mat3(MODEL_MATRIX) * (B * mir));
		vec3 nl = pc_relief(st_bend(nw, Tw, Bw, s.tilt * s.cover));
		NORMAL = normalize((VIEW_MATRIX * vec4(nl, 0.0)).xyz);

		// La nuit, un plancher de luminance pour les figurines : leurs fils
		// sombres (cuir, tunique) sont relevés plus que les clairs, sans briller
		// (l'or ne tourne pas au gris-olive, l'armure reste sous la lanterne).
		float fl = g_night * figure;
		vec3 emit = col * fl * (0.32 + 0.38 * (1.0 - clamp(st_luma(col) * 1.6, 0.0, 1.0)));
		if (v_kind > 0.5 && v_kind < 1.5) {
			// Fenêtres : un fil d'or qui s'allume à la nuit tombée.
			emit = st_albedo(vec3(0.93, 0.70, 0.36)) * (0.02 + g_night * 1.05) * (1.0 - damage);
		} else if (v_kind > 1.5 && v_kind < 2.5) {
			float f = 0.85 + 0.15 * sin(TIME * 11.0 + v_wp.x * 17.0) * sin(TIME * 7.3 + v_wp.z * 11.0);
			emit = v_col * (0.55 + g_night * 0.9) * f;
		}
		EMISSION = emit;
		// Le voile de la veille (écrire FOG remplace celui du moteur).
		FOG = pc_veil(VERTEX, g_veil);
	}
}
