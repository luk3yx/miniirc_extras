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
ver     = VersionInfo(0,2,8, 'alpha')
version = 'miniirc v{}.{}.{} / miniirc_extras v{}.{}.{}'.format(miniirc.ver[0],
    miniirc.ver[1], miniirc.ver[2], ver[0], ver[1], ver[2])

# The base exception class
class error(Exception):
    pass

# The require() code may eventually move into miniirc.
if hasattr(miniirc, 'Feature'):
    from miniirc import Feature # type: ignore
else:
    from ._require import Feature

AbstractIRC.require = miniirc.IRC.require
AbstractIRC.require.__qualname__ = 'AbstractIRC.require'
AbstractIRC.require.__module__ = __name__

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

# Set a few docstrings.
miniirc.ircv3_message_parser.__doc__ = """
    The default IRCv2/IRCv3 message parser, returns a 4-tuple:
    (`command`, `hostmask`, `tags`, `args`). Do not use this directly, if you
    want to parse IRCv3 messages in your own code use
    `miniirc_extras.utils.ircv3_message_parser`, and if you want to reset the
    message parser on an IRC object, call `irc.change_parser()` without any
    parameters.
"""

miniirc.Handler.__doc__ = """
    Adds `Handler`s to every IRC object that will ever exist (inside the
    current process). For more information on handlers, see
    https://github.com/luk3yx/miniirc/#handlers
    or https://gitlab.com/luk3yx/miniirc/#handlers.
"""

miniirc.CmdHandler.__doc__ = """
    Adds `CmdHandler`s to every IRC object that will ever exist (inside the
    current process). For more information on handlers, see
    https://github.com/luk3yx/miniirc/#handlers
    or https://gitlab.com/luk3yx/miniirc/#handlers.
"""
