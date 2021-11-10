#!/usr/bin/python3
#
# irc.tracking: User and channel mode tracking
#

from __future__ import annotations
from .. import AbstractIRC, error, Feature, Hostmask
from . import users
from .users import AbstractChannel, User
from collections.abc import Callable
from typing import Any, Optional, Union

# Mode lists
class ModeList(dict):
    # Get booleans
    def getbool(self, mode: str) -> bool:
        return bool(self.get(mode, False))

    # Get frozensets
    def getset(self, mode: str) -> frozenset[str]:
        res = self.get(mode)
        if isinstance(res, set):
            return frozenset(res)
        return frozenset()

    # Get strings
    def getstr(self, mode: str, default: Optional[str] = None) \
            -> Optional[str]:
        res = self.get(mode)
        if isinstance(res, str):
            return res
        return default

    # Check if the mode list has a set
    def hasset(self, mode: str) -> bool:
        return isinstance(self.get(mode), set)

    # Check if the mode list has a string
    def hasstr(self, mode: str) -> bool:
        return isinstance(self.get(mode), str)

    # Make sure a set exists
    def _addset(self, mode: str) -> set[str]:
        if not self.hasset(mode): self[mode] = set()
        return self[mode]

    # Make sure there are no empty sets
    def _prune(self, mode: str) -> None:
        if self.hasset(mode) and len(self[mode]) == 0:
            del self[mode]

    # Update the mode list
    def add_modes(self, modes: str, params: Union[list[str], tuple[str]]) \
            -> None:
        if not isinstance(params, list):
            params = list(params)

        adding: bool = True

        # Iterate over every character
        for char in modes:
            if char == '+':
                adding = True
            elif char == '-':
                adding = False
            elif adding:
                if char in self.chanmodes[0]:
                    self._addset(char).add(params.pop(0))
                elif char in self.chanmodes[1] or char in self.chanmodes[2]:
                    self[char] = params.pop(0)
                else:
                    self[char] = True
            elif char in self.chanmodes[0]:
                if char in modes:
                    param: str = params.pop(0)
                    s: set = self._addset(char)
                    if param in s:
                        s.remove(param)
                    del param, s
            elif char in self.chanmodes[1]:
                params.pop(0)
                if char in self:
                    del self[char]
            elif char in modes:
                del self[char]

            self._prune(char)

    # Copy this ModeList
    def copy(self) -> ModeList:
        return ModeList(self._irc, super().copy())

    # Convert this ModeList to a string
    def __str__(self) -> str:
        params = ['+']

        # Sort the items list
        chars: list = list(self.items())
        chars.sort()

        # Iterate over the list
        for char, data in chars:
            if isinstance(data, set):
                for i in data:
                    params[0] += char
                    params.append(i)
                continue
            elif isinstance(data, str):
                params.append(data)

            params[0] += char

        return ' '.join(params)

    def __repr__(self) -> str:
        return '<ModeList {}>'.format(repr(str(self)))

    def __init__(self, irc: AbstractIRC,
            initial_modes: Optional[dict] = None) -> None:
        if initial_modes:
            super().__init__(initial_modes)
        else:
            super().__init__()

        self._irc: AbstractIRC = irc
        self.chanmodes = irc.chans.chanmodes # type: ignore

# Channels
class Channel(AbstractChannel):
    # Alias for add_modes
    @property
    def add_modes(self) -> Callable[[str, Union[list[str], tuple[str]]], None]:
        return self.modes.add_modes

    def __init__(self, name: str, topic: str = '',
            irc: Optional[AbstractIRC] = None) -> None:
        if not isinstance(irc, AbstractIRC):
            raise TypeError('Channel.__init__() missing 1 required'
                " keyword-only argument: 'irc'")

        super().__init__(name, topic, irc)
        self._irc: AbstractIRC = irc
        self.modes: ModeList = ModeList(irc)

users.Channel = Channel

@Feature('chans')
class ChannelTracker:
    # CHANMODES
    #   https://tools.ietf.org/html/draft-hardy-irc-isupport-00#section-4.3
    chanmodes: tuple = (frozenset(),) * 4

    # Aliases for objects defined in users.py
    @property
    def _chans(self) -> dict[str, AbstractChannel]:
        return self._users._chans

    # Check if a string is a channel.
    def is_channel(self, identifier: str) -> bool:
        if len(identifier) < 1: return False
        return identifier[0] in str(self._irc.isupport.get('CHANTYPES', '#&+'))

    # Get a channel
    def __getitem__(self, item: str) -> Channel:
        assert self.is_channel(item), 'irc.chans.__getitem__ requires a channel'
        res: AbstractChannel = self._chans[item.lower()]
        assert isinstance(res, Channel)
        return res

    def __contains__(self, item: str) -> bool:
        return self.is_channel(item) and item.lower() in self._chans

    # Handle initial channel modes
    def _handle_324(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        if len(args) < 3 or args[1] not in self:
            return
        args.pop(0)

        # Call Channel.add_modes()
        self[args.pop(0)].add_modes(args.pop(0), args)

    # Handle JOINs
    def _handle_join(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        if self._users[hostmask].current_user:
            irc.quote('MODE', args[0])

    # Handle MODEs
    def _handle_mode(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        if len(args) < 2 or args[0] not in self:
            return

        # Call Channel.add_modes()
        self[args.pop(0)].add_modes(args.pop(0), args)

    # Parse mode lists
    _mode_lists: dict[str, str] = {'367': 'b', '348': 'e', '346': 'I'}
    def _parse_mode_lists(self, irc: AbstractIRC, cmd: str, hostmask: Hostmask,
            args: list[str]) -> None:
        args.pop(0)
        self[args.pop(0)].add_modes('+' + self._mode_lists[cmd], args)

    # Handle TOPICs
    def _handle_topic(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        if args[0] in self:
            self[args[0]].topic = args[-1]

    def _handle_332(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        self._handle_topic(irc, hostmask, args[1:])

    # Spaghetti code to automatically change any status modes to the new
    #   nickname.
    def _handle_nick_(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        oldnick: str = hostmask[0].lower()
        user: User = self._users[args[0]]
        prefixes: str = str(irc.isupport.get('PREFIX', 'Yqaohv'))
        for chan in user.channels:
            if not isinstance(chan, Channel):
                continue
            for mode in chan.modes:
                if mode not in prefixes or not chan.modes.hasset(mode):
                    continue

                data: set[str] = chan.modes[mode]
                target: Optional[str] = None
                for i in data:
                    if i.lower() == oldnick:
                        target = oldnick
                        break

                if target is not None:
                    data.remove(target)
                    data.add(user.nick)

    # Handle WHO replies
    def _handle_352_(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        prefixes = self._353_prefixes
        name = ''.join(i for i in args[6] if i in prefixes) + args[5]
        self._handle_353_(irc, hostmask, [args[1], name])

    # Handle NAMES
    _353_prefixes: dict[str, str] = {}
    def _handle_353_(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        prefixes = self._353_prefixes

        chan: Channel = self._users.Channel(args[-2])
        for nick in args[-1].split(' '):
            # Get the modes
            modes = set()
            while nick and nick[0] in prefixes:
                modes.add(prefixes[nick[0]])
                nick = nick[1:]

            if not nick:
                continue

            user: User = self._users[Hostmask(nick, '???', '???')]
            user.add_to_channel(chan)

            for mode in modes:
                chan.modes.add_modes('+' + mode, [nick])

    # Get the channel modes from the ISUPPORT
    def _handle_005(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        # Get the CHANMODES isupport
        if 'CHANMODES' not in irc.isupport:
            return
        chanmodes: list[str] = str(irc.isupport['CHANMODES']).split(',', 4)

        # Sanity checks
        while len(chanmodes) < 4:
            chanmodes.append('')

        # Add channel statuses to chanmodes[0].
        prefix: str = str(irc.isupport.get('PREFIX', '(ov'))
        chanmodes[0] += prefix[1:].split(')', 1)[0]

        # Get a list with modes and their characters
        n: str = str(irc.isupport.get('PREFIX', ''))[1:]
        p: Union[list[str], tuple[str, str]] = n.split(')', 1)

        # Sanity check
        if len(p) != 2 or len(p[0]) != len(p[1]):
            p = ('Yqaohv', '!~&@%+')

        # Convert the list to a dict
        self._353_prefixes = dict((p[1][i], p[0][i]) for i in range(0,
            len(p[0])))

        # Update self.chanmodes
        self.chanmodes = tuple(map(frozenset, chanmodes))

    def __init__(self, irc: AbstractIRC) -> None:
        self._irc: AbstractIRC = irc
        assert not irc.connected, 'The "channels" feature must be enabled' \
            ' before connecting to IRC!'

        # Load the (required) users feature
        irc.require('users')
        self._users = irc.users # type: ignore

        # Add more handlers
        irc.CmdHandler(*self._mode_lists.keys())(self._parse_mode_lists)
        for attr in dir(self):
            if attr.startswith('_handle_') and not attr.endswith('_'):
                irc.Handler(attr[8:].upper(), colon=False)(getattr(self, attr))
