# the handshake: the people (hs/people.json) placed as the original, the documents (hs/docs.py) in front
import json,re,sys
sys.path.insert(0,'hs'); from docs import DOCS as docs
P=json.load(open('hs/people.json'))
d0='<linearGradient id="hs-sheet" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fbfbfb"/><stop offset="1" stop-color="#dadada"/></linearGradient>'
s=0.632; I,O=1.81/s,5.66/s
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 403 477" width="403" height="477">
 <!-- Two people shaking hands over a stack of documents: an agreement (the Visio work-flow shape of the UBL CPFR
      figures), in grey. The person on the right is the person at the head of the meeting table, mirrored, standing;
      the one on the left the same person from behind. The documents drawn. Isometric, 30 degrees. -->
 <defs>{d0}{''.join(P['defs'])}</defs>
 <g transform="matrix(0.63 0 0 0.635 7 -12)">   <!-- the render placed as the original: fitted on the outlines -->
  {''.join(P['fills'])}
  <g fill="none" stroke="#262626" stroke-width="{I:.2f}" stroke-linejoin="round" stroke-linecap="round">{''.join(f'<path d="{l}"/>' for l in P['lines'])}</g>
  <path d="{P['outline']}" fill="none" stroke="#262626" stroke-width="{O:.2f}" stroke-linejoin="round"/>
 </g>
{docs}</svg>'''
open('v2/handshake-clean.svg','w').write(svg); print(len(svg)//1024,'KB')
