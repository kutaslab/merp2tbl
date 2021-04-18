import re

# single source the python package version
__version__ = "0.1.4"


def get_ver():
    pf_ver = re.search(r"(?P<ver_str>\d+\.\d+\.\d+\S*)", __version__)

    if pf_ver is None:
        msg = f"""Illegal spudtr __version__: {__version__}
        spudtr __init__.py must have an X.Y.Z semantic version, e.g.,

        __version__ = '0.0.0'
        __version__ = '0.0.0.dev0'
        __version__ = '0.0.0rc1'

        """
        raise Exception(msg)
    else:
        return pf_ver["ver_str"]
