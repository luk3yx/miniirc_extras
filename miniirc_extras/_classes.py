#!/usr/bin/env python3
#
# Base miniirc_extras classes
#

import abc, collections, io, miniirc, socket, threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

__all__ = ['AbstractIRC', 'DummyIRC', 'Hostmask', 'VersionInfo']

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

    # Get the VersionInfo representation
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

# A dummy IRC class
class DummyIRC(miniirc.IRC):
    def connect(self) -> None: raise NotImplementedError

    def quote(self, *msg: str, force: Optional[bool] = None,
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> None:
        pass

    def __init__(self, ip: str = '', port: int = 0, nick: str = '',
            channels = (), **kwargs) -> None:
        kwargs['auto_connect'] = False
        super().__init__(ip, port, nick, channels, **kwargs)

# An abstract IRC class
_hostmask = Union[Hostmask, Tuple[str, str, str]]
class AbstractIRC(abc.ABC):
    connected = None # type: Optional[bool]
    debug_file = None # type: Optional[Union[io.TextIOWrapper, miniirc._Logfile]]
    sendq = None # type: Optional[List[tuple]]
    msglen = 512 # type: int
    _sasl = False # type: bool
    _unhandled_caps = None # type: Optional[set]

    sock = None # type: socket.socket
    ip = None # type: str
    port = None # type: str
    nick = None # type: str
    channels = None # type: Set[str]
    ident = None # type: str
    realname = None # type: str
    ssl = None # type: Optional[bool]
    persist = True # type: bool
    ircv3_caps = None # type: Set[str]
    active_caps = None # type: Set[str]
    isupport = None # type: Dict[str, Union[str, int]]
    connect_modes = None # type: Optional[str]
    quit_message = 'I grew sick and died.' # type: str
    ping_interval = 60 # type: int
    verify_ssl = True # type: bool

    ns_identity = None # type: Optional[Union[Tuple[str, str], str]]

    @abc.abstractmethod
    def require(self, feature: str) -> Optional[Callable[[miniirc.IRC], Any]]:
        ...

    @abc.abstractmethod
    def debug(self, *args: Any, **kwargs) -> None: ...

    @abc.abstractmethod
    def quote(self, *msg: str, force: Optional[bool] = None,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...

    @abc.abstractmethod
    def msg(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    @abc.abstractmethod
    def notice(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    @abc.abstractmethod
    def ctcp(self, target: str, *msg: str, reply: bool = False,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    @abc.abstractmethod
    def me(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...

    @abc.abstractmethod
    def Handler(self, *events: str, ircv3: bool = False) \
        -> Callable: ...
    @abc.abstractmethod
    def CmdHandler(self, *events: str, ircv3: bool = False) \
        -> Callable: ...

    @abc.abstractmethod
    def connect(self) -> None: ...

    @abc.abstractmethod
    def disconnect(self, msg: Optional[str] = None, *,
        auto_reconnect: bool = False) -> None: ...

    @abc.abstractmethod
    def finish_negotiation(self, cap: str) -> None: ...

    @abc.abstractmethod
    def change_parser(self, parser: Callable[[str],
        Tuple[str, _hostmask, Dict[str, Union[str, bool]],
        List[str]]] = miniirc.ircv3_message_parser) -> None: ...

    @abc.abstractmethod
    def _handle(self, cmd: str, hostmask: _hostmask,
        tags: Dict[str, Union[str, bool]], args: List[str]) -> bool: ...

    @abc.abstractmethod
    def _handle_cap(self, cap: str) -> None: ...

    @abc.abstractmethod
    def _main(self) -> None: ...

    @abc.abstractmethod
    def main(self) -> threading.Thread: ...

    @abc.abstractmethod
    def __init__(self, ip: str, port: int, nick: str,
        channels: Union[List[str], Set[str]] = None, *,
        ssl: Optional[bool] = None, ident: Optional[str] = None,
        realname: Optional[str] = None, persist: bool = True,
        debug: Union[bool, io.TextIOWrapper, str] = False,
        ns_identity: Optional[Union[Tuple[str, str], str]] = None,
        auto_connect: bool = True, ircv3_caps: Union[Set[str], List[str],
        Tuple[str, ...]] = [], connect_modes: Optional[str] = None,
        quit_message: str = 'I grew sick and died.', ping_interval: int = 60,
        verify_ssl: bool = True) -> None: ...

AbstractIRC.register(miniirc.IRC)
