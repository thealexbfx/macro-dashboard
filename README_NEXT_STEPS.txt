MacroLens Phase 1 Refactor Pack

What this contains:
- config.py
- data/fred.py
- data/bls.py
- data/bea.py
- data/yahoo.py
- data/transforms.py
- data/local.py
- indicators/usa.py

Safe workflow:
1) Copy these files/folders into your project root next to app.py.
2) Do NOT delete functions from app.py yet.
3) Add imports to app.py and test one function at a time.
4) Once imports work, then delete/move duplicated functions from app.py in small batches.

Suggested first import block in app.py:
from indicators.usa import *
from data.yahoo import get_fx_data_yahoo
from data.local import load_local_macro_data, load_usa_data
from data.transforms import calculate_yoy_from_index, calculate_mom_pct_change, calculate_diff

Run:
streamlit run app.py

If it breaks, undo only the last small change.
