# -*- coding: utf-8 -*-
#
#   TV-Box: Live Stream
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

"""
    TV Box
    ~~~~~~

    Live Stream
"""


from .stream import LiveStream
from .channel import LiveChannel
from .genre import LiveGenre

from .factory import LiveChecker, LiveCreator
from .factory import LiveFactory

from .scanner import LiveStreamScanner

from .parser import LiveParser

from .translate import LiveTranslator
# from .translate import M3UInfo
from .translate import M3UTranslator


__all__ = [

    'LiveStream', 'LiveChannel', 'LiveGenre',

    'LiveChecker', 'LiveCreator',
    'LiveFactory',

    'LiveStreamScanner',

    'LiveParser',

    'LiveTranslator',
    # 'M3UInfo',
    'M3UTranslator',

]
