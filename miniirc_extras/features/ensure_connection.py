#!/usr/bin/env python3
#
# irc.ensure_connection: Decreases the ping interval temporarily
#

from __future__ import annotations
import threading
from .. import AbstractIRC, error, Feature, Hostmask
from ..utils import get_raw_socket
from typing import Optional

class NotConnectedError(error):
    pass

_ping_arg: str = 'miniirc_extras-connection_ensurer'

# The ensure_connection feature
@Feature('ensure_connection')
class ConnectionEnsurer:
    _new_interval: int = 2
    _old_interval: Optional[int] = None
    _managers: int = 0

    # Handle new contexts
    def __enter__(self) -> None:
        irc, interval = self._irc, self._new_interval

        # Make sure irc.connected is True.
        if not irc.connected:
            raise NotConnectedError('You are not connected to IRC!')

        # Back up the current ping interval
        if self._old_interval is None:
            self._old_interval = irc.ping_interval

        # Change the ping interval
        get_raw_socket(irc).settimeout(interval)

        # Wait for a PONG - This also makes the new ping interval work
        self._managers += 1
        try:
            self._event.clear()
            irc.quote('PING', ':' + _ping_arg)

            # Raise an error
            if not self._event.wait(interval):
                raise NotConnectedError('PING timeout!')

            self._event.clear()
        except:
            self.__exit__(1, 1, 1)
            raise

    # Handle leaving a context
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._managers > 0:
            self._managers -= 1

        if not self._managers:
            try:
                get_raw_socket(self._irc).settimeout(self._old_interval)
            except error:
                pass

    # Set the new interval
    def __call__(self, interval: int = 2):
        if not isinstance(interval, (int, float)) or interval < 1:
            raise ValueError(
                'irc.ensure_connection() interval must be at least 1.'
            )

        self._new_interval = interval
        return self

    # Handle PONGs
    def _handle_pong(self, irc: AbstractIRC, hostmask: Hostmask,
            args: list[str]) -> None:
        if args and args[-1] == _ping_arg and self._managers:
            self._event.set()

    # Create new irc.ensure_connection() instances for IRC objects.
    def __init__(self, irc: AbstractIRC) -> None:
        self._event = threading.Event()
        self._irc   = irc
        irc.Handler('PONG', colon=False)(self._handle_pong)
