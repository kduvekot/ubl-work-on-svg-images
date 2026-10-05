import json, re
p=json.load(open('lines/person2.json'))
s_,ox,oy=0.68,-24,-6; I,O=1.6/s_,5/s_
person=f'''<g transform="matrix({s_} 0 0 {s_} {ox} {oy})">
 <defs>{''.join(p['defs'])}</defs>
 {''.join(p['fills'])}
 <g fill="none" stroke="#262626" stroke-width="{I:.2f}" stroke-linejoin="round" stroke-linecap="round">{''.join(f'<path d="{d}"/>' for d in p['lines'])}</g>
 <g stroke="#262626" stroke-width="{I:.2f}">{''.join(p['hands'])}</g>
 <path d="{p['sil']}" fill="none" stroke="#262626" stroke-width="{O:.2f}" stroke-linejoin="round"/>
</g>'''
s=open('v2/desk9.svg').read()
s=re.sub(r'<g transform="matrix\(0\.68 0 0 0\.68 -24 -6\)">.*?\n</g>',lambda m:person,s,flags=re.S)
# the chair: a low, narrow back behind him, seen on its edge: its side and its front face, behind the desk
s=re.sub(r'<path d="M17,140 L31,132 L37,135 L60,135 L60,215 L17,234 Z"[^>]*/>\n','',s)
chair='''<g stroke="#262626" stroke-width="5" stroke-linejoin="round">
  <path d="M20,131 L30,126 L30,245 L20,245 Z" fill="#7a7a7a"/>
  <path d="M30,126 L41,131 L52,131 L52,245 L30,245 Z" fill="#a6a6a6"/>
 </g>
 '''
# the chair: the back of it, a slab standing behind his back, along the edge he sits at, as wide as his back;
# only its end, left of him, shows (measured on the original: x 25..37, its top at y 130..134)
import numpy as _np
_U=_np.array([0.866,-0.5]); _V=_np.array([0.866,0.5]); _Z=_np.array([0,-1.])
_F=_np.array([32.,134.]); _t,_Lc,_H=8.,88.,100.
_q=lambda *ps:' L'.join(f'{p[0]:.1f},{p[1]:.1f}' for p in ps)
_A,_B2,_C=_F-_t*_V,_F+_Lc*_U,_F-_t*_V+_Lc*_U
chair=(' <g stroke="#262626" stroke-width="5" stroke-linejoin="round">\n'
  f'  <path d="M{_q(_F,_B2,_B2-_H*_Z,_F-_H*_Z)} Z" fill="#a8a8a8"/>\n'
  f'  <path d="M{_q(_A,_F,_F-_H*_Z,_A-_H*_Z)} Z" fill="#888888"/>\n'
  f'  <path d="M{_q(_A,_C,_B2,_F)} Z" fill="#d0d0d0"/>\n </g>\n')
s=s.replace('<g transform="translate(0,-5)"><g stroke="#262626" stroke-width="5"',chair+'<g transform="translate(0,-5)"><g stroke="#262626" stroke-width="5"',1)
assert 'fill="#888888"' in s

# the paper: an open book, two pages side by side, the fold across its short way, a thick dark (green) rim;
# corners measured on the original (+5: this group is shifted up by 5)
import numpy as _np
_L=_np.array([143,203.]);_T=_np.array([231,156.]);_R=_np.array([281,186.]);_B=_np.array([193,232.])
_sh=_np.array([-10.,-5.8]); _L,_T,_R,_B=_L+_sh,_T+_sh,_R+_sh,_B+_sh   # towards him and the edge he sits at
_f=0.53; _p=_L+(_T-_L)*_f; _q=_B+(_R-_B)*_f
_P=lambda v:f"{v[0]:.1f},{v[1]:.1f}"
paper=(f'<path d="M{_P(_L)} L{_P(_T)} L{_P(_R)} L{_P(_B)} Z" fill="#f4f4f4" stroke="#6a6a6a" stroke-width="4"/>\n'
       f'  <path d="M{_P(_p)} L{_P(_q)}" fill="none" stroke="#7a7a7a" stroke-width="1.3"/>\n')
s=re.sub(r'<path d="M146,198 L229,150 L285,181 L201,229 Z"[^>]*/>\n\s*<path d="M174,214 L257,166"[^>]*/>\n',lambda m:paper,s)
assert 'M133.0,197.2' in s

import sys; sys.path.insert(0,'lines'); from calc import CALC
s=re.sub(r'<!-- the calculator, its paper tape.*?(?=\n </g>\n</svg>)',lambda m:CALC,s,flags=re.S)
assert 'printer roll' in s

# outlines: outer edges 5, as the original at its own size (74 px wide: a 1 px outline); inner lines 1.6
open('v2/desk10.svg','w').write(s)
