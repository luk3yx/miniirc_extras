#!/usr/bin/python3
#
# miniirc_json: A proof-of-concept JSON IRC protocol thing
# This is currently alpha-level software and should not be used in production.
#
# S: [["nick", "user", "host"], "PRIVMSG", "#channel", "Test message\nNewline"]
# S: [{"+client-tag": "tag-value"}, ["nick", "user", "host"], "PRIVMSG",
#       "#channel", "Test message."]
#
# © 2019 by luk3yx.
#

import json, miniirc
from .. import AbstractIRC, Hostmask, Feature, utils
from typing import Dict, List, Optional, Union

cap_name = 'luk3yx.github.io/json' # type: str

# JSON message parser
@Feature('_json')
class JSONParser:
    __slots__ = ('_irc',)

    def debug(self, *args, **kwargs) -> None:
        self._irc.debug('[JSON decoder]', *args, **kwargs)

    def json_parser(self, msg: str):
        # Use the standard parser if required
        if msg.startswith('@') or msg.startswith('CAP'):
            return miniirc.ircv3_message_parser(msg)

        # Parse the message
        tags = {} # type: dict
        try:
            msg = json.loads(msg)
        except json.JSONDecodeError:
            self.debug('Error decoding JSON.')
            return

        if not isinstance(msg, list) or len(msg) == 0:
            self.debug('Decoded JSON is not a list (or an empty list).')
            return

        # Get the tags
        if isinstance(msg[0], dict):
            tags = msg.pop(0)

            # Sanity check
            for k, v in tags.items():
                if not isinstance(v, (str, bool)):
                    self.debug('Invalid IRCv3 tags.')
                    tags = {}
                    break

        # Make sure the message is not too short
        if len(msg) < 2:
            self.debug('Message too short.')
            return

        # Get the hostmask
        if isinstance(msg[0], str) and '!' in msg:
            h = msg[0].split('!', 1)
            if len(h) < 2:
                h.append(h[0])
            i = h[1].split('@', 1)
            if len(i) < 2:
                i.append(i[0])
            hostmask = (h[0], i[0], i[1])
        elif isinstance(msg[0], (tuple, list)) and len(msg[0]) == 3:
            hostmask = tuple(msg[0])
        else:
            hostmask = (msg[1], msg[1], msg[1])

        # Get the args
        cmd  = msg[1]
        args = msg[2:]
        if args:
            args[-1] = ':' + args[-1]

        # Return the parsed data
        return cmd, hostmask, tags, args

    # irc.quote() hack
    def _irc_quote_hack(self, *msg, force: Optional[bool] = None,
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> None:
        irc = self._irc
        if cap_name not in irc.active_caps:
            del irc.quote
            return irc.quote(*msg, force=force, tags=tags)
        cmd, hostmask, _, args_ = miniirc.ircv3_message_parser(' '.join(msg))
        args = args_ # type: list

        if args and args[-1].startswith(':'):
            args[-1] = args[-1][1:]
        args.insert(0, cmd)
        if isinstance(tags, dict):
            args.insert(0, tags)

        rawmsg = json.dumps(args, separators=(',', ':'))
        utils.get_raw_socket(irc).sendall(rawmsg.encode('utf-8') + b'\r\n')

    # Switch to JSON
    def _switch_to_json(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        irc.quote = self._irc_quote_hack # type: ignore
        irc.change_parser(self.json_parser)
        irc.finish_negotiation(args[0])

    def __init__(self, irc: AbstractIRC) -> None:
        self._irc = irc # type: AbstractIRC
        irc.Handler('IRCv3 ' + cap_name)(self._switch_to_json)
        irc.ircv3_caps.add(cap_name)
