shader_type spatial;
// L'ombre de pied d'une figurine : à la place de l'ancien socle, une ombre
// douce et courte posée sur la toile, un rien décalée vers le sud-est (la
// lumière vient du haut-gauche). Elle ancre la figurine et la détache du
// fond, sans faire « jeton ». Un quad couché (UV 0..1), aucun motif fin :
// rien à effacer de loin. Portable (gl_compatibility) : 0 hash, 0 texture.

render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

#include "res://view/shaders/stitch.gdshaderinc"

global uniform float g_night;
global uniform float g_units_hide;

// Opacité au cœur de l'ombre.
uniform float strength = 0.42;
// L'AURA d'une figurine en carte (UnitPiece._build_aura) : en plus de
// l'ombre, un anneau au point avant (des points courts sur l'ellipse) à la
// couleur du peuple `team` (sRGB), sur un voile léger du même ton.
uniform bool ring = false;
uniform vec3 team = vec3(0.6, 0.23, 0.14);

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	// Un cœur plus dense sous les pieds, un bord fondu.
	float a = (1.0 - smoothstep(0.45, 0.95, r)) * strength;
	a *= 1.0 - 0.35 * g_night;
	vec3 col = st_albedo(ST_BRUN) * 0.6;
	if (ring) {
		float px = max(fwidth(r), 1e-4);
		// l'anneau : un fil épais (au moins 1,5 px) au bord de l'ellipse
		float hw = max(0.1, 0.9 * px);
		float band = st_band(r - 0.86, hw, px);
		// le point avant : 28 points autour, assez longs pour rester un trait
		float ang = atan(p.y, p.x) / (2.0 * ST_PI) * 28.0;
		float dash = mix(0.8, smoothstep(0.08, 0.2, abs(fract(ang) - 0.5) * 2.0 - 0.0) * 0.35 + 0.65, 1.0 - smoothstep(0.02, 0.05, px));
		vec3 tc = st_albedo(team);
		// le voile du peuple dans l'anneau, l'ombre au cœur par-dessus
		float veil = (1.0 - smoothstep(0.72, 0.86, r)) * 0.3;
		col = mix(tc, col, a / max(a + veil, 1e-4));
		a = max(a, veil);
		col = mix(col, mix(tc * 1.15, vec3(1.0), 0.12), band * dash);
		a = max(a, band * dash * 0.95);
		// unités cachées : l'ombre et le voile s'en vont, l'anneau reste
		if (g_units_hide > 0.5) {
			a = band * dash * 0.95;
		}
	}
	ALBEDO = col;
	ALPHA = a;
}
