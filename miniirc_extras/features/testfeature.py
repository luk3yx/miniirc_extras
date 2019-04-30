#
# Test
#

from .. import Feature

print('Testing feature loaded.')

# A debug feature
@Feature('testfeature')
class TestFeature:
    def __call__(self):
        print('Test feature called on', self._irc)

    def __init__(self, irc):
        print('Test feature added to', irc)
        self._irc = irc
