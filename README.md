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
 - `_json` *(WIP)*: Parse JSON messages.

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
