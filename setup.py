# to install in development mode, from this directory run
# 
#     pip uninstall merp2tbl
#     python setup.py clean --all
#     python ./setup.py build_ext --inplace
#     python ./setup.py develop -d ~/.local/lib/python3.6/site-packages/ 
#
# python ./setup.py develop -d ~/.local/lib/python3.6/site-packages --install-option="--install-scripts=/home/turbach/.local/bin"
#  to install stable package, as root run 
#
#    pip uninstall merp2tbl
#    pip install . --install-scripts=/usr/local/anaconda/bin
# 
#  Note it may be necessary to prerun 
#  
#  
# 
# http://python-packaging.readthedocs.io/en/latest/minimal.html

# from Cython.Distutils import build_ext
# from Cython.Build import cythonize
from setuptools import  find_packages, setup, Extension
import numpy as np

setup(
    name='merp2tbl',
    version = '0.1',
    description='format ERPSS merp verbose output to tab-separated text or yaml',
    author='Tom Urbach',
    author_email='turbach@ucsd.edu',
    url='http://kutaslab.ucsd.edu/people/urbach',
    packages=find_packages(), 
    entry_points = {
        'console_scripts': ['merp2table=merp2tbl.merp2tbl:main'],
    },
#    cmdclass = {'build_ext': build_ext},
#    ext_modules = cythonize(extensions)
)

