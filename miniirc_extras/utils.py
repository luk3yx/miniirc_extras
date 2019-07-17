#!/usr/bin/env python3
#
# Miscellaneous miniirc_extras utilities
#

import collections, functools, miniirc, re, socket
from . import AbstractIRC, error as _error, Hostmask
from ._classes import _DummyIRC as DummyIRC, _namedtuple as namedtuple, \
    VersionInfo
from ._numerics import numerics
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from deprecated import deprecated # type: ignore

__all__ = ['DummyIRC', 'dict_to_tags', 'tags_to_dict', 'ircv3_message_parser',
    'hostmask_to_str', 'ircv2_message_unparser', 'ircv3_message_unparser',
    'namedtuple']

if namedtuple.__module__.endswith('._classes'):
    namedtuple.__name__ = namedtuple.__qualname__ = 'namedtuple'
    namedtuple.__module__ = __name__
    namedtuple.__doc__ = collections.namedtuple.__doc__

# Copy "internal functions" from miniirc
dict_to_tags = miniirc._dict_to_tags
dict_to_tags.__module__ = __name__
dict_to_tags.__name__ = dict_to_tags.__qualname__ = 'dict_to_tags'
dict_to_tags.__doc__ = """
Converts a dict containing strings and booleans into an IRCv3 tags string.
Example:
    dict_to_tags({'tag1': True, 'tag2': 'tag-data'})
    Return value: b'@tag1;tag2=tag-data '
"""

try:
    _tags_to_dict = miniirc._tags_to_dict
except AttributeError:
    # A hack in case _tags_to_dict is removed.
    def _tags_to_dict(tag_list: Union[str, List[str]],
            separator: Optional[str] = ';') -> Dict[str, Union[str, bool]]:
        if not separator:
            assert isinstance(tag_list, list)
            tag_list = ';'.join(map(lambda i : i.replace(';', '\\:'), tag_list))
        elif separator != ';':
            assert isinstance(tag_list, str)
            tag_list = tag_list.replace(';', '\\:').replace(separator, ';')
        cmd, hostmask, tags, args = miniirc.ircv3_message_parser(
            '@{} '.format(tag_list))
        return tags

def tags_to_dict(tag_list: Union[str, bytes, bytearray],
        separator: str = ';') -> Dict[str, Union[str, bool]]:
    """
    Converts a tags list (tag1;tag2=tag-data) joined by separator to a dict
    containing strings and booleans.
    """

    if isinstance(tag_list, (bytes, bytearray)):
        if tag_list.startswith(b'@') and tag_list.endswith(b' '):
            tag_list = tag_list[1:-1]
        tag_list = tag_list.decode('utf-8', 'replace')

    return _tags_to_dict(tag_list, separator)

# Allow bytes to be passed to the message parser
_hostmask = Union[Hostmask, Tuple[str, str, str]]
def ircv3_message_parser(msg: Union[str, bytes, bytearray], *,
        colon: bool = True) -> Tuple[str, Hostmask, Dict[str, Union[str,
        bool]], List[str]]:
    """
    The same as miniirc.ircv3_message_parser, but also accepts bytes and
    bytearrays. The colon keyword argument works in the same way as the colon
    keyword argument on miniirc.Handler.

    Returns a 4-tuple: (command, hostmask, tags, args)
    """
    if isinstance(msg, (bytes, bytearray)):
        msg = msg.decode('utf-8', 'replace')

    if colon:
        return miniirc.ircv3_message_parser(msg) # type: ignore

    command, hostmask, tags, args = miniirc.ircv3_message_parser(msg)
    if args and args[-1].startswith(':'):
        args[-1] = args[-1][1:]
    return command, hostmask, tags, args # type: ignore

# Convert a hostmask to a string
def hostmask_to_str(hostmask: _hostmask) -> str:
    """ Converts a Hostmask object to a nick!user@host string. """
    if not isinstance(hostmask, Hostmask):
        raise TypeError('hostmask_to_str() expects a Hostmask object.')

    return '{}!{}@{}'.format(hostmask[0].replace('!', '_').replace('@', '_'),
        hostmask[1].replace('@', '_'), hostmask[2])

# Replace invalid RFC1459 characters with Unicode lookalikes
def _prune_arg(arg):
    if arg.startswith(':'):
        arg = '\u0703' + arg[1:]
    return arg.replace(' ', '\xa0')

# Convert miniirc-parsed messages back to IRCv2 messages
def ircv2_message_unparser(cmd: str, hostmask: _hostmask, tags: Dict[str,
        Union[str, bool]], args: List[str], *, colon: bool = True,
        encoding: Optional[str] = 'utf-8') -> Union[bytes, str]:
    """
    Converts miniirc-style message data into an IRCv2 message encoded with
    encoding (or None to return a str). When colon is False, args[-1] will have
    a colon prepended to it.
    """

    res = [] # type: list
    if hostmask and not any(i == cmd for i in hostmask):
        res.append(':{}!{}@{}'.format(*hostmask))

    # Add a unicode lookalike to cmd
    if cmd.startswith('@'):
        cmd = '\uff20' + cmd[1:]
    res.append(_prune_arg(cmd))

    # Add the arguments list
    if len(args) > 0:
        res.extend(map(_prune_arg, args[:-1]))
        if colon:
            res.append(args[-1])
        else:
            res.append(':' + args[-1])

    # Encode and strip newlines
    if not encoding:
        return ' '.join(res).replace('\r', ' ').replace('\n', ' ')

    raw = ' '.join(res).encode(encoding, 'replace') # type: bytes
    raw = raw.replace(b'\r', b' ').replace(b'\n', b' ')
    return raw

# Extend the previous function for IRCv3
def ircv3_message_unparser(cmd: str, hostmask: _hostmask, tags: Dict[str,
        Union[str, bool]], args: List[str], *, colon: bool = True,
        encoding: Optional[str] = 'utf-8') -> Union[bytes, str]:
    """ The same as ircv2_message_unparser, but IRCv3 tags are added. """
    res = ircv2_message_unparser(cmd, hostmask, tags, args, colon=colon,
        encoding=encoding)

    if not tags:
        return res
    elif isinstance(res, bytes):
        return dict_to_tags(tags) + res
    else:
        return dict_to_tags(tags).decode('utf-8', 'replace') + res

# Backwards compatibility
@deprecated(version='0.2.6', reason='Set the "colon" keyword argument to False'
    ' on irc.Handler or irc.CmdHandler instead.')
def remove_colon(func: Optional[Callable] = None) -> Callable:
    """
    Removes the leading colon (if any) from args[-1] on Handlers.
    Deprecated since miniirc_extras 0.2.6, set the "colon" keyword argument to
        False on irc.Handler or irc.CmdHandler instead.
    """

    if not func:
        return remove_colon

    # Please don't do this in your own code.
    getattr(func, '__func__', func).miniirc_colon = True

    return func

# Get the raw socket from an IRC object
def get_raw_socket(irc: AbstractIRC) -> socket.socket:
    """
    Attempts to get the raw socket from a miniirc.IRC object. This is not
    recommended, and under no circumstances should you attempt to receive data
    using this socket. Only use this if there is no alternative.

    Raises a miniirc_extras.error if no socket can be found.
    """

    if not isinstance(irc, AbstractIRC):
        raise TypeError('get_raw_socket() expects an AbstractIRC.')
    elif irc.connected is not None:
        for n in '_sock', 'sock':
            sock = getattr(irc, n, None)
            if isinstance(sock, socket.socket):
                return sock

    raise _error('Could not get a raw socket object from ' + repr(irc) + '.')

# Handle IRC URLs
_schemes = {}
def register_url_scheme(*schemes: str):
    """
    A function decorator/at-rule that allows you to register custom URL schemes.
    For examples, see utils.py.
    """

    def n(func: Callable[..., AbstractIRC]) -> Callable[..., AbstractIRC]:
        for scheme in schemes:
            _schemes[str(scheme).lower()] = func
        return func
    return n

class URLError(_error):
    pass

# A generic URL dispatcher
def irc_from_url(url: str, **kwargs) -> AbstractIRC:
    """
    Creates AbstractIRC objects based on the URL and keyword arguments provided.
    """

    if '://' not in url:
        raise URLError('Invalid URL.')
    scheme, url2 = url.split('://', 1)
    scheme = scheme.lower()
    if scheme not in _schemes:
        raise URLError('Unknown scheme ' + repr(scheme) + '.')

    return _schemes[scheme](url2, **kwargs)

# Create the default IRC schemes
_irc_scheme_re = re.compile(
    r'^(?:([^@/]+)@)?([^@/:]+)(?:\:([0-9]+))?(?:/([^\?]+))?(?:/?\?.*)?$')
@register_url_scheme('ircs')
def _ircs_scheme(url: str, ssl: Optional[bool] = True, **kwargs) \
        -> miniirc.IRC:
    match = _irc_scheme_re.match(url)
    if not match:
        raise URLError('Invalid IRC URL.')
    nick, ip, raw_port, chans = match.groups()

    nick = nick or kwargs.get('nick', '')
    if 'nick' in kwargs:
        del kwargs['nick']
    elif not nick:
        raise URLError('No nickname specified in the URL or kwargs.')

    ip   = ip
    port = 6697 # type: int
    if raw_port:
        port = int(raw_port)
    elif 'port' in kwargs:
        port = kwargs.pop('port')

    channels = set(kwargs.pop('channels', ())) # type: set
    if chans:
        for chan in chans.split(','):
            if not chan:
                continue
            elif chan[0].isalnum():
                chan = '#' + chan
            channels.add(chan)

    return miniirc.IRC(ip, port, nick, channels, ssl=ssl, **kwargs)

# irc:// and ircu://
@register_url_scheme('irc')
def _irc_scheme(url: str, ssl: Optional[bool] = None, **kwargs) -> miniirc.IRC:
    return _ircs_scheme(url, ssl=ssl, **kwargs)

@register_url_scheme('ircu')
def _ircu_scheme(url: str, port: int = 6667, ssl: Optional[bool] = False,
        **kwargs) -> miniirc.IRC:
    return _ircs_scheme(url, port=port, ssl=ssl, **kwargs)

# Because I am too lazy to put this in miniirc_discord
@register_url_scheme('discord')
def _discord_scheme(url: str, port: int = 0, **kwargs) -> AbstractIRC:
    try:
        import miniirc_discord # type: ignore
    except ImportError as e:
        raise URLError('miniirc_discord is required to handle Discord URLs.') \
            from e
    url = url.split('/', 1)[0]
    return miniirc_discord.Discord(url, 0, kwargs.pop('nick', 'unknown'),
        **kwargs)

# Handler groups
class _Handler:
    __slots__ = ('func', 'events', 'cmd_arg', 'ircv3', 'colon')

    def add_to(self, group: 'Union[AbstractIRC, HandlerGroup]') -> None:
        handler = group.CmdHandler if self.cmd_arg else group.Handler
        handler(*self.events, colon=self.colon, ircv3=self.ircv3)(self.func)

    def __init__(self, func: Callable, events: Tuple[str, ...], cmd_arg: bool,
            colon: bool, ircv3: bool) -> None:
        if len(events) == 0 and not cmd_arg:
            raise TypeError('Handler() called without arguments.')
        self.func    = func     # type: Callable
        self.events  = events   # type: Tuple[str, ...]
        self.cmd_arg = cmd_arg  # type: bool
        self.colon   = colon    # type: bool
        self.ircv3   = ircv3    # type: bool

class HandlerGroup:
    """
    Allows you to create a group of handlers and apply them in bulk to
    AbstractIRC objects.
    """

    __slots__ = ('_handlers',)

    # Generic add_handler function
    def _add_handler(self, events: Tuple[str, ...], cmd_arg: bool, colon: bool,
            ircv3: bool) -> Callable[[Callable], Callable]:
        def _finish_handler(func: Callable) -> Callable:
            self._handlers.add(_Handler(func, events, cmd_arg, colon, ircv3))
            return func

        return _finish_handler

    # User-facing Handler and CmdHandler
    def Handler(self, *events: str, colon=True, ircv3=False):
        """
        Adds a Handler to the group, uses the same syntax as irc.Handler.
        """
        return self._add_handler(events, False, colon, ircv3)

    def CmdHandler(self, *events: str, colon=True, ircv3=False):
        """
        Adds a CmdHandler to the group, uses the same syntax as irc.CmdHandler.
        """
        return self._add_handler(events, True, colon, ircv3)

    # Copy to another handler group
    def add_to(self, group: 'Union[AbstractIRC, HandlerGroup]') -> None:
        """
        Adds all the handlers in this group to an AbstractIRC object or another
        handler group.
        """
        if isinstance(group, HandlerGroup):
            group._handlers.update(self._handlers)
        elif not hasattr(group, 'Handler'):
            raise TypeError('add_to() expects a HandlerGroup-like object, not '
                + type(group).__name__)
        elif group is not self:
            for handler in self._handlers:
                handler.add_to(group)

    # Copy to a new handler group
    def copy(self) -> 'HandlerGroup':
        """ Returns a copy of the HandlerGroup. """
        group = HandlerGroup()
        group._handlers.update(self._handlers)
        return group

    # Add self._handlers
    def __init__(self):
        self._handlers = set() # type: Set[_Handler]
