# Reads the shapes of the deck's slides: type, anchor (master units, 576 per
# inch), properties, text and its style runs.
import olefile, struct
from paths import PPT
o = olefile.OleFileIO(PPT); d = o.openstream('PowerPoint Document').read()

def rec(off):
    vi, t, l = struct.unpack_from('<HHI', d, off)
    return vi & 0xf, vi >> 4, t, l
def children(off, l):
    p = off
    while p + 8 <= off + l:
        v, inst, t, ln = rec(p); yield p + 8, v, inst, t, ln; p += 8 + ln

def props(off, n):
    out, cx = {}, off + 6 * n
    for k in range(n):
        pid, val = struct.unpack_from('<HI', d, off + 6 * k)
        if pid & 0x8000:   # complex: its data follows the table
            out[pid & 0x3fff] = d[cx:cx + val]; cx += val
        else:
            out[pid & 0x3fff] = val
    return out

def shape(off, l):
    s = {'props': {}, 'text': None}
    for p, v, inst, t, ln in children(off, l):
        if t == 0xF00A: s['type'] = inst; s['id'], s['flags'] = struct.unpack_from('<II', d, p)
        elif t in (0xF00B, 0xF122): s['props'].update(props(p, inst))
        elif t == 0xF010: s['anchor'] = struct.unpack_from('<4h', d, p) if ln == 8 else struct.unpack_from('<4i', d, p)
        elif t == 0xF00F: s['child'] = struct.unpack_from('<4i', d, p)   # left, top, right, bottom
        elif t == 0xF00D:   # client textbox
            for q, v2, i2, t2, l2 in children(p, ln):
                if t2 == 4000: s['text'] = d[q:q + l2].decode('utf-16le')
                elif t2 == 4008: s['text'] = d[q:q + l2].decode('latin1')
                elif t2 == 0x0FA1: s['style'] = d[q:q + l2]
                elif t2 == 3999: s['texttype'] = struct.unpack_from('<I', d, q)[0]
    return s

def group(off, l, depth=0):
    """[shape] of a SpgrContainer, the first being the group itself"""
    out = []
    for p, v, inst, t, ln in children(off, l):
        if t == 0xF004: out.append(shape(p, ln))
        elif t == 0xF003: out.append(group(p, ln, depth + 1))
    return out

def slides():
    res, n = [], 0
    for p, v, inst, t, ln in children(0, len(d)):
        pass
    # walk everything for Slide records (1006) in document order
    def walk(off, l):
        for p, v, inst, t, ln in children(off, l):
            if t == 1006:
                res.append(slide_shapes(p, ln))
            elif v == 0xf and t not in (1006,):
                walk(p, ln)
    walk(0, len(d))
    return res

def slide_shapes(off, l):
    def find(off, l, T):
        for p, v, inst, t, ln in children(off, l):
            if t == T: return p, ln
            if v == 0xf:
                r = find(p, ln, T)
                if r: return r
    p, ln = find(off, l, 0xF003)    # the slide's top group
    return group(p, ln)

if __name__ == '__main__':
    NAMES = {0: 'none', 1: 'rect', 20: 'line', 32: 'connector', 75: 'picture', 202: 'textbox'}
    ss = slides()
    for i, sh in enumerate(ss[:6]):
        print('=== slide', i + 1)
        def pr(g, ind=''):
            for s in (g[1:] if isinstance(g, list) else [g]):
                if isinstance(s, list): print(ind + 'group', s[0].get('anchor'), s[0].get('child')); pr(s, ind + '  '); continue
                ps = {('%x' % k): (v if not isinstance(v, bytes) else len(v)) for k, v in s['props'].items()}
                print(ind, NAMES.get(s.get('type'), s.get('type')), 'flags %x' % s.get('flags', 0), s.get('anchor') or s.get('child'),
                      repr(s['text'])[:40] if s['text'] else '', ps)
        pr(sh)

def text_style(st, text):
    """(paragraph runs [(count, align)], character runs [(count, size_pt, bold, fontref, colour)])"""
    import struct
    p, paras, chars, n = 0, [], [], len(text) + 1
    got = 0
    while got < n and p < len(st):
        cnt, = struct.unpack_from('<I', st, p); p += 4
        indent, = struct.unpack_from('<H', st, p); p += 2
        mask, = struct.unpack_from('<I', st, p); p += 4
        align = None
        if mask & 0xF: p += 2                      # bulletFlags
        if mask & (1 << 7): p += 2                 # bulletChar
        if mask & (1 << 4): p += 2                 # bulletFontRef
        if mask & (1 << 6): p += 2                 # bulletSize
        if mask & (1 << 5): p += 4                 # bulletColor
        if mask & (1 << 11): align, = struct.unpack_from('<H', st, p); p += 2
        if mask & (1 << 12): p += 2                # lineSpacing
        if mask & (1 << 13): p += 2                # spaceBefore
        if mask & (1 << 14): p += 2                # spaceAfter
        if mask & (1 << 8): p += 2                 # leftMargin
        if mask & (1 << 10): p += 2                # indent
        if mask & (1 << 9): p += 2                 # defaultTabSize
        if mask & (1 << 20):                       # tabStops
            c, = struct.unpack_from('<H', st, p); p += 2 + 4 * c
        if mask & (1 << 16): p += 2                # fontAlign
        if mask & (7 << 17): p += 2                # wrapFlags
        if mask & (1 << 21): p += 2                # textDirection
        paras.append((cnt, align)); got += cnt
    got = 0
    while got < n and p < len(st):
        cnt, = struct.unpack_from('<I', st, p); p += 4
        mask, = struct.unpack_from('<I', st, p); p += 4
        size = bold = font = col = None
        if mask & 0xFFFF:
            fs, = struct.unpack_from('<H', st, p); p += 2; bold = bool(fs & 1)
        if mask & (1 << 16): font, = struct.unpack_from('<H', st, p); p += 2
        if mask & (1 << 21): p += 2
        if mask & (1 << 22): p += 2
        if mask & (1 << 23): p += 2
        if mask & (1 << 17): size, = struct.unpack_from('<H', st, p); p += 2
        if mask & (1 << 18): col, = struct.unpack_from('<I', st, p); p += 4
        if mask & (1 << 19): p += 2
        chars.append((cnt, size, bold, font, col)); got += cnt
    return paras, chars

def fonts():
    """the font collection: [name]"""
    import struct
    out = []
    def walk(off, l):
        for p, v, inst, t, ln in children(off, l):
            if t == 4023: out.append(d[p:p + 64].decode('utf-16le').split('\x00')[0])
            elif v == 0xf: walk(p, ln)
    walk(0, len(d)); return out
