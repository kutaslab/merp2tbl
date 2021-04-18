from setuptools import find_packages, setup  # , Extension
from merp2tbl import get_ver


setup(
    name="merp2tbl",
    version=get_ver(),
    description="format ERPSS merp verbose output to tab-separated text or yaml",
    author="Tom Urbach",
    author_email="turbach@ucsd.edu",
    url="http://kutaslab.ucsd.edu/people/urbach",
    packages=find_packages(),
    entry_points={"console_scripts": ["merp2table=merp2tbl.merp2tbl:main"]},
)
