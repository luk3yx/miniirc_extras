#!/usr/bin/env python3
#
# Miscellaneous miniirc_extras utilities
#

import miniirc
from . import Hostmask
from typing import Callable, Dict, List, Tuple, Union

__all__ = ['dict_to_tags', 'tags_to_dict', 'ircv3_message_parser',
    'hostmask_to_str', 'ircv2_message_unparser', 'ircv3_message_unparser']

# Copy "internal functions" from miniirc
dict_to_tags = miniirc._dict_to_tags
tags_to_dict = miniirc._tags_to_dict

# Allow bytes to be passed to the message parser
_hostmask = Union[Hostmask, Tuple[str, str, str]]
def ircv3_message_parser(msg: Union[str, bytes, bytearray]) -> Tuple[str,
        Hostmask, Dict[str, Union[str, bool]], List[str]]:
    if isinstance(msg, (bytes, bytearray)):
        msg = msg.decode('utf-8', 'replace')

    return miniirc.ircv3_message_parser(msg) # type: ignore

# Convert a hostmask to a string
def hostmask_to_str(hostmask: _hostmask) -> str:
    if not isinstance(hostmask, Hostmask):
        raise TypeError('hostmask_to_string() expects a Hostmask object.')

    return '{}!{}@{}'.format(hostmask[0].replace('!', '_').replace('@', '_'),
        hostmask[1].replace('@', '_'), hostmask[2])

# Replace invalid RFC1459 characters with Unicode lookalikes
def _prune_arg(arg):
    if arg.startswith(':'):
        arg = '\u0703' + arg[1:]
    return arg.replace(' ', '\xa0')

# Convert miniirc-parsed messages back to IRCv2 messages
def ircv2_message_unparser(cmd: str, hostmask: _hostmask, tags: Dict[str,
        Union[str, bool]], args: List[str], *, encoding: str = 'utf-8') \
        -> bytes:
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
        res.append(args[-1])

    # Encode and strip newlines
    raw = ' '.join(res).encode(encoding, 'replace') # type: bytes
    raw = raw.replace(b'\r', b' ').replace(b'\n', b' ')

    return raw

# Extend the previous function for IRCv3
def ircv3_message_unparser(cmd: str, hostmask: _hostmask, tags: Dict[str,
        Union[str, bool]], args: List[str], *, encoding: str = 'utf-8') \
        -> bytes:
    res = ircv2_message_unparser(cmd, hostmask, tags, args,
        encoding = encoding) # type: bytes

    if len(tags) > 0:
        res = dict_to_tags(tags) + res
    return res
