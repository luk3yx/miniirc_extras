#!/usr/bin/env python3
#
# miniirc_extras: Adds extendability to miniirc.
#
# © 2019 by luk3yx.
#

import miniirc, os, sys
assert hasattr(miniirc, 'ver') and miniirc.ver >= (1,3,2), \
    'miniirc_extras requires miniirc >= 1.3.2.'

from miniirc import CmdHandler, Handler, IRC
from typing import Any, List

# Version info
ver = (0,0,1)
version = 'miniirc v{} / miniirc_extras v0.0.1'
version = version.format('.'.join(map(str, miniirc.ver)))

# The base exception class
class error(Exception):
    pass

# The require() code may eventually move into miniirc.
if hasattr(miniirc, 'Feature'):
    from miniirc import Feature # type: ignore
else:
    from ._require import Feature

# Load features on-the-fly when required
def _core_feature(name: str) -> None:
    module = __name__ + '.features.' + name # type: str

    @Feature(name)
    def _feature(irc: miniirc.IRC) -> Any:
        if name.startswith('_'):
            print('WARNING: WIP feature loaded!', file = sys.stderr)

        __import__(module)
        return irc.require(name)

# Create __all__
__all__ = ['CmdHandler', 'Feature', 'Handler', 'IRC', 'error'] # type: List[str]

# Add core features
for f in os.listdir(os.path.dirname(__file__) + os.sep + 'features'):
    if not f.startswith('__') and f.endswith('.py'):
        _core_feature(f[:-3])

del f
