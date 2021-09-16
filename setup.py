from setuptools import setup
from Cython.Build import cythonize

setup(
    package_dir={'src': ''},
    ext_modules=cythonize(
        ["*.pyx", "logic/*.pyx"],
        language_level="3"
    )
)
