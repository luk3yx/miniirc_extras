#!/usr/bin/env python3
#
# Base miniirc_extras classes
#

import abc, collections, io, miniirc, socket, sys, threading
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, \
    Type, Union
from deprecated import deprecated # type: ignore

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

# Backport namedtuple features - This is made public in utils.py
if sys.version_info >= (3, 7):
    from collections import namedtuple as _namedtuple
else:
    def _namedtuple(typename: str, field_names: Union[str, Iterable[str]], *,
            rename: bool = False, defaults: Optional[Iterable[Any]] = None,
            module: Optional[str] = None):
        # Try and auto-detect the module
        if module is None:
            try:
                module = sys._getframe(1).f_globals.get('__name__', '__main__')
            except:
                pass

        if sys.version_info >= (3, 6):
            res = collections.namedtuple(typename, field_names, # type: ignore
                rename = rename, module = module)
        else:
            res = collections.namedtuple(typename, field_names, # type: ignore
                rename = rename)
            if module is not None:
                res.__module__ = module

        if defaults is not None:
            res.__new__.__defaults__ = tuple(defaults) # type: ignore
        return res

# A version info class
VersionInfo = _namedtuple('VersionInfo', 'major minor micro releaselevel '
    'serial', defaults = (0,0,0, 'final', 0), module = __name__)
VersionInfo.patch = VersionInfo.micro # type: ignore

# Make miniirc.ver a VersionInfo.
miniirc.ver = VersionInfo(*miniirc.ver) # type: ignore

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
    port = None # type: int
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

    # Functions copied from miniirc.IRC.
    def require(self, feature: str) -> Optional[Callable[[miniirc.IRC], Any]]:
        ...
    def debug(self, *args: Any, **kwargs) -> None: ...
    def quote(self, *msg: str, force: Optional[bool] = None,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    def msg(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    def notice(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    def ctcp(self, target: str, *msg: str, reply: bool = False,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...
    def me(self, target: str, *msg: str,
        tags: Optional[Dict[str, Union[str, bool]]] = None) -> None: ...

    # Abstract functions.
    @abc.abstractmethod
    def Handler(self, *events: str, colon: bool = False,
        ircv3: bool = False) -> Callable: ...
    @abc.abstractmethod
    def CmdHandler(self, *events: str, colon: bool = False,
        ircv3: bool = False) -> Callable: ...

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

# Replace some functions with ones from miniirc.IRC
for func in ('debug', 'quote', 'msg', 'notice', 'ctcp', 'me'):
    setattr(AbstractIRC, func, getattr(miniirc.IRC, func)) # type: ignore
del func

AbstractIRC.register(miniirc.IRC)

# A dummy IRC class
# TODO: Move this to miniirc_extras.utils
class _DummyIRC(miniirc.IRC):
    def connect(self) -> None: raise NotImplementedError

    def quote(self, *msg: str, force: Optional[bool] = None,
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> None:
        pass

    def __init__(self, ip: str = '', port: int = 0, nick: str = '',
            channels = (), **kwargs) -> None:
        kwargs['auto_connect'] = False
        super().__init__(ip, port, nick, channels, **kwargs)

_DummyIRC.__qualname__ = _DummyIRC.__name__ = 'DummyIRC'
_DummyIRC.__module__ = __name__.rsplit('.', 1)[0] + '.utils'

@deprecated(version='0.2.6',
            reason='Use miniirc_extras.utils.DummyIRC instead.')
class DummyIRC(_DummyIRC):
    """ Deprecated, use miniirc_extras.utils.DummyIRC instead. """
