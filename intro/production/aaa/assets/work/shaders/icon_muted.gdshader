// Les icônes de l'interface, BRODÉES : les illustrations d'assets/icons
// (saturées, peintes) deviennent du fil sur le lin de la tapisserie
// (docs/DIRECTION_TAPISSERIE.md), sans être redessinées une à une :
//  1. la couleur rejoint la palette : chaque teinte est ramenée vers son fil
//     (rouge → brique, jaune → or, vert → sapin clair, bleu → denim…), la
//     saturation baisse, les valeurs se resserrent (noir → fil brun, blanc →
//     crème) ;
//  2. la matière : un satin de points parallèles dont la direction change
//     d'une plage de couleur à l'autre, comme des blocs de broderie, et dont
//     les rangs se décalent (point lancé long et court) ; le motif s'efface
//     sous ~2 px (anti-moiré) ;
//  3. le relief : un cerne de fil brun autour de la silhouette (point arrière)
//     et une ombre courte vers le bas-droite (la broderie est posée SUR la
//     toile, lumière du haut-gauche).
// Interface seulement (canvas_item) : 10 lectures de la texture, 1 hachage,
// aucune boucle. Les icônes ont des mipmaps (UiTheme.icon), si bien que les
// lectures décalées restent nettes à toutes les tailles.
shader_type canvas_item;

// Part de saturation propre gardée (le reste part vers la teinte de palette).
uniform float garde = 0.28;
// Force de la recoloration vers la palette (0 : couleur d'origine sourde).
uniform float palette = 0.85;
// Relief des points (0 : aucun).
uniform float points = 1.0;
// Le cerne brun (0 : aucun).
uniform float cerne = 1.0;
// L'ombre portée (0 : aucune).
uniform float ombre = 1.0;
uniform vec4 fil_brun : source_color = vec4(0.231, 0.153, 0.067, 1.0);

const vec3 LUMA = vec3(0.299, 0.587, 0.114);

varying vec4 v_mod;

void vertex() {
	// La modulation de l'objet (une icône grisée, un fondu) : gardée à part,
	// la couleur est recomposée depuis la texture seule.
	v_mod = COLOR;
}

// La couleur de fil de la palette pour une teinte h (0..1, cercle HSV).
vec3 fil_de(float h) {
	vec3 brique = vec3(0.608, 0.231, 0.141);
	vec3 rouille = vec3(0.640, 0.400, 0.200);
	vec3 or_ = vec3(0.706, 0.573, 0.282);
	vec3 sapin = vec3(0.369, 0.420, 0.227);
	vec3 vert_eau = vec3(0.310, 0.420, 0.395);
	vec3 denim = vec3(0.290, 0.392, 0.471);
	vec3 prune = vec3(0.400, 0.300, 0.440);
	vec3 lie = vec3(0.500, 0.230, 0.270);
	vec3 c = mix(brique, rouille, smoothstep(0.0, 0.07, h));
	c = mix(c, or_, smoothstep(0.07, 0.13, h));
	c = mix(c, sapin, smoothstep(0.15, 0.27, h));
	c = mix(c, vert_eau, smoothstep(0.36, 0.46, h));
	c = mix(c, denim, smoothstep(0.46, 0.58, h));
	c = mix(c, prune, smoothstep(0.66, 0.76, h));
	c = mix(c, lie, smoothstep(0.80, 0.88, h));
	c = mix(c, brique, smoothstep(0.90, 0.98, h));
	return c;
}

vec3 hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-6)), d / (q.x + 1e-6), q.x);
}

float h12(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	vec2 px = max(fwidth(UV), vec2(1e-5));   // un pixel d'écran, en UV
	float taille = 1.0 / px.x;               // largeur affichée, en pixels
	vec4 t = texture(TEXTURE, UV);
	vec3 c = t.rgb;

	// 1. La couleur.
	float l = dot(c, LUMA);
	vec3 s = hsv(c);
	vec3 fil = fil_de(s.x);
	vec3 teint = fil * (l / max(dot(fil, LUMA), 0.04));
	// (le fil garde un peu plus de corps que la palette des grands aplats)
	teint = mix(vec3(l), teint, 1.2);
	float k = smoothstep(0.10, 0.45, s.y) * palette;
	vec3 gris = vec3(l) * vec3(1.05, 1.0, 0.90);
	c = mix(mix(gris, c, garde), teint, k);
	// Les valeurs se resserrent : rien de plus noir que le fil brun, rien
	// de plus blanc que la crème ; les ombres virent au brun. Un peu de
	// contraste d'abord, pour que le dessin intérieur reste lisible.
	// Une broderie n'a pas de dégradé continu : quelques tons de fil par
	// couleur (cinq), dont le passage reste doux à l'écran.
	float lq = l * 5.0;
	float w = clamp(fwidth(lq) * 0.75, 0.05, 0.5);
	float ton = floor(lq) + smoothstep(0.5 - w, 0.5 + w, fract(lq));
	float lc = smoothstep(0.0, 1.0, mix(l, ton / 5.0, 0.6));
	lc = mix(l, lc, 0.75);
	float l2 = mix(0.12, 0.83, lc);
	c = clamp(c * (l2 / max(l, 0.02)), 0.0, 1.0);
	c = mix(c, fil_brun.rgb * 1.15, smoothstep(0.30, 0.04, l) * 0.75);

	// 2. Les points de satin. Le pas suit la taille de l'icône (entre 2,2 et
	// 4,4 px) ; il s'efface quand il devient trop fin pour l'écran.
	float pas = clamp(taille / 26.0, 2.2, 4.4);
	vec2 p = UV / px;                        // position en pixels d'écran
	// La plage : teinte et valeur grossières ; sa direction, au hasard parmi
	// quatre (0°, 45°, 90°, 135°).
	float plage = floor(s.x * 8.0) + 8.0 * floor(lq + 0.5) + 61.0 * step(0.12, s.y);
	float ang = floor(h12(vec2(plage, 7.0)) * 4.0) * 0.7854 + 0.35;
	vec2 dir = vec2(cos(ang), sin(ang));
	float u = dot(p, vec2(-dir.y, dir.x)) / pas;   // à travers les points
	float v = dot(p, dir) / (pas * 3.2);           // le long des points
	float rang = floor(u);
	float coupe = fract(v + h12(vec2(rang, plage)) );  // long et court
	float relief = 0.5 + 0.5 * cos(6.2832 * u);
	float jour = smoothstep(0.0, 0.12, coupe) * smoothstep(1.0, 0.88, coupe);
	float fondu = smoothstep(1.8, 2.8, pas) * points;
	c *= 1.0 + fondu * (0.34 * (relief - 0.5) - 0.18 * (1.0 - jour));

	// 3. Le cerne et l'ombre : huit prises d'alpha autour du pixel.
	float r = clamp(taille / 44.0, 1.0, 2.2);
	vec2 o = px * r;
	float a8 = max(max(max(texture(TEXTURE, UV + vec2(o.x, 0.0)).a, texture(TEXTURE, UV - vec2(o.x, 0.0)).a),
		max(texture(TEXTURE, UV + vec2(0.0, o.y)).a, texture(TEXTURE, UV - vec2(0.0, o.y)).a)),
		max(max(texture(TEXTURE, UV + o * 0.7071).a, texture(TEXTURE, UV - o * 0.7071).a),
		max(texture(TEXTURE, UV + vec2(o.x, -o.y) * 0.7071).a, texture(TEXTURE, UV + vec2(-o.x, o.y) * 0.7071).a)));
	float sh = texture(TEXTURE, UV - o * vec2(1.1, 1.5)).a;
	float bord = clamp(a8 - t.a, 0.0, 1.0) * cerne;
	vec4 outc = vec4(c, t.a);
	// Le cerne sous la broderie, l'ombre sous le cerne.
	vec4 cerne_c = vec4(fil_brun.rgb, bord * 0.95);
	vec4 ombre_c = vec4(fil_brun.rgb * 0.6, sh * 0.32 * ombre);
	vec4 dessous = vec4(mix(ombre_c.rgb, cerne_c.rgb, cerne_c.a), cerne_c.a + ombre_c.a * (1.0 - cerne_c.a));
	vec4 res = vec4(mix(dessous.rgb, outc.rgb, outc.a), outc.a + dessous.a * (1.0 - outc.a));
	COLOR = vec4(res.rgb, res.a) * v_mod;
}
