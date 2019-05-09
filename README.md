# miniirc_extras

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

 - `ensure_connection`: https://github.com/luk3yx/miniirc/issues/15
 - `testfeature`: Debugging
 - `users`: User tracking.
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

*Note that `Channel` objects are currently a WIP and will be documented soon,
and `channel.name` is the name of the channel.*

`User` objects have the following helper functions:

| Function          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `msg(*text)`      | Send a `PRIVMSG` to the user.                           |
| `me(*text)`       | Send a `CTCP ACTION` (`/me`) to the user.               |
| `notice(*text)`   | Send a `NOTICE` to the user.                            |
| `kick(channel, reason = '')` | Kicks the user from `channel` (a string or `Channel` object). |

## Hostmask objects

miniirc_extras adds the abstract base class `miniirc_extras.Hostmask`:

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
    def test_func(self, irc):
        print('test_func called with', irc)

    def __call__(self, irc):
        print('MyFeature called with', irc)

    def __init__(self, irc):
        self._irc = irc
```

Once registered, you can `require` and use it:

```py
irc.require('feature_name')

irc.feature_name()           # MyFeature called with <miniirc.IRC object>
irc.feature_name.test_func() # test_func called with <miniirc.IRC object>
```
