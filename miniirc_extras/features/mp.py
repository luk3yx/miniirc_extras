#!/usr/bin/env python3
#
# Multiprocessing wrapper for miniirc
#

import miniirc, multiprocessing as mp, queue, sys, threading, traceback
from .. import AbstractIRC, Feature, Hostmask
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

def _not_implemented(*args, **kwargs):
    raise NotImplementedError('RestrictedIRC objects do not have this '
        'function.')
_not_implemented.__name__ = _not_implemented.__qualname__ = '(not implemented)'

# Restricted IRC objects have less functions available
class RestrictedIRC(AbstractIRC):
    # Send all irc.quote() and irc.debug() messages through the Queue.
    def quote(self, *msg: str, force: Optional[bool] = None,
            tags: Optional[Dict[str, Union[str, bool]]] = None) -> None:
        if not all(isinstance(i, str) for i in msg):
            raise TypeError('irc.quote() expects all positional arguments to '
                'be strings.')
        elif self.__sendq:
            self.__sendq.put((msg, force, tags))

    def debug(self, *args, **kwargs) -> None:
        if self._debug and self.__sendq:
            self.__sendq.put((tuple(map(str, args)), kwargs))

    # Add lots of not implemented functions
    Handler = CmdHandler = connect = disconnect = _not_implemented
    finish_negotiation = change_parser = _start_handler = _not_implemented
    _handle = main = require = _not_implemented

    # Make everything read-only after __init__ finishes
    def __setattr__(self, attr, value) -> None:
        try:
            self.__sendq
        except AttributeError:
            pass
        else:
            raise AttributeError('RestrictedIRC object attribute '
                + repr(attr) +' is read-only')

        super().__setattr__(attr, value)

    # Copy attributes
    def __init__(self, orig: AbstractIRC, queue=None) -> None:
        if not isinstance(orig, AbstractIRC):
            raise TypeError('RestrictedIRC.__init__ expects an AbstractIRC.')
        self.ip = orig.ip # type: str
        self.port = orig.port # type: int
        self.nick = orig.nick # type: str
        self.channels = orig.channels # type: Set[str]
        self.ident = orig.ident # type: str
        self.realname = orig.realname # type: str
        self.ssl = orig.ssl # type: Optional[bool]
        self.persist = orig.persist # type: bool
        self.ircv3_caps = orig.ircv3_caps # type: Set[str]
        self.active_caps = orig.ircv3_caps # type: Set[str]
        self.isupport = dict(orig.isupport) # type: Dict[str, Union[str, int]]
        self.connect_modes = orig.connect_modes # type: Optional[str]
        self.quit_message = orig.quit_message or '' # type: str
        self.ping_interval = orig.ping_interval # type: int
        self.debug_file = None
        self._debug = bool(orig.debug_file) # type: bool
        self.verify_ssl = orig.verify_ssl # type: bool

        # __sendq has to be the last one set.
        self.__sendq = queue

del _not_implemented

# Multiprocessing - Don't send this or the actual IRC object to workers.
@Feature('mp')
class MultiprocessingFeature:
    _thread_obj = None # type: Optional[threading.Thread]

    # Start a handler function - Mostly copied from miniirc
    def _start_handler(self, irc: RestrictedIRC,
            handlers: List[Callable[..., None]], command: str,
            hostmask: Hostmask, tags: Dict[str, Union[str, bool]],
            args: List[str]) -> bool:
        r = False
        for handler in handlers:
            r = True
            params = [irc, hostmask, list(args)]
            if not hasattr(handler, 'miniirc_colon') and args and \
                    args[-1].startswith(':'):
                params[2][-1] = args[-1][1:] # type: ignore
            if hasattr(handler, 'miniirc_ircv3'):
                params.insert(2, dict(tags))
            if hasattr(handler, 'miniirc_cmd_arg'):
                params.insert(1, command)

            # Call the handler
            a = self._pool.apply_async(handler, params)
        return r

    # Override the handler function
    def _handle(self, cmd: str, hostmask: Hostmask, tags: Dict[str,
            Union[str, bool]], args: List[str]) -> bool:
        # Don't explode if the miniirc_extras code fails
        try:
            cmd = str(cmd).upper()
            if not isinstance(hostmask, Hostmask):
                hostmask = Hostmask(*hostmask)

            r = False  # type: bool
            irc = None # type: Optional[RestrictedIRC]
            for c in (cmd, None):
                if c in self._handlers:
                    irc = irc or RestrictedIRC(self._irc, self._queue)
                    r = self._start_handler(irc, self._handlers[c], cmd,
                        hostmask, tags, args)
        except:
            traceback.print_exc()

        res = type(self._irc)._handle(self._irc, cmd, hostmask, tags, args)
        return res or r

    def Handler(self, *events: str, colon: bool = True, ircv3: bool = False):
        args = [self._handlers, events, ircv3, False]
        if miniirc.ver >= (1,4,0):
            args.append(colon)
        return miniirc._add_handler(*args) # type: ignore

    def CmdHandler(self, *events: str, colon: bool = True, ircv3: bool = False):
        args = [self._handlers, events, ircv3, True]
        if miniirc.ver >= (1,4,0):
            args.append(colon)
        return miniirc._add_handler(*args) # type: ignore

    def _thread_raw(self) -> None:
        while self._irc.connected:
            try:
                data = self._queue.get(timeout = 30)
                if not isinstance(data, (tuple, list)):
                    pass
                elif len(data) == 2:
                    self._irc.debug(*data[0], **data[1])
                elif len(data) == 3:
                    self._irc.quote(*data[0], force=data[1], tags=data[2])
            except queue.Empty:
                pass
            except:
                traceback.print_exc()

    def _thread(self, *args) -> None:
        if not self._irc.connected or (self._thread_obj
                and self._thread_obj.is_alive()):
            return

        self._thread_obj = threading.Thread(target = self._thread_raw)
        self._thread_obj.start()

    def __init__(self, irc: AbstractIRC) -> None:
        self._irc = irc
        self._manager = manager = mp.Manager()
        self._queue = manager.Queue()
        irc._handle = self._handle # type: ignore
        self._pool = mp.Pool()
        self._handlers = {} # type: Dict[str, List[Callable[..., None]]]

        # Start the message sending thread
        irc.Handler('001')(self._thread)
        self._thread()
