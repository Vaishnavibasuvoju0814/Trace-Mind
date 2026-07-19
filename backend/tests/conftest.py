import sys
from pathlib import Path

# Ensure the backend package root is importable when running
# `pytest d:\agent-crew\backend\tests\test_agents.py` directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))