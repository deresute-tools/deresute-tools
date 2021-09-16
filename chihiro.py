import os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
if __name__ == '__main__':
    import pyximport

    pyximport.install(language_level=3)
    import sys
    sys.path.insert(1, 'src')
    import main
    main.main()
