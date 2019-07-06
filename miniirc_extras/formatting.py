#!/usr/bin/env python3
#
# miniirc_extras: IRC formatting
#
# References: https://github.com/myano/jenni/wiki/IRC-String-Formatting
#             https://modern.ircdocs.horse/formatting.html#characters
#
# Inspired by https://pypi.org/project/ircmessage/.
#

import enum, re
from typing import Optional, Tuple, Union

class _Code(int):
    __slots__ = ()
    def __str__(self) -> str:
        return super().__repr__().zfill(2)
    __repr__ = __str__

    def __call__(self, text: str) -> str:
        return '\x03{}{}\x0399'.format(self, text)

    def __eq__(self, other) -> bool:
        return int(self) == other or str(self) == other

    def __ne__(self, other) -> bool:
        return int(self) != other and str(self) != other

class _CodeEnum(_Code, enum.Enum):
    __slots__ = ()
    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def _missing_(cls, value) -> '_CodeEnum':
        if isinstance(value, (int, str)) and not isinstance(value, _Code):
            try:
                return cls(_Code(value))
            except ValueError:
                pass

        raise ValueError(repr(value) + ' is not a valid IRC colour/color code.')

class colours(_CodeEnum):
    white       =  0
    black       =  1
    blue        =  2
    green       =  3
    red         =  4
    brown       =  5
    purple      =  6
    orange      =  7
    yellow      =  8
    light_green =  9
    lime        =  9
    teal        = 10
    cyan        = 10
    light_cyan  = 11
    light_blue  = 12
    pink        = 13
    grey        = 14
    gray        = 14
    light_grey  = 15
    light_gray  = 15
    default     = 99 # Not supported on all clients

colors = colours

class _StrEnum(str, enum.Enum):
    def __str__(self) -> str:
        return str(self.value)

class _codes(_StrEnum):
    bold = '\x02'
    italic = '\x1d'
    italics = '\x1d'
    underline = '\x1f'
    reverse_colour = '\x16'
    reverse_color = '\x16'
    reset = '\x0f' # Not actually used

    # These characters are not supported by some/most clients.
    strikethrough = '\x1e'
    monospace = '\x11'

    # I don't know if this works in any client yet.
    spoiler = '\x0301,01'

def _get_code(c: Union[colours, str]) -> colours:
    if isinstance(c, str):
        return colours[c]
    elif isinstance(c, colours):
        return c

    raise TypeError('Invalid colour/color.')

# Slightly faster than style() when only setting a foreground.
_col = Union[colours, str]
def colorize(text: str, fg: _col) -> str:
    return _get_code(fg)(text)

colourise = colorize

# Stylers
_ocol = Optional[_col]
class Styler:
    __slots__ = ('fg', 'bg', 'bold', 'italics', 'underline', 'reverse_color',
        'reverse_colour', 'strikethrough', 'spoiler', 'monospace', 'reset')

    # Add a control character to text
    def _wrap(self, text: str, char: str) -> str:
        if not self.reset:
            return char + text
        elif char.startswith('\x03'):
            if ',' in char:
                return char + text + '\x0399,99'
            else:
                return char + text + '\x0399'

        return char + text + char

    def __call__(self, text: str) -> str:
        text = str(text)

        if self.reverse_colour:
            text = self._wrap(text, _codes.reverse_colour)

        if self.bg:
            text = self._wrap(text, '\x03{},{}'.format(self.fg
                or colours.default, self.bg))
        elif self.fg:
            text = self._wrap(text, '\x03' + str(self.fg))

        if self.bold:
            text = self._wrap(text, _codes.bold)
        if self.italics:
            text = self._wrap(text, _codes.italics)
        if self.underline:
            text = self._wrap(text, _codes.underline)
        if self.strikethrough:
            text = self._wrap(text, _codes.strikethrough)
        if self.spoiler:
            text = _codes.spoiler + text + _codes.spoiler
        if self.monospace:
            text = self._wrap(text, _codes.monospace)

        return text

    def __init__(self, fg: _ocol = None, bg: _ocol = None, *,
            bold: bool = False, italics: bool = False, underline: bool = False,
            reverse_colour: bool = False, reverse_color: bool = False,
            strikethrough: bool = False, spoiler: bool = False,
            monospace: bool = False, reset: bool = True):
        self.fg = None # type: Optional[colours]
        self.bg = None # type: Optional[colours]

        if fg:
            self.fg = _get_code(fg)
        if bg:
            self.bg = _get_code(bg)

        self.bold = bold # type: bool
        self.italics = italics # type: bool
        self.underline = underline # type: bool
        self.reverse_colour = reverse_colour or reverse_color # type: bool
        self.reverse_color = self.reverse_colour # type: bool
        self.strikethrough = strikethrough # type: bool
        self.spoiler = spoiler # type: bool
        self.monospace = monospace # type: bool
        self.reset = reset # type: bool

# Lightweight stylers
class _LightweightStyler(Styler):
    __slots__ = ('name', 'char')

    def __repr__(self) -> str:
        return '<Styler object: {} {}>'.format(self.name,
            repr(str(self.char)))

    def __call__(self, text: str) -> str:
        return self.char + str(text) + self.char

    def __init__(self, name: str, char: Optional[str] = None):
        self.name = name # type: str
        if char is None:
            char = _codes[name]
        assert isinstance(char, str)
        self.char = char # type: str

        kwargs = {}
        if name in Styler.__slots__:
            kwargs[name] = True
        super().__init__(**kwargs) # type: ignore

# Create a few lightweight stylers
bold            = _LightweightStyler('bold')
italics         = _LightweightStyler('italics')
italic          = italics
underline       = _LightweightStyler('underline')
reverse_colour  = _LightweightStyler('reverse_colour')
reverse_color   = reverse_colour
strikethrough   = _LightweightStyler('strikethrough')
monospace       = _LightweightStyler('monospace')
spoiler         = _LightweightStyler('spoiler')

# Create a nicer function
def style(text: str, fg: _ocol = None, bg: _ocol = None, *,
        bold: bool = False, italics: bool = False, underline: bool = False,
        reverse_colour: bool = False, reverse_color: bool = False,
        strikethrough: bool = False, spoiler: bool = False,
        monospace: bool = False, reset: bool = True) -> str:
    styler = Styler(fg, bg, bold=bold, italics=italics, underline=underline,
        reverse_colour=reverse_colour, reverse_color=reverse_color,
        strikethrough=strikethrough, spoiler=spoiler, monospace=monospace,
        reset=reset)
    return styler(text)

# Remove all formatting from text
_unstyle_re = None
def unstyle(text: str) -> str:
    global _unstyle_re
    if not _unstyle_re:
        _unstyle_re = re.compile(r'\x03([0-9]{1,2})?(,[0-9]{1,2})?|['
            + ''.join(code for code in _codes if len(code) == 1) + ']')

    return _unstyle_re.sub('', text)
