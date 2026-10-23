import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # los scripts del pipeline se importan entre sí por nombre
