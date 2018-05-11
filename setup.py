# to install in development mode, from this directory run
# 
#     pip uninstall eegr
#     python ./setup.py build_ext --inplace
#     python ./setup.py develop -d ~/.local/lib/python3.6/site-packages/
#
#  to install stable package, as root run 
#
#    pip install .
# 
# http://python-packaging.readthedocs.io/en/latest/minimal.html

# from Cython.Distutils import build_ext
# from Cython.Build import cythonize
from setuptools import  find_packages, setup, Extension
import numpy as np

# extensions =  [
#     Extension("merp2tbl._merp2tbl",
#               ["merp2tbl/_merp2tbl.pyx"],
#               include_dirs=[np.get_include()],
#           )
# ]

setup(
    name='merp2tbl',
    version = '0.1',
    description='parse ERPSS merp long form output',
    author='Tom Urbach',
    author_email='turbach@ucsd.edu',
    url='http://kutaslab.ucsd.edu/people/urbach',
    packages=find_packages(), 
    scripts=['bin/merp2tbl'],
#    cmdclass = {'build_ext': build_ext},
#    ext_modules = cythonize(extensions)
)

