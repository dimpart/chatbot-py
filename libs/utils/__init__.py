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

from typing import List

from dimples.utils import *
from dimples.utils.http import Response, fetch_cookies

from dimples.group.manager import find
from dimples.database.dos.document import parse_document

from .pnf import get_filename, get_extension
from .pnf import get_cache_name
from .pnf import filename_from_url, filename_from_data


def zigzag_reduce(array: List[List]) -> List:
    snake = []
    #
    #  check size
    #
    h = len(array)
    w = 0
    for line in array:
        s = len(line)
        if s > w:
            w = s
    n = w + h - 1
    #
    #  traverse
    #
    x = 0
    y = 0
    while x < n and y < n:
        # pick up existing item
        if y < len(array):
            line = array[y]
            if x < len(line):
                snake.append(line[x])
        # move pointers to next position
        if y == 0:
            # next slash
            y = x + 1
            x = 0
        else:
            x = x + 1
            y = y - 1
    #############################################
    #                                           #
    #   0 1 2 3                                 #
    #   4 5         =>    0 4 1 6 5 2 7 3 8 9   #
    #   6 7 8 9                                 #
    #                                           #
    #############################################
    return snake


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


def show_response(response: Response):
    status_code = response.status_code
    text = response.text
    Log.info(msg='[HTTP]\t> response: code=%d, len=%d' % (status_code, len(text)))
    Log.debug(msg='[HTTP]\t> response: %d, %s' % (status_code, text))
    Log.info(msg='[HTTP]\t> cookies: %s' % fetch_cookies(response=response))


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
    'zigzag_reduce',

    'md_esc',

]
