"""Encode guard (review item P3): is the blank parchment field, which is extremely low-frequency, at risk of banding in
an 8-bit delivery? Encodes the 16:9 keyframe as a 1.5 s still hold with three settings, decodes the last frame back to
full-range RGB with the same BT.709 matrix and compares the field (eroded 40 px) with the source PNG:

   mean / max abs error (luma), distinct luma levels spanned, the largest step between neighbouring 24 px block means
   (a banding indicator), and the 2 px high-pass energy (texture kept vs flattened).

One still, three encoder settings: evidence for the recommendation, not a guarantee for the final encode. G12 must
still be run on the shipped file.

usage: python3 encode_guard_test.py HANDOFF_DIR
"""
import sys, os, json, subprocess, tempfile, shutil
import numpy as np
from PIL import Image
from scipy import ndimage

SETTINGS = {
    'x264_8bit_crf18_default': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high'],
    'x264_8bit_crf18_grain_aq3': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-tune', 'grain', '-x264-params', 'aq-mode=3:aq-strength=1.3',
                                  '-pix_fmt', 'yuv420p', '-profile:v', 'high'],
    'x265_10bit_crf18': ['-c:v', 'libx265', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p10le', '-tag:v', 'hvc1',
                         '-x265-params', 'log-level=error:pools=2:frame-threads=2'],
}
TAGS = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']


def metrics(img, ref, field):
    lum = img.astype(np.float64).mean(2)
    rl = ref.astype(np.float64).mean(2)
    d = np.abs(img.astype(np.float64) - ref.astype(np.float64)).max(2)
    h, w = lum.shape
    bs = 24
    bm = lum[:h // bs * bs, :w // bs * bs].reshape(h // bs, bs, w // bs, bs).mean((1, 3))
    fm = field[:h // bs * bs, :w // bs * bs].reshape(h // bs, bs, w // bs, bs).all((1, 3))
    step = np.maximum(np.abs(np.diff(bm, axis=0))[:, :-1], np.abs(np.diff(bm, axis=1))[:-1, :])
    sel = (fm[:-1, :-1] & fm[1:, 1:])
    hp = lum - ndimage.gaussian_filter(lum, 2.0)
    return dict(mean_abs_err_255=round(float(d[field].mean()), 3), max_abs_err_255=int(d[field].max()),
                luma_levels_spanned=int(len(np.unique(np.round(lum[field])))),
                max_block_step_255=round(float(step[sel].max()), 3), highpass_std_sigma2=round(float(hp[field].std()), 3))


def main(hd):
    tag = '16x9_2560x1440'
    src = os.path.join(hd, f'f1983_{tag}.png')
    ref = np.asarray(Image.open(src).convert('RGB'))
    mask = np.asarray(Image.open(os.path.join(hd, f'mattes_{tag}', 'menu_card_parchment_field.png')).convert('RGBA'))[..., 3] > 0
    field = ndimage.binary_erosion(mask, iterations=40)
    tmp = tempfile.mkdtemp(prefix='encguard_', dir=os.path.join(hd, 'work'))
    out = {'source_png': metrics(ref, ref, field)}
    vf = 'scale=out_color_matrix=bt709:out_range=tv,format=%s'
    try:
        for name, args in SETTINGS.items():
            mp4 = os.path.join(tmp, name + '.mp4')
            pf = 'yuv420p10le' if '10bit' in name else 'yuv420p'
            cmd = ['nice', '-n', '5', 'ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', '30', '-i', src, '-frames:v', '45', '-vf', vf % pf,
                   '-threads', '2'] + args + TAGS + [mp4]
            subprocess.run(cmd, check=True)
            dec = os.path.join(tmp, name + '.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp4, '-vf', 'select=eq(n\\,44),scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24',
                            '-frames:v', '1', dec], check=True)
            m = metrics(np.asarray(Image.open(dec).convert('RGB')), ref, field)
            m['file_kb'] = round(os.path.getsize(mp4) / 1024, 1)
            out[name] = m
            print(name, m)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out['note'] = ('16:9 keyframe, 45 frames at 30 fps, field eroded 40 px. luma_levels_spanned is the count of distinct rounded luma values in the field; '
                   'BT.709 tv-range 8-bit squeezes the 25-level span further. One still and three encoder settings: evidence, not a guarantee.')
    json.dump(out, open(os.path.join(hd, 'qa', 'encode_guard_test.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    main(sys.argv[1])
