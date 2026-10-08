import sys
from pathlib import Path

# Add repo root and backend directory to sys.path
repo_root = Path(__file__).resolve().parents[1]
backend_dir = repo_root / "backend"

if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
