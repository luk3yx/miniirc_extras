#!/usr/bin/env python3
#
# Base miniirc_extras classes
#

from __future__ import annotations
import abc, collections, io, miniirc, sys, threading, types
from collections.abc import Callable, Iterable
from typing import Any, Optional, Union

try:
    from deprecated import deprecated # type: ignore
except ImportError:
    def deprecated(**kwargs): return lambda func : func

__all__ = ['AbstractIRC', 'DummyIRC', 'Hostmask', 'VersionInfo']

# Remove ._classes from __module__.
_fixed_name = __name__.rsplit('.', 1)[0]
def _fix_name(cls):
    if cls.__module__.endswith('._classes'):
        cls.__module__ = _fixed_name
    return cls

# A metaclass for instance checking
class _HostmaskMetaclass(type):
    def __instancecheck__(self, other) -> bool:
        # Make sure the other class is a 3-tuple
        if not isinstance(other, tuple) or len(other) != 3:
            return False

        # Make sure all arguments are str instances
        return all(isinstance(i, str) for i in other)

# Create a hostmask class
@_fix_name
class Hostmask(tuple, metaclass=_HostmaskMetaclass):
    def __new__(cls, nick: str, user: str, host: str) -> tuple[str, str, str]: # type: ignore
        res: tuple[str, str, str] = (nick, user, host)
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
                rename=rename, module=module)
        else:
            res = collections.namedtuple(typename, field_names, # type: ignore
                rename=rename)
            if module is not None:
                res.__module__ = module

        if defaults is not None:
            res.__new__.__defaults__ = tuple(defaults) # type: ignore
        return res

# A version info class
VersionInfo = _namedtuple('VersionInfo', 'major minor micro '
    'releaselevel serial', defaults=(0,0,0, 'final', 0),
    module=_fixed_name + '.utils')
VersionInfo.patch = VersionInfo.micro # type: ignore

# Make miniirc.ver a VersionInfo.
miniirc.ver = VersionInfo(*miniirc.ver) # type: ignore

# An abstract IRC class
_hostmask = Union[Hostmask, 'tuple[str, str, str]']
@_fix_name
class AbstractIRC(abc.ABC):
    connected: Optional[bool] = None
    debug_file: Optional[Union[io.TextIOWrapper, miniirc._Logfile]] = None
    msglen: int = 512
    _sasl: bool = False
    _unhandled_caps: Optional[set] = None

    @property
    def current_nick(self) -> str:
        return self.nick

    ip: str
    port: int
    nick: str
    channels: set[str]
    ident: str
    realname: str
    ssl: Optional[bool] = None
    persist: bool = True
    ircv3_caps: set[str]
    active_caps: set[str]
    isupport: dict[str, Union[str, int]]
    connect_modes: Optional[str] = None
    quit_message: str = 'I grew sick and died.'
    ping_interval: int = 60
    verify_ssl: bool = True

    ns_identity: Optional[Union[tuple[str, str], str]] = None

    # Functions copied from miniirc.IRC.
    def require(self, feature: str) -> Any: ...

    def debug(self, *args: Any, **kwargs) -> None:
        """ Debug, calls print() if debug mode is on. """
        ...

    def msg(self, target: str, *msg: str,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        """ Sends a PRIVMSG to `target`. """
        ...

    def notice(self, target: str, *msg: str,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        """ Sends a NOTICE to `target`. """
        ...

    def ctcp(self, target: str, *msg: str, reply: bool = False,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        """ Sends a CTCP request or reply to `target`. """
        ...

    def me(self, target: str, *msg: str,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        """ Sends a /me (CTCP ACTION) to `target`. """
        ...

    # Abstract functions.
    @abc.abstractmethod
    def quote(self, *msg: str, force: Optional[bool] = None,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        """
        Sends a raw message to IRC, use force=True to send while disconnected.
        Do not send multiple commands in one irc.quote(), as the newlines will
        be stripped and it will be sent as one command. The `tags` parameter
        optionally allows you to add a dict with IRCv3 message tags, and will
        not be sent to IRC servers that do not support message tags.
        """
        ...

    @abc.abstractmethod
    def Handler(self, *events: str, colon: bool = False,
            ircv3: bool = False) -> Callable:
        """
        Adds `Handler`s specific to this AbstractIRC object. For more
        information on handlers, see https://github.com/luk3yx/miniirc/#handlers
        or https://gitlab.com/luk3yx/miniirc/#handlers.
        """
        ...

    @abc.abstractmethod
    def CmdHandler(self, *events: str, colon: bool = False,
            ircv3: bool = False) -> Callable:
        """
        Adds `CmdHandler`s specific to this AbstractIRC object. For more
        information on handlers, see https://github.com/luk3yx/miniirc/#handlers
        or https://gitlab.com/luk3yx/miniirc/#handlers.
        """
        ...

    @abc.abstractmethod
    def connect(self) -> None:
        """ Connects to the IRC server if not already connected. """
        ...

    @abc.abstractmethod
    def disconnect(self, msg: Optional[str] = None, *,
            auto_reconnect: bool = False) -> None:
        """
        Disconnects from the IRC server. `auto_reconnect` will be overriden by
        self.persist if set to True.
        """
        ...

    @abc.abstractmethod
    def finish_negotiation(self, cap: str) -> None:
        """
        Removes `cap` from the IRCv3 capability processing list. Use this in
        IRCv3 capability handlers.
        """
        ...

    @abc.abstractmethod
    def change_parser(self, parser: Callable[[str],
            tuple[str, _hostmask, dict[str, Union[str, bool]],
            list[str]]] = miniirc.ircv3_message_parser) -> None:
        """
        Changes the message parser.

        Message parsers are called with the raw message (as a str) and can
        either return None to ignore the message or a 4-tuple (command,
        hostmask, tags, args) that will then be sent on to the handlers. The
        items in this 4-tuple should be the same type as the items expected by
        handlers (and `command` should be a string).
        """
        ...

    @abc.abstractmethod
    def _handle(self, cmd: str, hostmask: _hostmask,
        tags: dict[str, Union[str, bool]], args: list[str]) -> bool: ...

    @abc.abstractmethod
    def __init__(self, ip: str, port: int, nick: str,
        channels: Union[list[str], set[str]] = None, *,
        ssl: Optional[bool] = None, ident: Optional[str] = None,
        realname: Optional[str] = None, persist: bool = True,
        debug: Union[bool, io.TextIOWrapper, str] = False,
        ns_identity: Optional[Union[tuple[str, str], str]] = None,
        auto_connect: bool = True, ircv3_caps: Union[set[str], list[str],
        tuple[str, ...]] = [], connect_modes: Optional[str] = None,
        quit_message: str = 'I grew sick and died.', ping_interval: int = 60,
        verify_ssl: bool = True) -> None: ...

# Add __doc__ to miniirc.IRC functions.
for k in dir(AbstractIRC):
    if k.startswith('_'): continue
    f = getattr(AbstractIRC, k, None)
    if not isinstance(f, types.FunctionType): continue
    f2 = getattr(miniirc.IRC, k, None)
    if isinstance(f2, types.FunctionType) and not f2.__doc__:
        f2.__doc__ = f.__doc__
del k, f, f2

# Replace some functions with ones from miniirc.IRC
MYPY = False
if not MYPY:
    for func in ('debug', 'msg', 'notice', 'ctcp', 'me'):
        f = getattr(miniirc.IRC, func)
        f.__qualname__ = 'Abstract' + f.__qualname__
        f.__module__ = _fixed_name
        setattr(AbstractIRC, func, f)
    del func, f
del MYPY

AbstractIRC.register(miniirc.IRC)

# A dummy IRC class
# TODO: Move this to miniirc_extras.utils
class _DummyIRC(miniirc.IRC):
    def connect(self) -> None: raise NotImplementedError

    def quote(self, *msg: str, force: Optional[bool] = None,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None:
        pass

    def __init__(self, ip: str = '', port: int = 0, nick: str = '',
            channels: Union[list[str], set[str]] = None, **kwargs) -> None:
        kwargs['auto_connect'] = False
        super().__init__(ip, port, nick, channels, **kwargs)

_DummyIRC.__name__ = _DummyIRC.__qualname__ = 'DummyIRC'
_DummyIRC.__module__ = _fixed_name + '.utils'

@_fix_name
@deprecated(version='0.2.6',
            reason='Use miniirc_extras.utils.DummyIRC instead.')
class DummyIRC(_DummyIRC):
    """ Deprecated, use miniirc_extras.utils.DummyIRC instead. """

del _fix_name, _fixed_name
