"""Where things are, for the scripts that made the four Fulfilment illustrations.

  PPT    the deck they come from, ShipmentConsignment-2.ppt (README: where to
         get it); default <WORK>/ShipmentConsignment-2.ppt, where run.sh puts it
  UBL    a clone of the UBL repository (https://github.com/oasis-tcs/ubl, branch
         ubl-2.5), for its art/ (the PNGs); default ubl, beside this repository,
         as for history/drawio-edits/diff
  WORK   where the scripts write what is not kept; default work/, here
  PARTS  the parts the drawings are made of: illustrations/parts/ (kept)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WORK = os.environ.get('WORK') or os.path.join(HERE, 'work')
PPT = os.environ.get('PPT') or os.path.join(WORK, 'ShipmentConsignment-2.ppt')
UBL = os.environ.get('UBL') or os.path.join(os.path.dirname(ROOT), 'ubl')
ART = os.path.join(UBL, 'art')
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
FIGURES = {2: 'UBL-2.2-Fulfilment-1simple', 3: 'UBL-2.2-Fulfilment-2split',
           4: 'UBL-2.2-Fulfilment-3intermediary', 5: 'UBL-2.2-Fulfilment-4consolidated'}   # slide -> figure


def work(*p):
    """a path in WORK, its directory made"""
    f = os.path.join(WORK, *p)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    return f
