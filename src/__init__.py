"""MarketLens: reproducible city housing affordability research."""
import os
from pathlib import Path

Path('tmp/matplotlib').mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(Path('tmp/matplotlib')))
