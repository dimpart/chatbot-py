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

import hashlib
import json
from typing import Optional, Union, List, Dict


def hex_md5(data: Union[bytes, str]) -> str:
    if isinstance(data, str):
        data = utf8_encode(string=data)
    return hex_encode(data=md5_digest(data=data))


def md5_digest(data: bytes) -> bytes:
    hash_obj = hashlib.md5()
    hash_obj.update(data)
    return hash_obj.digest()


def utf8_encode(string: str) -> bytes:
    return string.encode('utf-8')


def utf8_decode(data: bytes) -> Optional[str]:
    return data.decode('utf-8')


def hex_encode(data: bytes) -> str:
    # return binascii.b2a_hex(data).decode('utf-8')
    return data.hex()


def hex_decode(string: str) -> Optional[bytes]:
    # return binascii.a2b_hex(string)
    return bytes.fromhex(string)


def json_encode(container: Union[Dict, List]) -> str:
    return json.dumps(container)


def json_decode(text: str) -> Union[Dict, List, None]:
    text = purify_json(text=text)
    try:
        return json.loads(text)
    except json.decoder.JSONDecodeError as jse:
        print('JSON failed to decode: %s, error: %s' % (text, jse))


def purify_json(text: str) -> str:
    lines = text.splitlines()
    index = len(lines)
    while index > 0:
        index -= 1
        text = lines[index].lstrip()
        if text.startswith('#') or text.startswith('//'):
            lines.pop(index)
    return '\n'.join(lines)
