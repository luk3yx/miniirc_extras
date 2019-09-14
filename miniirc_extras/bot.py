#!/usr/bin/env python3
#
# Bot creation class
#

import collections.abc, configparser, functools, miniirc, re, sys, \
       threading, types
from typing import (Any, Callable, Dict, IO, List, Mapping, Optional, Tuple,
                    Union, overload)
from . import AbstractIRC, error, Hostmask, utils, version

__all__ = ['ConfigError', 'Bot']

class ConfigError(error):
    pass

class _NamedIRCMapping(collections.abc.Mapping):
    """
    A Mapping of named IRC objects. This class should not be created or used
    outside this module, for type hints use "Mapping[str, AbstractIRC]"
    instead of "miniirc_extras.bot._NamedIRCMapping".
    """

    __slots__ = ('_bot',)

    def __repr__(self) -> str:
        return '<Mapping {}>'.format(dict(self))

    def __getitem__(self, item):
        if isinstance(item, str):
            for irc in self._bot.ircs:
                if getattr(irc, 'name', None) == item:
                    return irc

        raise KeyError(item)

    def __iter__(self):
        for irc in self._bot.ircs:
            if hasattr(irc, 'name'):
                yield irc.name

    def __len__(self):
        return sum(1 for irc in self._bot.ircs if hasattr(irc, 'name'))

    def __init__(self, bot: 'Bot'):
        if not isinstance(bot, Bot):
            raise TypeError('_NamedIRCMapping.__init__ requires a Bot.')
        self._bot = bot

_docstring_re = re.compile(r'\s{3,}')
_cmd_type = Callable[[AbstractIRC, Hostmask, str, str], Any]
class Bot:
    """
    A multi-IRC-network Bot class.

    Example handler function (for subclasses):
    def on_privmsg(self, irc, hostmask, args):
        if args[-1].startswith('Hello'):
            irc.msg(args[0], 'Hi!')
    If you want to replace on_privmsg(), see the documentation of
    miniirc_extras.bot.Bot.on_privmsg first.

    Note that "colon" will default to "False" unless otherwise specified.
    This class will assume that AbstractIRC objects added to it will silently
    ignore duplicate handlers (similar to miniirc.IRC).

    Any method starting in "on_" will be added as a handler to all IRC objects
    (on_privmsg → Handler('PRIVMSG', colon=False)) and any method starting in
    "cmd_" will be added to the commands that are executed by the default
    "on_privmsg" function.

    Attributes:
     • prefix: The bot's command prefix.
     • config: An optional ConfigParser-like object representing the bot's
        configuration.
     • ircs: A list of IRC objects associated with this bot.
     • named_ircs: A collections.abc.Mapping of named IRC objects, only IRC
        objects with a `name` attribute will appear here.
     • lock: A threading.Lock functions use when iterating over `ircs`.
    """

    # The default bot prefix for this class.
    prefix = '$' # type: str
    config = None # type: Optional[Mapping[str, Mapping[str, str]]]

    def __add_handler(self, real_add_handler: Callable[[Callable], Callable]) \
            -> Callable[[Callable], Callable]:
        """
        Wraps add_handler so it will automatically update IRC objects.
        """
        def add_handler(func: Callable):
            func = real_add_handler(func)

            with self.lock:
                for irc in self.ircs:
                    self._handlers.add_to(irc)

            return func

        return add_handler

    def Handler(self, *events: str, colon: bool = False,
            ircv3: bool = False) -> Callable[[Callable], Callable]:
        """
        Adds `Handler`s to all IRC objects related to this `Bot`. For more
        information on handlers, see https://github.com/luk3yx/miniirc/#handlers
        or https://gitlab.com/luk3yx/miniirc/#handlers.

        Note that this function is not a classmethod, and any class-wide
        handlers should go into an on_<event> function.
        """
        return self.__add_handler(self._handlers.Handler(*events, colon=colon,
            ircv3=ircv3))

    def CmdHandler(self, *events: str, colon: bool = False,
            ircv3: bool = False) -> Callable[[Callable], Callable]:
        """
        Adds `CmdHandler`s to all IRC objects related to this `Bot`. For more
        information on handlers, see https://github.com/luk3yx/miniirc/#handlers
        or https://gitlab.com/luk3yx/miniirc/#handlers.

        Note that this function is not a classmethod, and any class-wide
        handlers should go into an on_<event> function.
        """
        return self.__add_handler(self._handlers.CmdHandler(*events,
            colon=colon, ircv3=ircv3))

    def add_irc(self, irc: Union[AbstractIRC, miniirc.IRC],
            name: Optional[str] = None) -> None:
        """
        Adds an IRC object to the bot. All bot-specific handlers will be
        automatically added to this IRC object. If the "name" parameter is
        specified, irc.name is set and this IRC object will appear in
        self.named_ircs (provided another IRC object doesn't already have the
        same name).
        """
        if not isinstance(irc, AbstractIRC):
            raise TypeError('Bot.add_irc() expects AbstractIRC objects.')

        if isinstance(name, str) and not hasattr(irc, 'name'):
            irc.name = name # type: ignore

        with self.lock:
            if irc in self.ircs:
                return

            self._handlers.add_to(irc)
            self.ircs.append(irc)

    def add_irc_from_url(self, url: str, name: Optional[str] = None,
            **kwargs) -> AbstractIRC:
        """
        Equivalent to self.add_irc(miniirc_extras.utils.irc_from_url(url)).
        """
        irc = utils.irc_from_url(url, **kwargs)
        self.add_irc(irc, name)
        return irc

    def connect(self, *, persist: bool = True) -> None:
        """
        Calls irc.connect() on all IRC objects associated with this bot.
        Setting `persist` to `True` will also set `irc.persist`.
        """

        with self.lock:
            for irc in self.ircs:
                irc.connect()
                if persist:
                    irc.persist = True

    def disconnect(self, msg: Optional[str] = None, *,
            auto_reconnect: bool = False) -> None:
        """
        Calls irc.disconnect() on all IRC objects associated with this bot.
        """
        with self.lock:
            for irc in self.ircs:
                irc.disconnect(msg, auto_reconnect=auto_reconnect)

    def require(self, feature_name: str) -> None:
        """
        Ensures that `feature_name` is available on all IRC objects associated
        with this bot.
        """
        with self.lock:
            for irc in self.ircs:
                irc.require(feature_name)

    def on_privmsg(self, irc: AbstractIRC, hostmask: Hostmask, \
            args: List[str]) -> bool:
        """
        The default PRIVMSG handler for bots. If you want to retain support
        for commands while adding a custom PRIVMSG handler, you can add
        "super().on_privmsg(irc, hostmask, args)" to the start of your
        function. This function will return True if the command has been
        handled.

        To only hande PRIVMSGs if this function can't:
        def on_privmsg(self, irc, hostmask, args):
            if super().on_privmsg(self, irc, hostmask, args):
                return True

            # Handler code here
        """
        msg = args[-1]

        # Relayed nick handling
        if msg.startswith('<'):
            n = msg.split(' ', 1)
            if n[0].endswith('>') and len(n) > 1 and msg[1].isalnum():
                _nick = n[0][1:-1]
                hostmask = Hostmask(
                    _nick + '@' + hostmask[0],
                    hostmask[1],
                    hostmask[2] + '/relayed/' + _nick
                )
                msg = n[1]

        msg = msg.strip(' \t\r\n')
        if not msg.startswith(self.prefix):
            return False

        n = msg[len(self.prefix):].split(' ', 1)
        cmd = n[0]
        if cmd not in self.commands:
            return False

        if len(n) > 1:
            param = n[1]
        else:
            param = ''

        msg = self.commands[cmd](irc, hostmask, args[0], param)
        if isinstance(msg, str):
            irc.msg(args[0], hostmask[0] + ': ' + msg)
        return True

    @overload
    def register_command(self, command: str) \
            -> Callable[[_cmd_type], _cmd_type]:
        ...

    @overload
    def register_command(self, command: str, func: _cmd_type) -> _cmd_type:
        ...

    def register_command(self, command, func=None):
        """
        Adds the command "command". Can be used as a decorator.
        Note that "func" will receive an extra "bot" argument, if you want to
        add handlers to every object in this class you should create a function
        called `cmd_commandname`.
        """
        if func is None:
            return functools.partial(self.register_command, command)

        assert callable(func)
        @functools.wraps(func)
        def cmdfunc(irc: AbstractIRC, hostmask: Hostmask, channel: str,
                param: str) -> Any:
            return func(self, irc, hostmask, channel, param)

        self.commands[command] = cmdfunc
        return func

    def get_cmd_doc(self, command: str) -> Optional[str]:
        doc = getattr(self.commands.get(command), '__doc__', None)
        if isinstance(doc, str):
            return _docstring_re.sub(' ', doc.strip()).replace('$', self.prefix)
        return None

    def cmd_help(self, irc: AbstractIRC, hostmask: Hostmask,
            channel: str, param: str) -> str:
        """
        The help command.
        Syntax: $help [command]
        """
        param = param.lstrip(' \t\r\n')
        if not param:
            return 'Available commands: ' + ', '.join(sorted(self.commands))

        if param not in self.commands:
            return 'The command {!r} does not exist!'.format(param)

        return self.get_cmd_doc(param) or \
               'No help available for {!r}'.format(param)

    def cmd_version(self, irc: AbstractIRC, hostmask: Hostmask,
            channel: str, param: str) -> str:
        """
        A basic "version" command.
        """
        return version

    @classmethod
    def main(cls, **kwargs) -> None:
        """
        A function that can be called from __main__. Keyword arguments are
        passed to argparse.ArgumentParser().
        """
        import argparse
        parser = argparse.ArgumentParser(**kwargs)
        parser.add_argument('config_file',
            help='The config file to use with this bot.')
        parser.add_argument('-V', '--version', action='version',
            version=version)
        args = parser.parse_args()

        try:
            cls.from_config(args.config_file)
        except ConfigError as e:
            print('ERROR: ' + str(e), file=sys.stderr)
            sys.exit(1)

    @classmethod
    def from_config(cls, filename: str, *,
            require: Optional[Union[Tuple[str, ...], List[str]]] = None) \
            -> 'Bot':
        """
        Reads a generic configuration from `filename` and returns a Bot object.
        "require" may be a tuple containing miniirc_extras features that will
        get require()d before connecting to IRC.

        Example config:
        [core]
        prefix = $

        [irc.network1]
        url = irc://irc.example.com/#channel1,#channel2
        nick = Test

        [irc.network2]
        ip = irc.example.com
        port = 6697
        nick = Test2
        channels = #channel1, #channel2
        """

        config = configparser.ConfigParser()
        config.read(filename)
        return cls.from_parsed_config(config, require=require)

    @classmethod
    def from_parsed_config(cls, config: Mapping[str, Mapping[str, str]], *,
            require: Optional[Union[Tuple[str, ...], List[str]]] = None) \
            -> 'Bot':
        """
        Similar to from_config(), however expects a parsed config similar to
        this dict (the config provided can be a collections.abc.Mapping if
        required):

        {
            'core': {
                'prefix': '$',
            },
            'irc.network1': {
                'url': 'irc://irc.example.com/#channel1,#channel2',
                'nick': 'Test',
            },
            'irc.network2': {
                'ip': 'irc.example.com',
                'port': '6697',
                'nick': 'Test2',
                'channels': '#channel1, #channel2',
            },
        }
        """

        prefix = None # type: Optional[str]
        if 'core' in config:
            prefix = config['core'].get('prefix')

        self = cls(prefix=prefix)
        self.config = config
        for section in config:
            if not section.startswith('irc.'):
                continue

            data = config[section]

            kwargs = {'auto_connect': False} # type: Dict[str, Any]
            # Get generic keyword arguments
            for i in 'ident', 'realname', 'ns_identity', 'connect_modes', \
                    'quit_message':
                if i in data:
                    kwargs[i] = data[i]

            # Add URL-based IRCs
            url = data.get('url') or data.get('uri')
            name = section[4:]
            if url:
                if 'nick' in data:
                    kwargs['nick'] = data['nick']
                self.add_irc_from_url(url, name, **kwargs)
                continue

            # Add "standard" IRC objects
            for i in 'ip', 'port', 'nick', 'channels':
                if i not in data:
                    raise ConfigError(('Required configuration entry {!r}'
                        ' missing!').format(i))

            try:
                port = int(data['port'])
            except ValueError as e:
                raise ConfigError("Configuration entry 'port' contains an "
                    'invalid number!') from e

            self.add_irc(miniirc.IRC(data['ip'], port, data['nick'],
                                     map(str.strip,
                                         data['channels'].split(','))), name)

        # Sanity check
        if not self.ircs:
            raise ConfigError('No IRC networks specified!')

        # Add irc.require() features.
        if require:
            for feature in require:
                self.require(feature)

        # Connect to everything
        self.connect()
        return self

    def __init__(self, *ircs: AbstractIRC, prefix: Optional[str] = None) \
            -> None:
        self.lock = threading.Lock() # type: threading.Lock
        self.named_ircs = _NamedIRCMapping(self) # type: Mapping[str, AbstractIRC]

        # Add the prefix
        if isinstance(prefix, str):
            self.prefix = prefix

        # Create handlers and commands
        hg = self._handlers = utils.HandlerGroup() # type: utils.HandlerGroup
        cmds = self.commands = {} # type: Dict[str, _cmd_type]
        for name in dir(self):
            if name.startswith('on_'):
                func = getattr(self, name, None)
                if isinstance(func, types.MethodType):
                    hg.Handler(name[3:], colon=False)(func)
            elif name.startswith('cmd_'):
                func = getattr(self, name, None)
                if callable(func):
                    cmds[name[4:]] = func

        # Add the IRC objects
        self.ircs = [] # type: List[AbstractIRC]
        for irc in ircs:
            self.add_irc(irc)

if __name__ == '__main__':
    Bot.main()
