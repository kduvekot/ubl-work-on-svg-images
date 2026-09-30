"""The pictures of the deck, as it stores them: <WORK>/pictures/picNN.<wmf|png>,
numbered in the order of its Pictures stream (the BStore's order, so the
deck's picture number k is picNN with NN = k - 1).

    python3 extract.py
"""
import struct, zlib
import olefile
from paths import PPT, work

o = olefile.OleFileIO(PPT)
p = o.openstream('Pictures').read()
off, i = 0, 0
while off + 8 <= len(p):
    vi, t, l = struct.unpack_from('<HHI', p, off)
    body = p[off + 8:off + 8 + l]
    inst = vi >> 4
    ext = {0xF01A: 'emf', 0xF01B: 'wmf', 0xF01C: 'pict', 0xF01D: 'jpg', 0xF01E: 'png', 0xF01F: 'dib'}.get(t, 'bin')
    if ext in ('emf', 'wmf', 'pict'):
        # the metafile's uid (two, for some instances), its 34-byte header, its data (deflated or not)
        hdr = 16 + (16 if inst in (0x3D5, 0x217, 0x543) else 0)
        data = body[hdr + 34:]
        if body[hdr + 32] == 0:
            data = zlib.decompress(data)
    else:
        hdr = 17 + (16 if inst in (0x46B, 0x6E1, 0x6E3, 0x6E5, 0x7A9) else 0)
        data = body[hdr:]
    fn = work('pictures', 'pic%02d.%s' % (i, ext))
    open(fn, 'wb').write(data)
    print(fn, len(data))
    off += 8 + l; i += 1
