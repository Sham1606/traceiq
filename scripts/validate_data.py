from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
cmd = [sys.executable, "-m", "pytest", "-q"]
result = subprocess.run(cmd, cwd=DATA, env={**__import__('os').environ, "PYTHONPATH": str(DATA / "src")})
raise SystemExit(result.returncode)
