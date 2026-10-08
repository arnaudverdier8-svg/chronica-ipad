"""Tag PNGs as sRGB without touching a single pixel: insert an `sRGB` chunk (rendering intent 0, perceptual)
right after IHDR, byte-copying every other chunk (IDAT is not recompressed). Untagged files are what Godot,
Playwright and Pillow produced; they are sRGB-encoded (Godot Compatibility blends 2D in sRGB space), and
Blender / After Effects / Nuke must not re-interpret them when the mattes are relit.

usage: python3 png_srgb.py FILE_OR_DIR [...]      (directories: every *.png, recursively)
"""
import sys, os, struct, zlib

SIG = b'\x89PNG\r\n\x1a\n'


def tag(path):
    """Returns True if the file was rewritten, False if already tagged (sRGB, iCCP, gAMA or cHRM present)."""
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:8] == SIG, path
    pos, chunks, have = 8, [], set()
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunks.append((typ, data[pos:pos + 12 + n]))
        have.add(typ)
        pos += 12 + n
    if have & {b'sRGB', b'iCCP', b'gAMA', b'cHRM'}:
        return False
    body = b'\x00'
    chunk = struct.pack('>I', len(body)) + b'sRGB' + body + struct.pack('>I', zlib.crc32(b'sRGB' + body) & 0xffffffff)
    out = bytearray(SIG)
    for typ, raw in chunks:
        out += raw
        if typ == b'IHDR':
            out += chunk
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(out)
    os.replace(tmp, path)
    return True


def untag(path):
    """Inverse of tag(): drop an sRGB chunk (restores the original bytes of a file tag() rewrote)."""
    with open(path, 'rb') as f:
        data = f.read()
    pos, out, hit = 8, bytearray(SIG), False
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        if typ == b'sRGB':
            hit = True
        else:
            out += data[pos:pos + 12 + n]
        pos += 12 + n
    if hit:
        with open(path + '.tmp', 'wb') as f:
            f.write(out)
        os.replace(path + '.tmp', path)
    return hit


def tag_all(*targets):
    n = 0
    for t in targets:
        if os.path.isdir(t):
            for r, _, fs in os.walk(t):
                for fn in fs:
                    if fn.lower().endswith('.png'):
                        n += tag(os.path.join(r, fn))
        elif t.lower().endswith('.png'):
            n += tag(t)
    return n


if __name__ == '__main__':
    print('tagged', tag_all(*sys.argv[1:]), 'files')
