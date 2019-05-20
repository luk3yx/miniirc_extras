# miniirc_extras

![Python 3.5+] [![Available on PyPI.]](https://pypi.org/project/miniirc_extras/) [![License: MIT]](https://github.com/luk3yx/miniirc_extras/blob/master/LICENSE.md)

[Python 3.5+]: https://img.shields.io/badge/python-3.5+-blue.svg
[Available on PyPI.]: https://img.shields.io/pypi/v/miniirc_extras.svg
[License: MIT]: https://img.shields.io/pypi/l/miniirc.svg

An extension of miniirc ([GitHub](https://github.com/luk3yx/miniirc),
[GitLab](https://gitlab.com/luk3yx/miniirc)) that adds more features.

Note that miniirc_extras is pre-alpha software and should not be used in
production.

Some features here may be merged into miniirc eventually.

## Loading features

After importing miniirc_extras, features can be loaded with
`irc.require('feature_name')`, and once loaded can be accessed with
`irc.feature_name`.

## Features

 - `chans`: Channel mode tracking, must be loaded while miniirc is disconnected.
 - `ensure_connection`: https://github.com/luk3yx/miniirc/issues/15
 - `testfeature`: Debugging
 - `users`: User tracking, must be loaded while miniirc is disconnected.
 - `_json` *(WIP)*: Parse JSON messages.

### `irc.users`

`irc.users` adds rudimentary user tracking to miniirc.

#### `User` objects

User objects store the current user's information and user-defined data, and
can be accessed with `irc.users[Hostmask]` or `irc.users['nick']`.

The following items are available in `User` objects:

| Variable      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `nick`        | The user's current nickname.                              |
| `ident`       | The user's current ident.                                 |
| `host`        | The user's current hostname.                              |
| `realname`    | The user's `realname`.                                    |
| `hostmask`    | A `Hostmask` object containing the user's hostmask.       |
| `raw_hostmask`| A string containing `nick!user@host`.                     |
| `channels`    | A set containing `Channel` objects for channels the user is currently in. |
| `account`     | A string containing the user's current NickServ account, or `None` if the user isn't logged in. |

You can also set and get items with strings as keys and JSON-compatible objects
as values.

`User` objects have the following helper functions:

| Function          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `msg(*text)`      | Send a `PRIVMSG` to the user.                           |
| `me(*text)`       | Send a `CTCP ACTION` (`/me`) to the user.               |
| `notice(*text)`   | Send a `NOTICE` to the user.                            |
| `kick(channel, reason = '')` | Kicks the user from `channel` (a string or `Channel` object). |

### `irc.chans`

`irc.chans` adds channel mode tracking on top of `irc.users`. You can get
channels with `irc.chans['#channel-name']`

#### `Channel` objects

`Channel` objects have the following attributes:

| Variable      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `name`        | The name of the channel.                                  |
| `modes`       | A `ModeList` object containing a list of modes.           |
| `topic`       | The channel topic.                                        |
| `users`       | A `set` containing `User` objects for members of this channel. |

#### `ModeList` objects

ModeList objects store a list of modes, and have the following functions:

| Function          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `getbool(mode)`   | Returns `True` if `mode` (a single-character string) is set on the corresponding channel. *Use this for `+i`, `+t`, etc* |
| `getstr(mode, default = None)` | Return the parameter `mode` was set with, otherwise `default`. *Use this for `+k`, `+l`, etc* |
| `getset(mode)` | Return a `frozenset` containing all the entries stored in `mode`. If you plan to use this for modes such as `+b`, you may want to run `MODE #channel +b` when the bot/client joins the channel to populate the list. *Use this for `+b`, `+e`, `+o`, `+v`, etc* |
| `hasstr(mode)` | Returns `True` if `mode` is set with a single parameter, otherwise `False`. |
| `hasset(mode)` | Equivalent to `len(getset(mode)) > 0`. |

*You can access `ModeList` objects like `dict`s, however this will require
extra type checking code if you plan to use mypy or another type checker.*

## Misc classes

### AbstractIRC

The `miniirc_extras.AbstractIRC` class provides an easy way to type check `IRC`
objects without stub files.

### DummyIRC

A subclass of `miniirc.IRC` that can't connect to servers.

### Hostmask

miniirc_extras adds the abstract-ish class `miniirc_extras.Hostmask`:

```py
from miniirc_extras import Hostmask

isinstance('test', Hostmask)                    # False
isinstance(('nick', 123, 'host'), Hostmask)     # False
isinstance(('nick', 'user', 'host'), Hostmask)  # True

Hostmask('nick', 'user', 'host') # ('nick', 'user', 'host')
Hostmask(123456, 'user', 'host') # TypeError
```

## Creating new features

*This API will probably change in the future.*

You can create your own features with `miniirc_extras.Feature`:

```py
@miniirc_extras.Feature('feature_name')
class MyFeature:
    def test_func(self):
        print('test_func called with', self._irc)

    def __call__(self):
        print('MyFeature called with', self._irc)

    def __init__(self, irc):
        self._irc = irc
```

Once registered, you can `require` and use it:

```py
irc.require('feature_name')

irc.feature_name()           # MyFeature called with <miniirc.IRC object>
irc.feature_name.test_func() # test_func called with <miniirc.IRC object>
```

## Miscellaneous functions

Some miscellaneous functions and classes are located in `miniirc_extras.utils`.

| Function          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `dict_to_tags(tags)` | Converts a dict containing strings and booleans into an IRCv3 tags string. Example: `dict_to_tags({'tag1': True, 'tag2': 'tag-data'})` → `b'@tag1;tag2=tag-data '` |
| `tags_to_dict(tag_list, separator = ';')` | Converts a tags list (`tag1;tag2=tag-data`) joined by `separator` into a `dict` containing strings and booleans. |
| `ircv3_message_parser(msg)` | The same as `miniirc.ircv3_message_parser`, but also accepts `bytes` and `bytearray`s. |
| `hostmask_to_str(hostmask)` | Converts a `Hostmask` object into a `nick!user@host` string. |
| `ircv2_message_unparser(cmd, hostmask, tags, args, *, encoding = 'utf-8')` | Converts miniirc-style message data into an IRCv2 message encoded with `encoding`. |
| `ircv3_message_unparser(cmd, hostmask, tags, args, *, encoding = 'utf-8')` | The same as `ircv2_message_unparser`, but tags are added. |

*Note that some of these functions may be available in miniirc as internal
functions, however miniirc's internal functions can and will change in the
future.*
