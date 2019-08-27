# to install in development mode, from this directory run
# 
#     pip install -e . 
#  
#  to install stable package, clone, then as root run 
#
#    pip install .
# 
#   and then link the merp2table script in the python site-packages
#   to /usr/local/anaconda3/bin/merp2table to merp2table script 
# 
# or run
# 
#    python ./setup.py install --install-scripts=/usr/local/anaconda3/bin
#
# may need this
#  
#     python setup.py clean --all
# 
# http://python-packaging.readthedocs.io/en/latest/minimal.html

from setuptools import  find_packages, setup, Extension
setup(
    name='merp2tbl',
    version = '0.2.0',
    description='format ERPSS merp verbose output to tab-separated text or yaml',
    author='Tom Urbach',
    author_email='turbach@ucsd.edu',
    url='http://kutaslab.ucsd.edu/people/urbach',
    packages=find_packages(), 
    entry_points = {
        'console_scripts': ['merp2table=merp2tbl.merp2tbl:main'],
    },
)

