// Les NUAGES D'ASTRA (pack « la table de guerre », assets/ui/table/clouds/) :
// la nappe et les bouffées du brouillard sont peintes, matelassées et
// surpiquées, au lieu d'être cousues par le shader (stitch_nuages, gardé pour
// la saison et la nuit). Partagé par fog / fog_lid (la nappe) et cloud /
// cloud_lid (les bouffées). Les textures sont posées par view/board.gd.
//
// COÛT par pixel : un échantillon de texture ; aucun hash, aucune boucle.

uniform sampler2D nu_fill : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D nu_puffs : source_color, filter_linear_mipmap;

// Le pas du motif de la nappe, en unités monde (une case a un rayon de 1) :
// un lobe matelassé fait plus d'une case (un motif large et calme, pas une
// texture serrée).
const float NA_FILL_TILE = 11.0;
// La bouffée déborde le disque de la disposition (view/quilt.gd PUFF_GROW) :
// l'image n'occupe pas tout son carré, et ses bosses doivent couvrir le bord
// droit de la nappe.
const float NA_PUFF_GROW = 1.65;

vec3 na_fill(vec2 xz) {
	return texture(nu_fill, xz / NA_FILL_TILE).rgb;
}

// La bouffée d'une instance : l'une des huit de l'atlas (4 × 2), choisie et
// retournée (miroir) par sa graine. Le haut de l'image est au loin (-Z) :
// la bouffée se tient droite à l'écran (caméra verrouillée).
vec4 na_puff(vec2 xz, vec2 c, float r, float seed) {
	vec2 uv = (xz - c) / (2.0 * r * NA_PUFF_GROW) + 0.5;
	if (fract(seed * 7.31) > 0.5) {
		uv.x = 1.0 - uv.x;
	}
	float idx = clamp(floor(seed * 8.0), 0.0, 7.0);
	vec2 cell = vec2(mod(idx, 4.0), floor(idx / 4.0));
	return texture(nu_puffs, (cell + clamp(uv, 0.0, 1.0)) / vec2(4.0, 2.0));
}
