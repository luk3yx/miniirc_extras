#!/usr/bin/env python3
#
# Base miniirc_extras classes
#

import collections, miniirc
from typing import Any, NewType, Optional, Tuple, Union

__all__ = ['Hostmask', 'VersionInfo']

# A metaclass for instance checking
class _HostmaskMetaclass(type):
    def __instancecheck__(self, other) -> bool:
        # Make sure the other class is a 3-tuple
        if not isinstance(other, tuple) or len(other) != 3:
            return False

        # Make sure all arguments are str instances
        return all(isinstance(i, str) for i in other)

# Create a hostmask class
class Hostmask(tuple, metaclass = _HostmaskMetaclass):
    def __new__(cls, nick: str, user: str, host: str) -> Tuple[str, str, str]:
        res = (nick, user, host) # type: Tuple[str, str, str]
        if not all(isinstance(i, str) for i in res):
            raise TypeError('{} is not a valid hostmask!'.format(res))
        return res

# A version info class
class VersionInfo(tuple):
    """ A version info class, similar to sys.version_info. """

    # TODO: Make this nicer
    @property
    def major(self) -> int:
        return self[0]

    @property
    def minor(self) -> int:
        return self[1]

    @property
    def micro(self) -> int:
        return self[2]
    patch = micro

    @property
    def releaselevel(self) -> str:
        return self[3]

    @property
    def serial(self) -> int:
        return self[4]

    # Get the VersinoInfo representation
    def __repr__(self) -> str:
        return '{}{}'.format(type(self).__name__,
            tuple(self) if self.serial else self[:-1])

    # Convert it into a human-readable string
    def __str__(self) -> str:
        res = '{}.{}.{}'.format(self.major, self.minor, self.micro)
        if self.releaselevel != 'final' or self.serial:
            res += ' ' + self.releaselevel
            if self.serial:
                res = '{} {}'.format(res, self.serial)
        return res

    # Prevent attributes being modified
    def __setattr__(self, attr, value):
        raise AttributeError("Can't set attributes on VersionInfo.")

    # Get an arguments list
    @staticmethod
    def _get_args(major: int, minor: int, micro: int = 0,
            releaselevel: str = 'final', serial: int = 0) -> Tuple[int, int,
            int, str, int]:
        return (int(major), int(minor), int(micro), str(releaselevel),
            int(serial))

    def __new__(cls, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], tuple) and not kwargs:
            args = args[0]
        return tuple.__new__(cls, cls._get_args(*args, **kwargs))

# Make miniirc.ver a VersionInfo.
miniirc.ver = VersionInfo(miniirc.ver) # type: ignore
