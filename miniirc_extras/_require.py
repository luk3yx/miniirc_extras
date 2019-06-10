#!/usr/bin/env python3
#
# miniirc_extras: require()
#

import miniirc
from . import error
from typing import Any, Callable, Dict, Optional

class FeatureNotFoundError(error):
    pass

# Add features
_c = Callable[[miniirc.IRC], Any]
_features = {} # type: Dict[str, _c]
def Feature(name: str) -> Callable[[_c], _c]:
    def res(func: _c):
        _features[str(name).lower()] = func
        return func

    return res

# Require features
def require(self, feature: str) -> _c:
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
