# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Utils
    ~~~~~

    I'm too lazy to write codes for demo project, so I borrow some utils here
    from the <dimsdk> packages, but I don't suggest you to do it also, because
    I won't promise these private utils will not be changed. Hia hia~ :P
                                             -- Albert Moky @ Jan. 23, 2019
"""

from dimples.utils import *

from dimples.group.manager import find
from dimples.database.dos.document import parse_document

from .http import HttpSession, HttpClient
from .http import show_response

from .pnf import get_filename, get_extension
from .pnf import get_cache_name
from .pnf import filename_from_url, filename_from_data


def md_esc(text: str) -> str:
    if text is None:
        return ''
    elif not isinstance(text, str):
        text = str(text)
    escape = ''
    for c in text:
        if c in _md_chars:
            escape += '\\'
        escape += c
    return escape


_md_chars = {
    '\\',
    '#', '*', '_', '-', '+',
    '~', '`',
    '|', ':', '!', '.',
    '[', ']', '(', ')',
    '<', '>', '{', '}',
    '"', "'",
}


__all__ = [

    'md5', 'sha1', 'sha256', 'keccak256', 'ripemd160',
    'base64_encode', 'base64_decode', 'base58_encode', 'base58_decode',
    'hex_encode', 'hex_decode',
    'utf8_encode', 'utf8_decode',
    'json_encode', 'json_decode',

    'random_bytes',

    'Converter',

    'Runnable', 'Runner',
    'Daemon',

    'Singleton',
    'Path', 'File', 'TextFile', 'JSONFile',
    'FrequencyChecker', 'RecentTimeChecker',

    'Log', 'Logging',
    'Config',

    'is_before',
    'get_msg_sig',
    'template_replace',

    'find',

    'parse_document',

    #
    #   PNF
    #
    'get_filename', 'get_extension',
    'get_cache_name',
    'filename_from_url', 'filename_from_data',

    #
    #   HTTP
    #
    'HttpSession', 'HttpClient',
    'show_response',

    #
    #   Others
    #
    'md_esc',

]
