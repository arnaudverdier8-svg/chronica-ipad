// ============================================================================
// stitch_nuages.gdshaderinc : les points communs des NUAGES CAPITONNÉS
// (cloud.gdshader, les bourrelets de la lisière ; fog.gdshader, la nappe). À
// inclure APRÈS stitch.gdshaderinc, dont il emploie le vocabulaire
// (StThread, st_*).
//
// Le nuage de la tapisserie (docs/CIBLE_TAPISSERIE.png) : une toile crème
// couverte de rangs fins de fil couché, horizontaux, ondulés et irréguliers,
// rembourrée (trapunto) : de gros cumulus cernés d'un fil brun fin dont le
// contour finit en volute (une crosse), sur de grandes plages lisses.
//
// COÛT : nu_rows = 0 hash, 5 sin + 1 cos ; nu_curl / nu_crook = 0 hash
// (1 atan, 1 length ; nu_crook : + 1 cos, 1 sin).
// ============================================================================

#ifndef CHRONICA_STITCH_NUAGES_GDSHADERINC
#define CHRONICA_STITCH_NUAGES_GDSHADERINC

// Les couleurs du nuage : des uniforms globaux posés par la préselection
// de couleurs (Vis.use_palette ; défauts de « tapisserie » dans
// project.godot, entre parenthèses).
// Le fil crème des rangs (0,870 ; 0,820 ; 0,715). Mesuré sur la cible :
// moyenne du nuage ≈ #C8B08D (TSL : saturation 0,34 à 0,37, luminosité
// 0,67), médiane #CFB48F ; la première passe sortait à S 0,48, L 0,71 (trop
// jaune, trop claire). Le fil est donc un crème grisé : la lumière du jour,
// chaude, le réchauffe.
global uniform vec3 g_nu_thread;
// La toile sous les rangs, qu'on voit dans les rainures (0,620 ; 0,535 ; 0,410).
global uniform vec3 g_nu_under;
// Le fil des piqûres et du contour : brun, entre ST_BRUN et ST_OCRE
// (0,380 ; 0,285 ; 0,170).
global uniform vec3 g_nu_cord;
// Le cordon rembourré des volutes et des bourrelets : le fil crème, un ton
// plus clair, il prend la lumière (0,920 ; 0,880 ; 0,800).
global uniform vec3 g_nu_curl;
#define NU_THREAD g_nu_thread
#define NU_UNDER g_nu_under
#define NU_CORD g_nu_cord
#define NU_CURL g_nu_curl
// La graine des rangs, commune à la nappe et aux bourrelets : leurs rangs
// tombent au même endroit du monde, la jointure ne se voit pas.
const float NU_SEED = 0.37;
// Demi-largeur du cordon des volutes et des contours de cumulus (monde).
const float NU_CORD_HW = 0.03;
// Le couvercle (fog_lid, cloud_lid) est levé d'autant au-dessus de ce qu'il
// redessine : moins que l'écart entre deux étages de bourrelets (0,003,
// view/quilt.gd), plus que la précision de profondeur au zoom le plus
// lointain (~0,0007).
const float NU_LID_LIFT = 0.002;

// Rangs de fil crème, horizontaux, ondulés et irréguliers : chaque rang est
// un cordon continu, rond, torsadé (le point de tige de la cible : de
// petites crêtes obliques le long du rang, décalées d'un rang à l'autre),
// séparé du suivant par une rainure fine où la toile se voit. L'ondulation
// varie d'un endroit à l'autre et le pas des rangs respire : rien de
// mécanique, pas de « carton ondulé ». Au loin, la torsade, puis le rond et
// la rainure s'effacent vers leurs moyennes (shade → 1, tilt → 0, cover →
// ~0,92 : règle de stitch.gdshaderinc). 0 hash (suite de Weyl par rang).
StThread nu_rows(vec2 xz, float seed, float px) {
	// Pas des rangs : mesuré sur la cible, ~1/22 de la largeur d'une case
	// (≈ 3 px sur la cible) ; ici 0,068, soit ≥ 4,5 px au zoom de partie :
	// le relief des rangs s'y voit encore en entier (en deçà, la règle
	// anti-moiré l'efface et la toile devient du papier).
	const float W = 0.068;
	// Deux ondes courtes (une demi-case, un tiers de case) qui ne battent pas
	// ensemble et glissent d'un rang à l'autre (leur phase dépend de z) : des
	// rangs « peignés », jamais deux pareils ; une houle lente module leur
	// amplitude (des plages calmes, d'autres plus frisées).
	float swell = 0.5 + 0.5 * sin(xz.x * 0.53 - xz.y * 0.91 + seed * 4.0);
	float wave = (0.006 + 0.016 * swell) * sin(xz.x * 11.3 + xz.y * 4.1 + seed * ST_TAU)
		+ (0.012 - 0.006 * swell) * sin(xz.x * 6.9 - xz.y * 5.3 + 1.7)
		+ 0.055 * sin(xz.y * 2.4 + xz.x * 0.31);
	vec2 uv = vec2(xz.x, xz.y + wave);
	float sv = uv.y / W;
	float j = floor(sv);
	float u = fract(sv) * 2.0 - 1.0;
	// Le rond et la rainure : un motif de période W (≈ 4,5 px au zoom de
	// partie), entier au-delà de 4,5 px, effacé sous 2 px.
	float f = st_fade(W, px);
	float tp = W * 1.5;                             // pas de la torsade
	float ft = st_fade(tp, px) * f;
	float ph = fract(j * 0.6180339 + seed * 3.0);   // propre au rang
	vec3 tw = st_twist(uv.x / tp + ph * 7.0, u, 0.55);
	StThread s;
	// La rainure : une ligne fine de toile entre deux rangs (demi-largeur
	// 0,07·W), à couverture filtrée exactement (elle pâlit au lieu de
	// crépiter) ; au loin, sa couverture moyenne.
	const float GW = 0.07 * W;
	float gr = st_band((1.0 - abs(u)) * 0.5 * W, GW, px);
	s.cover = mix(1.0 - 0.85 * 2.0 * GW / W, 1.0 - 0.85 * gr, f);
	s.tie = 0.0;
	s.u = u;
	s.tilt = vec2(tw.y * 0.16 * ft, st_round(u) * 0.27 * f + tw.z * 0.12 * ft);
	s.shade = 1.0 - 0.20 * (u * u - 0.3333) * f + (tw.x - 0.5) * 0.12 * ft
		+ (fract(j * 0.6180339 + seed * 7.0) - 0.5) * 0.08 * f;
	s.rnd = ph;
	return s;
}

// Une volute de trapunto : un cordon crème rembourré, posé le long d'une
// spirale d'Archimède centrée en 0 (pas `pitch`, de 0,2 à `turns` tours),
// de demi-largeur hw, tenu de part et d'autre par une piqûre brune fine.
// Rend cover (le cordon, filtré), tie (les deux piqûres brunes posées
// dessus, demi-largeur ≥ ~0,45 px), tilt.y = rond du cordon EN TRAVERS
// (direction radiale : q / |q|), shade, u. Tout s'efface quand le pas de la
// spirale tombe sous ~2 px. 0 hash. Le bras extérieur finit, à `turns` tours,
// dans la direction d'angle (fract(turns) - 0,5)·2π, au rayon pitch·turns.
StThread nu_curl(vec2 q, float pitch, float turns, float hw, float px) {
	StThread s;
	float rr = length(q);
	float a = atan(q.y, q.x) / ST_TAU + 0.5;
	float k = floor(rr / pitch - a + 0.5);
	float tt = a + k;
	float across = rr - pitch * tt;
	float on = smoothstep(0.1, 0.25, tt) * step(tt, turns);
	float vis = st_fade(pitch, px);
	s.cover = st_band(across, hw, px) * on * vis;
	float lw = max(0.005, 0.45 * px);
	s.tie = st_band(abs(across) - hw, lw, px) * on * vis;
	s.u = clamp(across / max(hw, 1e-6), -1.0, 1.0);
	float vr = st_fade(hw * 2.0, px);
	s.tilt = vec2(0.0, st_round(s.u) * 0.55 * vr);
	s.shade = 1.0 + 0.16 * (0.3333 - s.u * s.u) * vr;
	s.rnd = 0.0;
	return s;
}

// Une CROSSE : la volute qui termine un contour de cumulus. Le contour est
// un cercle de centre 0 et de rayon R (son cordon a son axe à R - NU_CORD_HW) ;
// la volute (`turns` tours, rayon extérieur rho) est posée dedans, tangente
// intérieurement dans la direction u (unitaire) : son bras extérieur prolonge
// le cordon du cercle et s'enroule vers le dedans. mir = 1 inverse le sens
// d'enroulement (miroir autour de l'axe u). p : position relative au centre
// du cercle. Sans miroir, le cordon arrive sur la crosse en tournant dans le
// sens ANTIHORAIRE à l'écran (x à droite, z vers le bas) ; avec, dans le sens
// horaire. Mêmes sorties que
// nu_curl (tilt.y : en travers, direction radiale depuis le centre de la
// crosse, voir nu_crook_normal).
StThread nu_crook(vec2 p, vec2 u, float R, float rho, float turns, float mir, float px) {
	vec2 q = p - u * (R - NU_CORD_HW - rho);
	q = mix(q, 2.0 * dot(q, u) * u - q, mir);
	float a_end = (fract(turns) - 0.5) * ST_TAU;
	vec2 e = vec2(cos(a_end), sin(a_end));
	float c = dot(u, e);
	float s = u.x * e.y - u.y * e.x;
	vec2 ql = vec2(c * q.x - s * q.y, s * q.x + c * q.y);
	return nu_curl(ql, rho / turns, turns, NU_CORD_HW, px);
}

// La normale bombée du cordon d'une crosse (mêmes p, u, R, rho que nu_crook).
vec3 nu_crook_normal(vec3 n, vec2 p, vec2 u, float R, float rho, StThread cu) {
	vec2 q = p - u * (R - NU_CORD_HW - rho);
	vec2 rd = q / max(length(q), 1e-4);
	return st_bend(n, vec3(-rd.y, 0.0, rd.x), vec3(rd.x, 0.0, rd.y), cu.tilt);
}

// ---------------------------------------------------------------------------
// LA NAPPE (fog.gdshader, fog_lid.gdshader)
// ---------------------------------------------------------------------------
// Sur la cible, l'intérieur d'un nuage est une toile REMBOURRÉE : de larges
// coussins bombés, séparés par des creux doux, et çà et là un CUMULUS cousu
// (le haut d'un coussin festonné de bosses, cerné d'un fil brun et d'un
// cordon crème, qui finit en crosse). Ici :
//   - les COUSSINS : un disque de 1,2 à 1,6 de rayon par maille de NU_PAD
//     (centre jitté de ±0,15 maille), dans un espace lentement gauchi (tailles
//     inégales, alignements brisés). Un coussin plus au sud (plus bas à
//     l'écran) passe le plus souvent devant : on voit surtout leur HAUT.
//     Chacun est un dôme (la normale roule vers son bord : le côté au soleil,
//     en haut à gauche, s'éclaire ; l'autre s'ombre) ; au pied d'un coussin
//     posé devant, la toile de derrière plonge (un creux doux, sans fil) ;
//   - les CUMULUS : sur un coussin sur deux à peu près (une houle lente en
//     règle la densité : des amas, et des plages calmes), le haut du contour
//     est cousu sur un arc de 85° à 185°, festonné de 1 à 4 bosses ; de
//     dehors vers dedans : un creux ombré, le fil brun, le cordon crème rond
//     et clair, puis la bosse bombée. L'arc finit en CROSSE à un bout, aux
//     deux ou à aucun (le cordon s'amincit alors).
// Près de la lisière (inner → 0), tout s'efface vers les rangs nus : la nappe
// y rejoint les bourrelets de la lisière (cloud.gdshader) sans couture.
//
// PORTÉE : un coussin ne porte pas au-delà de 0,76 (rayon) + 0,15 (jitter)
// + 0,08 (creux) = 0,99 maille de son centre nominal, et le point est à plus
// de 1 maille du centre nominal de toute maille hors de son bloc 2 × 2 :
// seules ces quatre comptent (pas de coupure droite).
//
// COÛT : 4 hash (une boucle de 4, puis une de 4 sans hash ni trigonométrie) ;
// 4 sin (gauchissement), rangs 5 sin + 1 cos, arc 1 atan + 1 cos, crosse
// 1 atan + 1 sin + 1 cos ; aucune texture.

// Maille des coussins (monde ; une case a un rayon de 1).
const float NU_PAD = 2.05;

// L'axe d'un arc cousu (son milieu), tiré de a (0..1) : un vecteur unitaire
// tourné de ±0,7 rad autour du haut de l'écran (le nord, -z). Sans
// trigonométrie.
vec2 nu_axis(float a) {
	return normalize(vec2((a - 0.5) * 1.7, -1.0));
}

// Cosinus approché (|x| ≤ 2 : erreur < 0,03), sans trigonométrie.
float nu_cos(float x) {
	float x2 = x * x;
	return 1.0 - 0.5 * x2 * (1.0 - x2 * (1.0 / 12.0));
}

// La part d'un contour cousu (en fonction du cosinus c de l'angle à l'axe de
// l'arc) : la même pour le coussin visible et pour ceux posés devant. Elle
// s'éteint avant le bout de l'arc, là où le cordon s'amincit.
float nu_arc_part(float c, float hspan) {
	return smoothstep(nu_cos(hspan - 0.05), nu_cos(hspan - 0.45), c);
}

// Un coussin porte-t-il un arc cousu ? 1 ou 0, d'après son hasard h et une
// houle lente sur les mailles (des amas de cumulus, et de grandes plages
// calmes). La houle est quasi périodique (deux ondes triangulaires de 7,3 et
// 8,8 mailles, sans commune mesure ; pas de trigonométrie : elle sert dans la
// boucle) : au zoom le plus lointain, on ne la voit pas se répéter. Une
// volute seule (un cumulus sur cinq) ne compte pas : elle n'a pas d'arc.
float nu_sewn(vec2 h, vec2 cell) {
	float swell = abs(fract(cell.x * 0.137 + cell.y * 0.071) - 0.5) + abs(fract(cell.y * 0.113 - cell.x * 0.059 + 0.3) - 0.5);
	float chance = mix(0.3, 0.8, smoothstep(0.25, 0.75, swell));
	return step(fract(h.x * 3.71 + h.y * 1.37), chance);
}

// Les deux tirages d'un cumulus (orientation, ouverture ; bosses, crosses),
// et s'il n'est qu'une volute seule.
vec2 nu_ga(vec2 h) {
	return fract(h * vec2(17.3, 23.9) + 0.13);
}
vec2 nu_g2(vec2 h) {
	return fract(h * vec2(41.7, 11.3) + 0.57);
}
float nu_lone(vec2 ga, vec2 g2) {
	return step(fract(g2.x * 5.7 + ga.x * 2.3), 0.2);
}

void nu_nappe(vec2 xz, float v_in, float px, out vec3 col, out vec3 n) {
	const vec3 UP = vec3(0.0, 1.0, 0.0);
	const vec3 AX = vec3(1.0, 0.0, 0.0);
	const vec3 AZ = vec3(0.0, 0.0, 1.0);
	// Les motifs s'effacent vers la lisière.
	float inner = smoothstep(0.15, 0.75, v_in);

	// --- Le gauchissement lent : des coussins de tailles inégales. -----------
	// Deux échelles : une houle lente (des régions de grands et de petits
	// coussins) et une onde à l'échelle d'un coussin (chacun devient une
	// patate, plus un disque : pas d'écailles alignées).
	vec2 wv = vec2(sin(xz.y * 0.43 + 0.7), sin(xz.x * 0.37 + 1.9));
	vec2 q = xz + vec2(0.50 * wv.x + 0.26 * sin(xz.x * 0.97 + xz.y * 0.61 + 2.3),
		0.40 * wv.y + 0.24 * sin(xz.y * 1.07 - xz.x * 0.53 + 0.4));
	vec2 g = q / NU_PAD;
	vec2 base = floor(g - 0.5);

	// --- Le coussin de devant (en mailles). ----------------------------------
	vec2 cs[4];
	float rs[4];
	float zs[4];
	vec2 hs[4];
	vec2 cells[4];
	float best = -1e6;
	int w = -1;
	for (int i = 0; i < 4; i++) {
		vec2 cell = base + vec2(mod(float(i), 2.0), floor(float(i) * 0.5));
		vec2 h = st_hash22(cell + 17.0);
		vec2 j = fract(h * vec2(7.13, 5.71) + vec2(0.31, 0.77)) - 0.5;
		cs[i] = cell + 0.5 + 0.30 * j;
		rs[i] = mix(0.58, 0.76, fract(h.y * 5.3 + h.x));
		// (un coussin cousu passe devant un coussin nu : un coussin nu, sans
		// relief ni fil, ne coupe jamais un cumulus)
		zs[i] = cs[i].y + 0.7 * fract(h.x * 13.7 + h.y * 3.1) + 10.0 * nu_sewn(h, cell);
		hs[i] = h;
		cells[i] = cell;
		if (zs[i] > best && length(g - cs[i]) < rs[i]) {
			best = zs[i];
			w = i;
		}
	}
	// Le creux au pied d'un coussin posé DEVANT (e : monde, > 0 dehors) : doux
	// partout, plus marqué sous un arc cousu.
	float crease = 0.0;
	vec2 slope = vec2(0.0);
	for (int i = 0; i < 4; i++) {
		vec2 pr = g - cs[i];
		float di = length(pr);
		float e = (di - rs[i]) * NU_PAD;
		float front = step(best + 1e-3, zs[i]) * step(0.0, e);
		float soft = 1.0 - smoothstep(0.0, 0.13, e);
		// (seulement au-dessus d'un arc cousu : la bosse surplombe le creux ;
		// ailleurs la toile est lisse)
		vec2 gi = nu_ga(hs[i]);
		float sw = zs[i] > 9.0 ? (1.0 - nu_lone(gi, nu_g2(hs[i])))
			* nu_arc_part(dot(pr / max(di, 1e-4), nu_axis(gi.x)), mix(0.75, 1.6, gi.y)) : 0.0;
		float k = front * soft * soft * sw;
		crease = max(crease, k);
		// La toile de derrière remonte du creux : sa normale penche vers le
		// coussin de devant, à plat au fond du creux (un U, pas une marche).
		slope -= pr / max(di, 1e-4) * k * smoothstep(0.0, 0.07, e);
	}
	float on = w >= 0 ? 1.0 : 0.0;
	int wi = max(w, 0);
	vec2 wh = hs[wi];
	vec2 pl = (g - cs[wi]) * NU_PAD;             // monde, depuis le centre
	float R = rs[wi] * NU_PAD;
	float d = length(pl);
	vec2 od = pl / max(d, 1e-4);
	float t = clamp(d / R, 0.0, 1.0);
	float m = on * inner;

	// --- L'arc cousu du coussin visible : tourné de ±0,7 rad autour du haut,
	// d'une demi-ouverture de 0,75 à 1,6 rad, festonné de 1 à 4 bosses (creux
	// pointés vers le dedans). Ses bouts tombent sur le haut d'une bosse : une
	// crosse y prend le relais (gauche, droite, les deux), ou le cordon
	// s'amincit. Un cumulus sur cinq n'est qu'une volute seule. --------------
	vec2 ga = nu_ga(wh);
	vec2 g2 = nu_g2(wh);
	float sewn = nu_sewn(wh, cells[wi]) * m;
	// Une volute seule (un cumulus sur cinq) : pas d'arc, la crosse d'un bout.
	float lone = nu_lone(ga, g2);
	vec2 ax = nu_axis(ga.x);
	vec2 axp = vec2(-ax.y, ax.x);
	float hspan = mix(0.75, 1.6, ga.y);
	float cphi = dot(od, ax);
	float phi = atan(dot(od, axp), cphi);
	float bumps = floor(mix(1.0, 4.99, fract(g2.x * 3.3 + ga.y)));
	float bw = 2.0 * hspan / bumps;
	float dip = R * mix(0.07, 0.13, fract(g2.y * 4.1));
	float cw = 2.0 * NU_CORD_HW;                     // le cordon crème
	float lw = max(0.009, 0.75 * px);               // demi-largeur du fil brun
	// Le bord cousu : dt = rayon de l'axe du cordon, festonné.
	float sc = 1.0 - abs(cos(ST_PI * (phi + hspan) / bw));
	float dt = R - 2.0 * lw - 0.5 * cw - dip * sc;
	float cl = max(step(0.3, g2.x), lone);           // crosse à gauche
	float cr = step(g2.x, 0.72) * (1.0 - lone);      // crosse à droite
	float tl = mix(smoothstep(-hspan, -hspan + 0.35, phi), step(-hspan, phi), cl);
	float tr = mix(1.0 - smoothstep(hspan - 0.35, hspan, phi), step(phi, hspan), cr);
	float arc = tl * tr * sewn * (1.0 - lone);
	float across = d - dt;                           // > 0 dehors (monde)
	float hwe = 0.5 * cw * mix(0.35, 1.0, tl * tr);

	// --- La toile : rangs de fil couché crème. -------------------------------
	StThread s = nu_rows(xz, NU_SEED, px);
	col = st_paint(st_albedo(NU_UNDER), st_albedo(NU_THREAD), s);
	n = st_bend(UP, AX, AZ, s.tilt * s.cover);

	// --- Le coussin : un dôme doux ; sous l'arc cousu, la bosse roule vers son
	// cordon. Le cœur est un ton plus clair, le fond un ton plus bas. ---------
	float fpad = st_fade(0.08, px);
	// (le roulé retombe à plat au fond du creux, sur les 0,1 du bord : U)
	float roll = smoothstep(0.4, 0.9, t) * (1.0 - smoothstep(R - 0.1, R, d));
	float sarc = nu_arc_part(cphi, hspan) * sewn * (1.0 - lone);
	float bump = smoothstep(dt - 0.45, dt - hwe, d) * step(d, dt + hwe) * sarc;
	// Le relief se tient autour des cumulus : sous l'arc, la bosse ; au-dessus,
	// le creux. Ailleurs la toile n'a que sa houle lente (les grandes ondes du
	// gauchissement, à peine : le nuage respire sans faire de galets).
	n = st_bend(n, AX, AZ, (od * (0.38 * roll * roll * sarc + 0.5 * bump) + slope * 0.38 * inner + wv * 0.10) * fpad);
	col *= 1.0 + (0.05 * (1.0 - t * t) - 0.02) * sarc + 0.05 * bump - 0.10 * bump * bump * bump;
	// Dans les creux du feston (entre le bord cousu et le disque), et au pied
	// d'un coussin de devant : la toile plonge.
	float outer = smoothstep(dt + hwe, dt + hwe + 0.05, d) * sarc;
	crease = max(crease, outer);
	// … et le coussin visible plonge lui aussi au fond du creux, sur son bord
	// (sinon l'ombre du creux s'arrête net sur le cercle).
	float own = 1.0 - smoothstep(0.0, 0.12, R - d);
	crease = max(crease, own * own * sarc);
	col *= 1.0 - 0.28 * crease * inner * fpad;

	// --- Les cordons : l'arc (cordon crème rond, deux piqûres brunes), puis la
	// crosse. ----------------------------------------------------------------
	float fcord = st_fade(cw, px);
	StThread ar;
	ar.cover = st_band(across, hwe, px) * arc;
	// (au loin, seule la piqûre du dehors reste : un cordon et son fil, pas un
	// double trait)
	ar.tie = st_band(abs(across) - hwe - lw, lw, px) * arc * mix(st_fade(0.05, px), 1.0, step(0.0, across));
	ar.u = clamp(across / hwe, -1.0, 1.0);
	ar.tilt = vec2(0.0, st_round(ar.u) * 0.6 * fcord);
	ar.shade = 1.0 + 0.18 * (0.3333 - ar.u * ar.u) * fcord;
	ar.rnd = 0.0;
	col = st_paint(col, st_albedo(NU_CURL), ar);
	col = st_paint_tie(col, st_albedo(NU_CORD), ar);
	n = normalize(mix(n, st_bend(n, vec3(-od.y, 0.0, od.x), vec3(od.x, 0.0, od.y), ar.tilt), ar.cover));

	// La crosse du bout le plus proche (une seule évaluée).
	float right = step(0.0, phi);
	vec2 ue = ax * cos(hspan) + axp * (sin(hspan) * mix(-1.0, 1.0, right));
	float rho = R * mix(0.2, 0.3, g2.y);
	float turns = mix(1.5, 2.3, fract(g2.y * 7.1));
	float Rc = R - 2.0 * lw - 0.5 * cw + NU_CORD_HW;
	StThread cu = nu_crook(pl, ue, Rc, rho, turns, right, px);
	float cm = mix(cl, cr, right) * sewn;
	cu.cover *= cm;
	cu.tie *= cm;
	col = st_paint(col, st_albedo(NU_CURL), cu);
	col = st_paint_tie(col, st_albedo(NU_CORD), cu);
	n = normalize(mix(n, nu_crook_normal(n, pl, ue, Rc, rho, cu), cu.cover));
}

// ---------------------------------------------------------------------------
// LES BOURRELETS DE LA LISIÈRE (cloud.gdshader, cloud_lid.gdshader)
// ---------------------------------------------------------------------------
// Un feston : un disque plat posé juste SOUS la nappe, dont seul le croissant
// qui déborde se voit (disposition : view/quilt.gd). xz : le point (monde) ;
// c, rad : centre et rayon du disque ; k : INSTANCE_CUSTOM ; l2 : le second
// bord de la nappe (couleur d'instance) ; ns : les normales des deux bords
// (cos, sin ; calculées par sommet) ; px, fr = fwidth(|xz - c| / rad) : les
// dérivées, prises par l'appelant hors de toute branche. Rend l'albédo
// (avant saison et nuit) et la normale (monde).
void nu_bourrelet(vec2 xz, vec2 c, float rad, vec4 k, vec2 l2, vec4 nsv, float px, float fr, out vec3 col, out vec3 n) {
	vec2 p = xz - c;
	float d = length(p);
	float r = d / rad;                       // > 1 : la lunule hors du cercle
	const vec3 UP = vec3(0.0, 1.0, 0.0);
	const vec3 AX = vec3(1.0, 0.0, 0.0);
	const vec3 AZ = vec3(0.0, 0.0, 1.0);
	vec2 od = p / max(d, 1e-4);
	vec3 T = vec3(-od.y, 0.0, od.x);
	vec3 B = vec3(od.x, 0.0, od.y);

	// --- La toile : les rangs de la nappe, à l'identique. --------------------
	StThread s = nu_rows(xz, NU_SEED, px);
	col = st_paint(st_albedo(NU_UNDER), st_albedo(NU_THREAD), s);
	n = st_bend(UP, AX, AZ, s.tilt * s.cover);

	// --- Le bord de la nappe au-dessus : e > 0 dehors (visible). À un cap du
	// nuage, la nappe est le coin de deux bords : dehors = dehors de l'un ou
	// de l'autre. -------------------------------------------------------------
	vec2 ns = nsv.xy;
	float e = max(dot(p, ns) - (k.w * 2.0 - 1.0) * rad,
			dot(p, nsv.zw) - (l2.y * 2.0 - 1.0) * rad);
	float fz = smoothstep(0.0, 0.09, e);
	// Le fil brun du contour s'efface plus tôt : là où un feston croise son
	// voisin, il n'entre que d'un pas dans la toile (sur la silhouette même,
	// e ≥ 0,15 : vérifié par échantillonnage, 99,7 % des points).
	float fl = smoothstep(0.04, 0.15, e);

	// --- Le rembourrage : le bord roule vers la couture (le côté au soleil
	// s'éclaire, l'autre s'ombre), la toile s'y bombe puis plonge. Le dessus
	// reste plat (r < 0,7) : c'est là que passe le bord de la nappe. --------
	float edge = smoothstep(0.7, 1.0, r);
	float fpad = st_fade(0.05, px);
	edge *= fz;
	n = st_bend(n, AX, AZ, od * 0.75 * edge * edge * fpad);
	col *= 1.0 + 0.04 * edge - 0.10 * edge * edge * edge;

	// --- La volute : une crosse au bout du feston, vers son voisin, tangente
	// au bord (le contour du feston s'y enroule au lieu de finir en pointe).
	// k.y : 0 = pas de volute, 1 = volute, 0,7 = volute en miroir. --------
	float mir = step(k.y, 0.85);
	vec2 kdir = normalize(vec2(-ns.y, ns.x) * mix(-0.6, 0.6, mir) + ns * 0.8);
	float cr = rad * mix(0.26, 0.36, fract(k.x * 5.3));
	float turns = mix(1.4, 2.0, fract(k.x * 9.7));
	StThread cu = nu_crook(p, kdir, rad, cr, turns, mir, px);
	float cm = step(0.5, k.y) * fz;
	cu.cover *= cm;
	cu.tie *= cm;
	col = st_paint(col, st_albedo(NU_CURL), cu);
	col = st_paint_tie(col, st_albedo(NU_CORD), cu);
	n = normalize(mix(n, nu_crook_normal(n, p, kdir, rad, cr, cu), cu.cover));

	// --- Le bord : piqûre fine, bourrelet crème rond, fil brun. Le
	// bourrelet est large (≥ 3 px) et clair : c'est lui qui fait le
	// capitonnage de la lisière ; un creux ombré le sépare de la toile. ------
	float W = max(1.6, 0.024 / px);                  // le contour, en px
	float dpx = (1.0 - r) / fr;                       // distance au bord, en px
	float line = (1.0 - smoothstep(W - 0.6, W + 0.6, dpx)) * fl;
	// Le bourrelet : un cordon crème épais et clair (≥ 4 px ; 0,085 monde, le
	// cordon de lisière de la cible), rond, qui prend la lumière.
	float RW = max(4.0, 0.085 / px);                 // le bourrelet, en px
	float ru = clamp((dpx - W - 0.5 * RW) / (0.5 * RW), -1.0, 1.0);
	// Le bourrelet est une bande isolée (≥ 4 px) : il reste entier au zoom de
	// partie, et ne fond qu'au loin (sinon les festons y deviennent des perles).
	float vrim = st_fade(0.12, px);
	float rim = (1.0 - line) * (1.0 - smoothstep(W + RW - 0.6, W + RW + 0.6, dpx)) * vrim * fz;
	col = mix(col, st_albedo(NU_CURL) * (1.0 + 0.16 * (0.3333 - ru * ru)), rim);
	// Le creux au pied du bourrelet (la piqûre, cachée dessous, tire la toile).
	float groove = (1.0 - smoothstep(0.0, 0.6 * RW, abs(dpx - W - RW - 0.3 * RW))) * (1.0 - rim);
	col *= 1.0 - 0.13 * groove * vrim * fz;
	col = mix(col, st_albedo(NU_CORD), line);
	n = normalize(mix(n, st_bend(n, T, B, vec2(0.0, -st_round(ru) * 0.6)), rim));
}

// L'hiver, la toile crème se refroidit (crème grisé, jamais blanc pur) :
// elle ne vire pas à l'orange contre la neige.
vec3 nu_season(vec3 col, float snow) {
	return mix(col, vec3(st_luma(col)) * vec3(1.03, 1.0, 0.95), 0.55 * snow);
}

// La nuit, la toile crème BLEUIT (docs/DIRECTION_TAPISSERIE.md : « la nuit
// assombrit et bleuit la toile, sans la noyer ») : c'est la lune, très bleue
// (Vis.PHASE_LIGHT « night »), qui la bleuit. Mesuré sous elle : le crème tel
// quel sort pervenche (#687CAF, saturation 0,40, plus bleu que la terre) ;
// réchauffé de (1,10 ; 1 ; 0,80), gris neutre (#7F808A) ; réchauffé de
// (1,05 ; 1 ; 0,90), gris bleuté (#798097, saturation 0,20) : le juste
// milieu, gardé ici. Seulement en pleine nuit : au crépuscule (night =
// 0,25), la lumière est chaude, rien à compenser. À reprendre si la lumière
// de nuit change.
vec3 nu_night(vec3 col, float night) {
	return col * mix(vec3(1.0), vec3(1.05, 1.0, 0.90), smoothstep(0.4, 1.0, night));
}

// … et garde une faible lueur bleu pâle (un nuage reste un nuage, on le lit
// encore). EMISSION s'affiche telle quelle en Compatibility : st_albedo.
vec3 nu_night_glow(vec3 col, float night) {
	return st_albedo(vec3(0.05, 0.058, 0.075)) * st_luma(col) * smoothstep(0.4, 1.0, night);
}

#endif
