import os
from pathlib import Path

from setuptools import setup
from Cython.Build import cythonize

root = Path(os.path.dirname(os.path.abspath(__file__)))
os.chdir(str(root / "src"))

setup(
    package_dir={'src': ''},
    ext_modules=cythonize(
        ["*.pyx", "logic/*.pyx"],
        language_level="3"
    )
)
