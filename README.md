# miniirc_extras

![Python 3.5+] [![Available on PyPI.]](https://pypi.org/project/miniirc_extras/) [![License: MIT]](https://github.com/luk3yx/miniirc_extras/blob/master/LICENSE.md)

[Python 3.5+]: https://img.shields.io/badge/python-3.5+-blue.svg
[Available on PyPI.]: https://img.shields.io/pypi/v/miniirc_extras.svg
[License: MIT]: https://img.shields.io/pypi/l/miniirc.svg

An extension of miniirc ([GitHub](https://github.com/luk3yx/miniirc),
[GitLab](https://gitlab.com/luk3yx/miniirc)) that adds more features.

Note that miniirc_extras is alpha-level software and should probably not be
used in production.

Some features here may be merged into miniirc eventually.

## Loading features

After importing miniirc_extras, features can be loaded with
`irc.require('feature_name')`, and once loaded can be accessed with
`irc.feature_name`.

## Features

 - `chans`: Channel mode tracking, must be loaded while miniirc is disconnected.
 - `ensure_connection`: https://github.com/luk3yx/miniirc/issues/15
 - `mp`: *(WIP)* Multiprocessing handlers for miniirc.
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

### `irc.mp`

Multiprocessing handlers. You can create multiprocessing handlers with
`irc.mp.Handler` and `irc.mp.CmdHandler`. These handlers are called with the
limited `RestrictedIRC` object (a subclass of `AbstractIRC`) instead of the
normal `IRC` object.

The following functions/variables work with `RestrictedIRC`:

`active_caps`, `channels`, `connect_modes`, `ctcp`, `debug`, `ident`, `ip`,
`ircv3_caps`, `isupport`, `me`, `msg`, `nick`, `notice`, `persist`,
`ping_interval`, `port`, `quit_message`, `quote`, `realname`, `ssl`,
`verify_ssl`

Trying to modify these variables will result in an `AttributeError` or the set
operation silently failing.

## Misc classes

### AbstractIRC

The `miniirc_extras.AbstractIRC` class provides an easy way to type check `IRC`
objects without stub files.

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
| `DummyIRC(...)`   | A subclass of `miniirc.IRC` that cannot connect to servers. `DummyIRC.__init__` has no required parameters. |
| `dict_to_tags(tags)` | Converts a dict containing strings and booleans into an IRCv3 tags string. Example: `dict_to_tags({'tag1': True, 'tag2': 'tag-data'})` → `b'@tag1;tag2=tag-data '` |
| `tags_to_dict(tag_list, separator = ';')` | Converts a tags list (`tag1;tag2=tag-data`) joined by `separator` into a `dict` containing strings and booleans. |
| `ircv3_message_parser(msg)` | The same as `miniirc.ircv3_message_parser`, but also accepts `bytes` and `bytearray`s. |
| `hostmask_to_str(hostmask)` | Converts a `Hostmask` object into a `nick!user@host` string. |
| `ircv2_message_unparser(cmd, hostmask, tags, args, *, encoding = 'utf-8')` | Converts miniirc-style message data into an IRCv2 message encoded with `encoding`. |
| `ircv3_message_unparser(cmd, hostmask, tags, args, *, encoding = 'utf-8')` | The same as `ircv2_message_unparser`, but tags are added. |
| `namedtuple(...)` | Alias for `collections.namedtuple` on Python 3.7+, otherwise a wrapper that adds `defaults` and `module` keyword arguments. |

*Note that `dict_to_tags` and `tags_to_dict` are available in miniirc as
internal functions, however they can and will change.*

### `miniirc_extras.utils.irc_from_url`

Allows you to create `IRC` objects from URLs, for example
`irc_from_url('irc://nick@ssl-server.example/#channel1,#channel2')` will create
an `IRC` object with the nickname `nick`. Any keyword arguments passed to
`irc_from_url` are sent to `IRC()`.

### `miniirc_extras.utils.HandlerGroup`

Allows you to create a group of handlers and apply them in bulk to `IRC`
objects.

| Method            | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `Handler(...)`    | Adds a `Handler` to the group, uses the same syntax as `irc.Handler`. |
| `CmdHandler(...)`    | Adds a `CmdHandler` to the group, uses the same syntax as `irc.CmdHandler`. |
| `add_to(irc_or_group)` | Adds all the handlers in this group to an IRC object or another handler group. |
| `copy()`          | Returns another handler group with the same handlers as this one. |

### `miniirc_extras.utils.numerics`

An `Enum` of most of the IRC numerics in [RFC 1459], [RFC 2812], and
[modern.ircdocs.horse](https://modern.ircdocs.horse/#numerics). See
`miniirc_extras/_numerics.py` for a list of
numerics and their names.

Example:
```py
import miniirc
from miniirc_extras.utils import numerics

@miniirc.Handler(numerics.RPL_WELCOME, colon = False)
def handler(irc, hostmask, args):
    print('Connected to IRC!')
```

Another example:
```py
>>> from miniirc_extras.utils import numerics
>>> numerics.RPL_ISUPPORT
<numerics.RPL_ISUPPORT: 0​0​5>
>>> numerics['RPL_MOTD']
<numerics.RPL_MOTD: 372>
>>> numerics(465)
<numerics.ERR_YOUREBANNEDCREEP: 465>
>>> numerics('422')
<numerics.ERR_NOMOTD: 422>
>>> str(numerics.RPL_YOURHOST)
'002'
```

### `miniirc_extras.formatting`

Text formatting. Inspired by [ircmessage](https://pypi.org/project/ircmessage/).

#### `colours`/`colors` enum

The `colours` (or `colors`) enum contains colours and their corresponding code.
Do not use these to format text, instead use the below `style` and `colorize`
functions.

#### `Styler` objects

Styler objects are callables that apply IRC formatting to strings.

```py
miniirc_extras.formatting.Styler(fg=None, bg=None, *,
        bold: bool = False, italics: bool = False, underline: bool = False,
        reverse_colour: bool = False, strikethrough: bool = False,
        spoiler: bool = False, monospace: bool = False, reset: bool = True)
```

*Note that `Styler` accepts both `reverse_colour` and `reverse_color`.*

`fg` and `bg` can be strings or values from the aforementioned `Enum`.

The parameters passed to `__init__` are available as attributes on the object,
for example `styler.bold`.

Setting `reset` to `False` is not recommended, as when enabled it only resets
any changed formatting.

For cleaner code, you can also use
`miniirc_extras.formatting.style(text, fg=None, ...)`.

**Example:**

```py
from miniirc_extras import formatting

styler = formatting.Styler('red', bold=True, monospace=True)
msg = styler('Test message')
print(styler.fg)    # <colours.red: 04>
print(styler.fg)    # None
print(styler.bold)  # True
print(repr(msg))    # '\x11\x02\x0304Test message\x0399\x02\x11'

msg2 = formatting.style('Test message', 'red', bold=True, monospace=True)
assert msg == msg2 # No error

print(repr(formatting.unstyle(msg))) # 'Test message'
```

#### "Lightweight" stylers

There are a number of predefined `Styler`s that are more efficient (if you are
only adding one style):

```py
bold            = Styler(bold=True)
italics         = Styler(italics=True)
italic          = italics
underline       = Styler(underline=True)
reverse_colour  = Styler(reverse_colour=True)
reverse_color   = reverse_colour
strikethrough   = Styler(strikethrough=True)
monospace       = Styler(monospace=True)
spoiler         = Styler(spoiler=True)
```

Lightweight stylers are subclassed from `Styler` and will run slightly faster,
provided you are only changing one style.

You can also use `miniirc_extras.formatting.colorize(text, fg)` (or
`miniirc_extras.formatting.colourise(text, fg)`) if you are only changing the
foreground colour/color for a similarly small speed improvement.

*Note that `formatting.style(text, 'red', bold=True)` is recommended over
`formatting.bold(formatting.colorize(text, 'red'))`, as it is more readable
and probably faster.*

### Deprecated functions.

These functions still work for now but will probably be removed from
miniirc_extras v1.0.0:

#### `miniirc_extras.utils.remove_colon`

This is no longer required since miniirc v1.4.0, you can simply add the
`colon` keyword argument to `Handler`s and `CmdHandler`s.

An at-rule to remove the `:` (if any) from `args[-1]` when running the handler.
This must be placed *after* `@miniirc.Handler`.

Example:

```py
# Without colon=False:
@miniirc.Handler('PRIVMSG')
def handle_privmsg(irc, hostmask, args):
    print(args) # ['#channel', ':Test message']

# Deprecated, do not use this.
@miniirc.Handler('PRIVMSG')
@miniirc_extras.utils.remove_colon
def handle_privmsg(irc, hostmask, args):
    print(args) # ['#channel', 'Test message']

# You should use this instead:
@miniirc.Handler('PRIVMSG', colon=False)
def handle_privmsg(irc, hostmask, args):
    print(args) # ['#channel', 'Test message']
```

#### `miniirc_extras.DummyIRC`

Now called `miniirc_extras.utils.DummyIRC`.

[RFC 1459]: https://tools.ietf.org/html/rfc1459
[RFC 2812]: https://tools.ietf.org/html/rfc2812
