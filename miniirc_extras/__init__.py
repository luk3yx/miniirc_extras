#!/usr/bin/env python3
#
# miniirc_extras: Adds extendability to miniirc.
#
# © 2019 by luk3yx.
#

import miniirc, os, sys
assert hasattr(miniirc, 'ver') and miniirc.ver >= (1,4,0), \
    'miniirc_extras requires miniirc >= 1.4.0.'

from miniirc import CmdHandler, Handler, IRC
from typing import Any, List
from ._classes import *

# Version info
ver     = VersionInfo(0,2,5, 'alpha')
version = 'miniirc v{} / miniirc_extras v{}'.format(miniirc.ver, ver)

# The base exception class
class error(Exception):
    pass

# The require() code may eventually move into miniirc.
if hasattr(miniirc, 'Feature'):
    from miniirc import Feature # type: ignore
else:
    from ._require import Feature

AbstractIRC.require = miniirc.IRC.require

# Load features on-the-fly when required
def _core_feature(name: str) -> None:
    module = __name__ + '.features.' + name # type: str

    @Feature(name)
    def _feature(irc: miniirc.IRC) -> Any:
        if name.startswith('_'):
            print('WARNING: WIP feature loaded!', file=sys.stderr)

        __import__(module)
        return irc.require(name)

# Create __all__
__all__ = ['CmdHandler', 'Feature', 'Handler', 'IRC', 'error'] # type: List[str]

# Load the base classes
from . import _classes
__all__.extend(_classes.__all__)
del _classes

# Add core features
for f in os.listdir(os.path.dirname(__file__) + os.sep + 'features'):
    if not f.startswith('__') and f.endswith('.py'):
        _core_feature(f[:-3])

del f
