"""Lecteur minimal de sommaire IoStore (.utoc) d'Unreal Engine 5.

Un fichier .utoc est la table des matières d'une archive du jeu (.ucas). Ce script n'en
lit que l'index des noms : il liste les éléments que l'archive contient, sans jamais
lire ni extraire leur contenu. Testé sur les archives d'Assetto Corsa Rally 0.6
(version de sommaire 8, non chiffrées).

Usage : python3 lire_utoc.py fichier.utoc [autre.utoc ...]
"""
import struct, sys

def read_fstring(b, o):
    n, = struct.unpack_from('<i', b, o); o += 4
    if n == 0: return '', o
    if n > 0:
        s = b[o:o+n-1].decode('utf-8', 'replace'); return s, o + n
    n = -n
    s = b[o:o+2*n-2].decode('utf-16-le', 'replace'); return s, o + 2*n

def parse(path):
    b = open(path, 'rb').read()
    assert b[:16] == b'-==--==--==--==-', 'magic'
    (ver, _r0, _r1, hsize, nent, nblk, blksz, nmeth, methlen, cblock, dirsize, nparts, cid) = struct.unpack_from('<BBHIIIIIIIIIQ', b, 16)
    guid = b[64:80]
    flags = b[80]
    nseeds, = struct.unpack_from('<I', b, 84)
    partsize, = struct.unpack_from('<Q', b, 88)
    nwo, = struct.unpack_from('<I', b, 96)
    info = dict(version=ver, header=hsize, entries=nent, blocks=nblk, methods=nmeth, dirsize=dirsize, flags=flags,
                seeds=nseeds, without_hash=nwo, encrypted=bool(flags & 2), signed=bool(flags & 4), indexed=bool(flags & 8))
    o = hsize
    o += nent * 12            # chunk ids
    o += nent * 10            # offsets + lengths
    if ver >= 4: o += nseeds * 4
    if ver >= 5: o += nwo * 4
    o += nblk * blksz
    meths = [b[o+i*methlen:o+(i+1)*methlen].split(b'\0')[0].decode() for i in range(nmeth)]
    info['compression'] = meths
    o += nmeth * methlen
    if flags & 4:
        hs, = struct.unpack_from('<i', b, o); o += 4 + 2*hs + nblk*20
    d = b[o:o+dirsize]
    if not (flags & 8) or dirsize == 0 or (flags & 2):
        return info, []
    mount, p = read_fstring(d, 0)
    nd, = struct.unpack_from('<i', d, p); p += 4
    dirs = [struct.unpack_from('<IIII', d, p + 16*i) for i in range(nd)]; p += 16*nd
    nf, = struct.unpack_from('<i', d, p); p += 4
    files = [struct.unpack_from('<III', d, p + 12*i) for i in range(nf)]; p += 12*nf
    ns, = struct.unpack_from('<i', d, p); p += 4
    strs = []
    for _ in range(ns):
        s, p = read_fstring(d, p); strs.append(s)
    info['mount'] = mount
    out, NONE = [], 0xFFFFFFFF
    stack = [(0, mount)]
    while stack:
        di, prefix = stack.pop()
        while di != NONE:
            name, child, sib, ffile = dirs[di]
            path = prefix + (strs[name] + '/' if name != NONE else '')
            fi = ffile
            while fi != NONE:
                fn, nxt, _ud = files[fi]
                out.append(path + strs[fn]); fi = nxt
            if child != NONE: stack.append((child, path))
            di = sib
    return info, sorted(out)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        info, names = parse(p)
        print(p.split('/')[-1], info, len(names))
        for n in names:
            print('  ', n)
