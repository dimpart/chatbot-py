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

from .crypto import md5
from .crypto import utf8_encode, utf8_decode
from .crypto import hex_encode, hex_decode
from .crypto import json_encode, json_decode

from .aio import http_head, http_get
from .aio import http_get_text, http_check_m3u8

from .aio import path_parent, path_join
from .aio import text_file_read, text_file_write
from .aio import json_file_read, json_file_write

from .log import DateTime
from .log import Log, Logging

from .runner import AsyncRunner


class Singleton(object):

    __instances = {}

    def __init__(self, cls):
        self.__cls = cls

    def __call__(self, *args, **kwargs):
        cls = self.__cls
        instance = self.__instances.get(cls, None)
        if instance is None:
            instance = cls(*args, **kwargs)
            self.__instances[cls] = instance
        return instance

    def __getattr__(self, key):
        return getattr(self.__cls, key, None)


__all__ = [

    'md5',
    'utf8_encode', 'utf8_decode',
    'hex_encode', 'hex_decode',
    'json_encode', 'json_decode',

    'http_head', 'http_get',
    'http_get_text', 'http_check_m3u8',

    'path_parent', 'path_join',
    'text_file_read', 'text_file_write',
    'json_file_read', 'json_file_write',

    'DateTime',
    'Log', 'Logging',

    'AsyncRunner',

    'Singleton',

]
