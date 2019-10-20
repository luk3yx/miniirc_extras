#!/usr/bin/env python3
#
# miniirc_extras.aioirc: asyncio-oriented IRC objects that are mostly
#   compatible with existing IRC objects.
#
# Copyright © 2019 by luk3yx.
#

import atexit, asyncio, functools, miniirc, ssl, threading
from typing import Dict, List, Optional, Tuple, Union
from . import AbstractIRC as _AbstractIRC
from .utils import dict_to_tags as _dict_to_tags

class _Awaitable:
    __slots__ = ('_irc', '_writer')

    async def _real_await(self):
        await self._writer.drain()

    def __await__(self):
        if self._irc and self._irc.connected is not None and self._writer:
            return self._real_await().__await__()

    def __init__(self, irc=None, writer=None):
        self._irc = irc
        self._writer = writer

class _FakeSocket:
    __slots__ = ('_irc',)

    def settimeout(self, timeout: int) -> None:
        self._irc.timeout = int(timeout)

    def __init__(self, irc) -> None:
        self._irc = irc

class AsyncIRC(miniirc.IRC):
    """
    An asyncio-based miniirc-compatible IRC class.
    """

    _pinged = False # type: bool
    _event_loop = None
    __awaitable = _Awaitable()

    def main(self):
        raise NotImplementedError
    def _main(self):
        raise NotImplementedError

    # Run a coroutine and disregard its return value.
    def _run(self, coro):
        loop = self._event_loop
        loop.call_soon_threadsafe(functools.partial(asyncio.ensure_future,
                                                    coro, loop=loop))

    # A replaced irc.quote()
    def quote(self, *msg: str, force: Optional[bool] = None, # type: ignore
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> _Awaitable:
        """
        Sends a raw message to IRC, use force=True to send while disconnected.
        Do not send multiple commands in one irc.quote(), as the newlines will
        be stripped and it will be sent as one command. The `tags` parameter
        optionally allows you to add a dict with IRCv3 message tags, and will
        not be sent to IRC servers that do not support message tags.
        """
        if not tags and msg and isinstance(msg[0], dict):
            tags = msg[0]
            msg  = msg[1:]

        if self.connected or force:
            self.debug('>3> ' + str(tags) if tags else '>>>', *msg)
            self._run(self._raw_quote(tags, ' '.join(msg), force))
        else:
            self.debug('>Q>', *msg)

            # TODO: Fix this
            if hasattr(self, 'sendq'):
                if self.sendq: # type: ignore
                    sendq = self.sendq # type: ignore
                else:
                    sendq = []
                    self.sendq = sendq # type: ignore
            elif self._sendq: # type: ignore
                sendq = self._sendq = [] # type: ignore
            else:
                sendq = []
                self._sendq = sendq = [] # type: ignore

            if isinstance(tags, dict):
                msg = (tags,) + msg # type: ignore
            sendq.append(msg)

        return self.__awaitable

    def msg(self, target: str, *msg: str, # type: ignore
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> _Awaitable:
        return self.quote('PRIVMSG', str(target), ':' + ' '.join(msg),
            tags=tags)

    def notice(self, target: str, *msg: str, # type: ignore
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> _Awaitable:
        return self.quote('NOTICE',  str(target), ':' + ' '.join(msg),
            tags=tags)

    def ctcp(self, target: str, *msg: str, reply: bool = False, # type: ignore
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> _Awaitable:
        m = (self.notice if reply else self.msg)
        return m(target, '\x01{}\x01'.format(' '.join(msg)), tags=tags)

    def me(self, target: str, *msg: str, # type: ignore
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> _Awaitable:
        return self.ctcp(target, 'ACTION', *msg, tags=tags)

    # Actually send messages
    async def _raw_quote(self, tags: Optional[Dict[str, Union[str, bool]]],
            msg: str, force: Optional[bool]) -> None:
        # Oops, the connection was lost before this function got called.
        if self.connected is None:
            if not force:
                self.quote(msg, tags=tags)
            return

        # Encode the message
        msg = msg.replace('\r', ' ').replace('\n', ' ')
        rawmsg = msg.encode('utf-8')[:self.msglen - 2] + b'\r\n'
        if isinstance(tags, dict) \
                and ('message-tags' in self.active_caps
                or   'draft/message-tags-0.2' in self.active_caps):
            rawmsg = _dict_to_tags(tags) + rawmsg

        # Send the message
        self.__writer.write(rawmsg)

    def _start_handler(self, handlers, command, hostmask, tags, args):
        r = False
        for handler in handlers:
            r = True
            params = [self, hostmask, list(args)]
            if not hasattr(handler, 'miniirc_colon') and args and \
                    args[-1].startswith(':'):
                params[2][-1] = args[-1][1:]
            if hasattr(handler, 'miniirc_ircv3'):
                params.insert(2, dict(tags))
            if hasattr(handler, 'miniirc_cmd_arg'):
                params.insert(1, command)

            if hasattr(handler, 'miniirc_coroutinefunc'):
                self._run(handler(*params))
            else:
                threading.Thread(target=handler, args=params).start()

        return r

    def Handler(self, *args, **kwargs):
        real_add_handler = super().Handler(*args, **kwargs)
        def add_handler(func):
            if asyncio.iscoroutinefunction(func):
                getattr(func, '__func__', func).miniirc_coroutinefunc = True
            return real_add_handler(func)

        return add_handler

    def CmdHandler(self, *args, **kwargs):
        real_add_handler = super().CmdHandler(*args, **kwargs)
        def add_handler(func):
            if asyncio.iscoroutinefunction(func):
                getattr(func, '__func__', func).miniirc_coroutinefunc = True
            return real_add_handler(func)

        return add_handler

    # The same as miniirc's _main() but async.
    # This could use readuntil() or readline(), however by reading lines
    #   "manually" compatibility with weird \r-only IRC servers is maintained.
    async def __main(self) -> None:
        reader = self.__reader
        self.debug('Main loop running!')
        buffer = b'' # type: bytes
        while True:
            try:
                assert len(buffer) < 65535, 'Very long line detected!'
                try:
                    raw = await asyncio.wait_for(reader.read(8192),
                                                 self.ping_interval)
                    assert raw
                    buffer += raw.replace(b'\r', b'\n')
                except asyncio.TimeoutError:
                    if self._pinged:
                        raise
                    else:
                        self._pinged = True
                        self.quote('PING', ':miniirc-ping', force=True)
            except Exception as e:
                self.debug('Lost connection!', repr(e))
                self.disconnect(auto_reconnect=True)
                while self.persist:
                    await asyncio.sleep(5)
                    self.debug('Reconnecting...')
                    try:
                        await self.async_connect()
                    except:
                        self.debug('Failed to reconnect!')
                        self.connected = None
                    else:
                        return
                return

            raw = buffer.split(b'\n') # type: ignore
            buffer = raw.pop() # type: ignore
            for line in raw:
                line = line.decode('utf-8', 'replace') # type: ignore

                if line:
                    self.debug('<<<', line)
                    try:
                        result = self._parse(line) # type: ignore
                    except:
                        result = None
                    if isinstance(result, tuple) and len(result) == 4:
                        self._handle(*result)
                    else:
                        self.debug('Ignored message:', line)
            del raw

    async def async_connect(self) -> None:
        """ Connects to the IRC server if not already connected. """

        if self.connected is not None:
            self.debug('Already connected!')
            return

        if self._event_loop is None:
            self._event_loop = asyncio.get_event_loop()

        self.connected = False
        self.debug('Connecting to', self.ip, 'port', self.port)

        self.sock = _FakeSocket(self)

        # Create an SSL context
        ctx = None # type: Optional[ssl.SSLContext]
        if self.ssl:
            if self.verify_ssl:
                ctx = ssl.create_default_context(cafile=miniirc.get_ca_certs())
                ctx.verify_mode = ssl.CERT_REQUIRED
            else:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

        # Get the stream reader and writer.
        self.__reader, self.__writer = \
            await asyncio.open_connection(self.ip, self.port, ssl=ctx)
        self.__awaitable = _Awaitable(self, self.__writer)

        # TODO: Something other than this.
        self._unhandled_caps = None
        self.quote('CAP LS 302', force=True)
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
            force=True)
        self.quote('NICK', self.nick, force=True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self._sasl = self._pinged = False

        # Call main()
        asyncio.ensure_future(self.__main())

    def connect(self) -> None:
        """
        Connects to the IRC server if not already connected.
        If you are calling this from a coroutine you should use `async_connect`
        instead.
        """
        if self._event_loop is None:
            self._event_loop = asyncio.get_event_loop()
        self._run(self.async_connect())

def _update_docstrings():
    for k in dir(AsyncIRC):
        f, f2 = getattr(AsyncIRC, k), getattr(_AbstractIRC, k, None)
        if f is not f2 and callable(f) and f.__doc__ is None and \
                f2.__doc__ is not None:
            f.__doc__ = f2.__doc__

_update_docstrings()
del _update_docstrings
