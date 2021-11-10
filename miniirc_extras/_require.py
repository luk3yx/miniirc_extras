#!/usr/bin/env python3
#
# miniirc_extras: require()
#

from __future__ import annotations
import miniirc
from . import error
from collections.abc import Callable
from typing import Any, Optional, Union

class FeatureNotFoundError(error):
    pass

# Add features
_c = Union['Callable[[miniirc.IRC], Any]']
_features: dict[str, _c] = {}
def Feature(name: str) -> Callable[[_c], _c]:
    def res(func: _c):
        _features[str(name).lower()] = func
        return func

    return res

# Require features
def require(self, feature: str) -> Any:
    """
    Loads a miniirc_extras feature and returns the feature object.
    Once loaded, features can also be accessed with `irc.feature_name`.

    Features must be loaded for every IRC object they are used on.
    """

    if hasattr(self, feature):
        return getattr(self, feature)
    elif feature not in _features:
        raise FeatureNotFoundError('The feature {} was not found.'.format(
            repr(feature)
        ))

    # Add the feature
    res = _features[feature](self)
    setattr(self, feature, res)

    self.debug('Feature', feature, 'loaded.')
    return res

# Add require() to all IRC objects
miniirc.IRC.require = require
