#!/usr/bin/env python3
#
# irc.users: User tracking
#

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from .. import AbstractIRC, Feature, Hostmask, utils

json_types = (dict, list, tuple, str, int, float, bool, type(None)) # type: tuple
_ujson_types = Union[dict, list, tuple, str, int, float, bool, None]

# Data
class _Base:
    # Get items
    def __getitem__(self, item: str) -> _ujson_types:
        return self._data[item]

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self._data[item]
        except (IndexError, KeyError):
            return default

    # Set items
    def __setitem__(self, item: str, value: _ujson_types) -> None:
        if not isinstance(item, str):
            raise TypeError('{} data keys must be strings, not {}.'.format(
                type(self).__name__, type(item).__name__))
        elif not isinstance(value, json_types):
            raise TypeError('{} data values must be JSON serializable.'.format(
                type(self).__name__))
        self._data[item] = value

    def __delitem__(self, item: str) -> None:
        del self._data[item]

    # Allow easier iterations
    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    # Create the data dictionary
    def __init__(self) -> None:
        self._data = {} # type: Dict[str, _ujson_types]

# Abstract channels
class AbstractChannel(_Base):
    # Check if a channel contains a user
    def __contains__(self, item: Any) -> bool:
        if isinstance(item, User):
            return item in self.users
        return False

    # Add a user
    def add_user(self, user: 'User') -> None:
        if not isinstance(user, User):
            raise TypeError('add_user() requires a User.')
        elif user not in self.users:
            user.channels.add(self)
            self.users.add(user)

    # Remove a user
    def remove_user(self, user: 'User') -> None:
        if not isinstance(user, User):
            raise TypeError('remove_user() requires a User.')
        elif user in self.users:
            user.channels.remove(self)
            self.users.remove(user)

    # Get the representation
    def __repr__(self) -> str:
        return '<{} {}>'.format(type(self).__name__, repr(self.name))

    def __init__(self, name: str, topic: str = '',
            irc: Optional[AbstractIRC] = None) -> None:
        super().__init__()
        self.id    = name.lower() # type: str
        self.name  = name         # type: str
        self.topic = topic        # type: str
        self.users = set()        # type: Set[User]

Channel = AbstractChannel # type: Callable[[str, str, Optional[AbstractIRC]], AbstractChannel]

# The user class
class User(_Base):
    account = None # type: Optional[str]
    server  = None # type: Optional[str]
    current_user = False # type: bool

    # Get the hostmask
    @property
    def hostmask(self) -> Hostmask:
        return Hostmask(self.nick, self.ident, self.host)

    # Get the raw hostmask
    @property
    def raw_hostmask(self) -> str: return '{}!{}@{}'.format(*self.hostmask)

    # Iterate over self.hostmask
    def __iter__(self):
        yield from self.hostmask

    # Get items
    def __getitem__(self, item: Union[int, slice, str]) -> _ujson_types:
        if isinstance(item, (int, slice)):
            return self.hostmask[item]
        elif isinstance(item, str):
            return self._data[item]
        else:
            raise TypeError('User indicies must be integers, slices, or '
                'strings, not {}.'.format(type(item).__name__))

    # Get the representation
    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, repr(self.raw_hostmask))

    # Add the user to a channel
    def add_to_channel(self, channel: Union[str, AbstractChannel]) -> None:
        if isinstance(channel, str):
            channel = self._assert_irc().users.Channel(channel)

        if isinstance(channel, AbstractChannel):
            channel.add_user(self)
        else:
            raise TypeError('add_to_channel() requires an AbstractChannel.')

    # Remove a user from a channel
    def remove_from_channel(self, channel: Union[str, AbstractChannel]) -> None:
        if isinstance(channel, str):
            channel = self._assert_irc().users.Channel(channel)

        if isinstance(channel, AbstractChannel):
            channel.remove_user(self)
        else:
            raise TypeError('remove_from_channel() requires an'
                ' AbstractChannel.')

    # Make sure self.irc exists
    def _assert_irc(self):
        assert self._irc, repr(self) + ' has no IRC object!'
        return self._irc

    # irc.msg()
    def msg(self, *msg: str) -> None:
        return self._assert_irc().msg(self.nick, *msg)

    # irc.notice()
    def notice(self, *msg: str) -> None:
        return self._assert_irc().notice(self.nick, *msg)

    # irc.me()
    def me(self, *msg: str) -> None:
        return self._assert_irc().me(self.nick, *msg)

    # Kick the user
    def kick(self, channel: Union[AbstractChannel, str],
            reason: str = '') -> None:
        if isinstance(channel, AbstractChannel):
            channel = channel.name # type: ignore
        elif not isinstance(channel, str):
            raise TypeError('User.kick() expects an AbstractChannel or string '
                ' as the first argument.')

        self._assert_irc().quote('KICK', channel, self.nick, ':' + reason)

    def __init__(self, nick: str, ident: str = '???', host: str = '???', *,
            realname: str = '???', account: Optional[str] = None,
            irc: Optional[AbstractIRC] = None) -> None:
        super().__init__()
        self.id    = nick.lower() # type: str
        self.nick  = nick  # type: str
        self.ident = ident # type: str
        self.host  = host  # type: str
        self._irc  = irc   # type: Optional[AbstractIRC]
        self.realname = realname # type: str
        self.channels = set() # type: Set[AbstractChannel]
        self.account  = account

# The current user
class CurrentUser(User):
    current_user = True

    @property
    def id(self):
        return self._irc.nick.lower()

    @property
    def nick(self):
        return self._irc.nick

    def __setattr__(self, attr: str, value) -> None:
        if attr not in ('nick', 'id'):
            return super().__setattr__(attr, value)

    def add_to_channel(self, channel: Union[str, AbstractChannel]) -> None:
        super().add_to_channel(channel)

        chan = channel if isinstance(channel, str) else channel.id # type: str
        self._assert_irc().quote('WHO', chan)

    def remove_from_channel(self, channel: Union[str, AbstractChannel]) -> None:
        if isinstance(channel, str):
            channel = self._tracker.Channel(channel)
        super().remove_from_channel(channel)

        if channel.id in self._tracker._chans:
            self._tracker._chans[channel.id]

    def __init__(self, tracker: 'UserTracker'):
        irc = tracker._irc # type: AbstractIRC
        super().__init__(nick=irc.nick, irc=irc)
        self._tracker = tracker # type: UserTracker
        irc.quote('WHOIS', irc.nick)

# User tracker
@Feature('users')
class UserTracker:
    # Check if a user exists
    def __contains__(self, item: Union[str, Hostmask, User]) \
            -> bool:
        if isinstance(item, Hostmask):
            item = item[0]

        if isinstance(item, str):
            return item.lower() in self._users
        elif isinstance(item, User):
            return item in self._users.values()

        return False

    # Get a user
    def __getitem__(self, item: Union[str, Hostmask, User]) -> User:
        # Pass User objects through
        if isinstance(item, User):
            if item not in self._users.values():
                raise KeyError(item)
            return item

        # Handle strings
        elif isinstance(item, str):
            item = item.lower()
            if item not in self._users:
                raise KeyError(item)
            return self._users[item]

        # Handle hostmasks
        elif isinstance(item, Hostmask):
            id = item[0].lower()
            if id not in self._users:
                self._users[id] = User(*item, irc=self._irc)
                if item[2] != '???':
                    self._irc.quote('WHOIS', item[0])

            return self._users[id]

    # Get a channel
    def Channel(self, name: str, topic: str = '') -> AbstractChannel:
        id = name.lower() # type: str
        res = self._chans.get(id)
        if not res:
            res = Channel(name, topic, self._irc)
            self._chans[id] = res
        elif topic:
            res.topic = topic

        return res

    # Handle 001s
    def _handle_001(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        self._chans.clear()
        self._users.clear()
        user = CurrentUser(self) # type: CurrentUser
        self._users[user.id] = user

    # Handle JOINs
    def _chandle_join(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        user = self[hostmask] # type: User

        user.ident = hostmask[1]
        user.host  = hostmask[2]

        # Handle extended JOINs
        if 'extended-join' in irc.active_caps and len(args) > 2:
            user.realname = args[-1]

            account = args[-2] # type: str
            user.account = '' if account == '*' else account

        # Add the user to the channel
        user.add_to_channel(args[0])

    # Handle PARTs
    def _handle_part(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        self[hostmask].remove_from_channel(args[0])

    # Handle KICKs
    def _handle_kick(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        if args[1] in self:
            self[args[1]].remove_from_channel(args[0])

    # Handle QUITs (and 401s)
    def _handle_quit(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        try:
            user = self[hostmask[0]]
        except KeyError:
            return

        # Delete the user from the users list
        del self._users[user.id]

        # Remove the user from all channels
        for chan in tuple(user.channels):
            chan.remove_user(user)

    # Handle NICKs
    def _chandle_nick(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        user = self[hostmask]
        del self._users[hostmask[0].lower()]
        user.nick = args[0]
        user.id   = args[0].lower()
        self._users[user.id] = user

        # Call the handler in chans.py
        if hasattr(irc, 'chans'):
            irc.chans._handle_nick_(irc, hostmask, args) # type: ignore

    # Handle WHO replies
    def _handle_352(self, irc: AbstractIRC, _: Hostmask,
            args: List[str]) -> None:
        channel = args[1] # type: str

        user = self[Hostmask(args[5], '???', '???')] # type: User
        user.ident = args[2]
        user.host = args[3]
        user.realname = args[-1].split(' ', 1)[-1]
        user.server = args[4]

        # Call the handler in chans.py
        if hasattr(irc, 'chans'):
            irc.chans._handle_352_(irc, _, args) # type: ignore

    # Handle NAMES replies
    def _chandle_353(self, irc: AbstractIRC, hostmask: Hostmask,
            args: List[str]) -> None:
        prefixes = str(irc.isupport.get('PREFIX', '!~&@+'))
        prefixes = prefixes[1:].split(')', 1)[-1]
        for nick in args[-1].split(' '):
            nick = nick.lstrip(prefixes) # type: ignore
            if not nick:
                continue

            user = self[Hostmask(nick, '???', '???')] # type: User
            user.add_to_channel(args[-2])

        # Call the handler in chans.py
        if hasattr(irc, 'chans'):
            irc.chans._handle_353_(irc, hostmask, args) # type: ignore

    def __repr__(self):
        return '<UserTracker ' + repr(self._users) + '>'

    # Add handlers
    def __init__(self, irc: AbstractIRC) -> None:
        assert not irc.connected, 'The "users" feature must be enabled' \
            ' before connecting to IRC!'

        self._irc   = irc # type: AbstractIRC
        self._chans = {}  # type: Dict[str, AbstractChannel]
        self._users = {}  # type: Dict[str, User]

        for attr in dir(self):
            if attr.startswith('_handle_'):
                irc.Handler(attr[8:].upper())(getattr(self, attr))
            elif attr.startswith('_chandle_'):
                irc.Handler(attr[9:].upper(), colon=False)(getattr(self, attr))

        irc.Handler('401')(self._handle_quit)
