import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / ".." / "data" / "src"
sys.path.insert(0, str(src.resolve()))
sys.path.insert(0, str(ROOT.resolve()))
