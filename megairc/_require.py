#!/usr/bin/env python3
#
# megairc: require()
#

import miniirc
from . import error

class FeatureNotFoundError(error):
    pass

# Add features
_features = {}
def Feature(name):
    def res(func):
        _features[str(name).lower()] = func
        return func

    return res

# Require features
def _require(self, feature):
    if hasattr(self, feature):
        return
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
miniirc.IRC.require = _require
