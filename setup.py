# Installation (from a bash shell terminal window)
#
# The options are to install system wide for all users # as root for
# for individual users by installing into a conda virtual environment.
#
#
# 1. navigate to some working directory and clone the git repo like so
#
#      $ git clone https://github.com/kutaslab/merp2tbl
#
#
# 2. Option A: Install for all users (as root or sudo)
#
#   2.1 confirm pip is the anaconda version, should look something like this
#
#      $ which pip
#      /usr/local/anaconda3/bin/pip
#
#   2.2  navigate into the merp2tbl directory with this setup.py file and run
#
#      $ pip uninstall merp2tbl
#      $ pip install .
#
#   2.3 confirm the merp2table executable is the one anaconda installed
#
#       $ which merp2table
#       /usr/local/anaconda3/bin/merp2table
#
#
# 3. Option B: Install per-user into a conda environment (does not need root)
#
#   3.1 navigate to merp2tabl/conda and create a new merp2table_0.2 env like so
#
#       $ conda env create -f environment.yml
#
#   3.2 activate the new environemnt like so
#
#       $ conda activate merp2table_0.2
#
#   3.3 navigate back up to the merp2tbl directory that has setup.py and
#       install merp2table in the active environment like so
#
#       (merp2table_0.2) $ pip install .
#
#   3.4 confirm the merp2table executable is the one in the active environment
#
#       (merp2table_0.2) $ which merp2table
#       ~/.conda/envs/merp2table_0.2/bin/merp2table
#
#
# 4. Option C: (for programmers) install in a conda env as in Option B
#    and run pip like so to install in develop mode
#
#       (merp2table_0.2) $ pip install -e .
#

from setuptools import find_packages, setup, Extension

setup(
    name="merp2tbl",
    version="0.1.3",
    description="format ERPSS merp verbose output to tab-separated text or yaml",
    author="Tom Urbach",
    author_email="turbach@ucsd.edu",
    url="http://kutaslab.ucsd.edu/people/urbach",
    packages=find_packages(),
    entry_points={"console_scripts": ["merp2table=merp2tbl.merp2tbl:main"]},
)
