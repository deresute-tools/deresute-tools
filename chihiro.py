import os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
if __name__ == '__main__':
    import main
    main.main()
