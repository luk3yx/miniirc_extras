#!/usr/bin/python3
#
# miniirc_json: A proof-of-concept JSON IRC protocol thing
# This is currently alpha-level software and should not be used in production.
#
# © 2019 by luk3yx.
#

import json, miniirc
from .. import Feature

cap_name = 'luk3yx.github.io/json'

# JSON message parser
def json_parser(msg):
    # Use the standard parser if required
    if msg.startswith('@') or msg.startswith('CAP'):
        return miniirc.ircv3_message_parser(msg)

    # Parse the message
    tags = {}
    try:
        msg = json.loads(msg)
        assert type(msg) == list

        # Get the tags
        if type(msg[0]) == dict:
            tags = msg[0]
            del msg[0]

        assert len(msg) > 1
    except Exception as e:
        return e

    # Get the hostmask
    # TODO: Remove the try/except
    try:
        assert msg[0]

        if isinstance(msg[0], str):
            nick, user = msg[0].split('!', 1)
            user, host = user.split('@', 1)
            hostmask = (nick, user, host)
        elif isinstance(msg[0], (tuple, list)):
            assert len(msg[0]) == 3
            hostmask = tuple(msg[0])
        else:
            raise TypeError
    except:
        hostmask = (msg[1], msg[1], msg[1])

    # Get the args
    cmd  = msg[1]
    args = msg[2:]

    # Return the parsed data
    return cmd, hostmask, tags, args

# irc.quote() hack
def _irc_quote_hack(irc, *msg, force=None, tags=None):
    cmd, hostmask, _, args = miniirc.ircv3_message_parser(' '.join(msg))
    if cap_name not in irc.active_caps:
        irc.quote = miniirc.IRC.quote
        return miniirc.IRC.quote(irc, *msg, force=force, tags=tags)

    args.insert(0, cmd)

    if type(tags) == dict:
        args.insert(0, tags)

    args = json.dumps(args, separators=(',', ':'))
    irc.sock.sendall(args.encode('utf-8') + b'\r\n')

# Switch to JSON
def _switch_to_json(irc, hostmask, args):
    irc.quote = lambda *msg, **kw : _irc_quote_hack(irc, *msg, **kw)
    irc.change_parser(json_parser)
    irc.finish_negotiation(args[0])

# Add the feature
@Feature('_json')
def json_feature(irc):
    irc.ircv3_caps.add(cap_name)
    irc.Handler('IRCv3 ' + cap_name)(_switch_to_json)
    return cap_name
