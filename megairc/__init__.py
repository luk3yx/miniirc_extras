#!/usr/bin/env python3
#
# megairc: Adds extendability to miniirc.
#
# © 2019 by luk3yx.
#

import miniirc, os, sys
from miniirc import *

assert hasattr(miniirc, 'ver') and miniirc.ver >= (1,3,2), \
    'megairc requires miniirc >= 1.3.2.'

# Version info
ver = (0,0,1)
version = 'megairc v0.0.1 (running on miniirc v{})'
version = version.format('.'.join(map(str, miniirc.ver)))

# The base exception class
class error(Exception):
    pass

# The require() code may eventually move into miniirc.
if not hasattr(miniirc, 'Feature') or not hasattr(IRC, 'require'):
    from ._require import Feature

# Load features on-the-fly when required
def _core_feature(name):
    module = __name__ + '.features.' + name

    @Feature(name)
    def _feature(irc):
        if name.startswith('_'):
            print('WARNING: WIP feature loaded!', file = sys.stderr)

        __import__(module)
        return irc.require(name)

# Create __all__
__all__ = ['error']
__all__.extend(miniirc.__all__)
if 'Feature' not in __all__:
    __all__.append('Feature')

# Add core features
for f in os.listdir(os.path.dirname(__file__) + os.sep + 'features'):
    if f.endswith('.py'):
        _core_feature(f[:-3])

del f
