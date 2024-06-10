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

from typing import Optional, Union, Tuple, List, Dict, Mapping

import aiohttp
from aiou import Path, TextFile

from ..types import URI
from .crypto import json_encode, json_decode
from .log import Log


#
#   HTTP
#

async def http_head(url: URI, allow_redirects: bool = False, timeout: float = None) -> Tuple[int, Mapping]:
    """ Get HTTP status and headers """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url=url, allow_redirects=allow_redirects, timeout=timeout) as response:
                return response.status, response.headers
    except Exception as error:
        Log.error(msg='failed to head URL: %s, error: %s' % (url, error))
        return 404, {}


async def http_get(url: URI, allow_redirects: bool = False, timeout: float = None) -> Optional[bytes]:
    """ Get data from URL """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, allow_redirects=allow_redirects, timeout=timeout) as response:
                return await response.read()
    except Exception as error:
        Log.error(msg='failed to get URL: %s, error: %s' % (url, error))


async def http_get_text(url: URI, timeout: float = None, encoding: str = 'utf-8') -> Optional[str]:
    """ Get text from URL """
    Log.info(msg='http get text: %s' % url)
    data = await http_get(url=url, allow_redirects=True, timeout=timeout)
    if data is not None:
        return data.decode(encoding=encoding)


async def http_check_m3u8(url: URI, timeout: float = None) -> bool:
    """ Check M3U8 for URL """
    m3u8 = await _http_check(url=url, timeout=timeout)
    if not m3u8:
        Log.warning(msg='this url is not available: %s' % url)
    return m3u8


async def _http_check(url: URI, is_m3u8: bool = None, timeout: float = None) -> bool:
    if is_m3u8 is None and url.lower().find('m3u8') > 0:
        is_m3u8 = True
    status_code, headers = await http_head(url=url, timeout=timeout)
    # check status code
    if status_code == 302 or status_code == 301:
        # redirect
        redirected_url = headers.get('Location')
        return await _http_check(url=redirected_url, is_m3u8=is_m3u8, timeout=timeout)
    elif status_code != 200:
        # HTTP error
        return False
    elif is_m3u8:
        return True
    # check content type
    content_type = headers.get('Content-Type')
    content_type = '' if content_type is None else str(content_type).lower()
    if content_type.find('application/vnd.apple.mpegurl') >= 0:
        return True
    elif content_type.find('application/x-mpegurl') >= 0:
        return True
    Log.warning(msg='this is not a m3u8 url: %s' % url)
    return False


#
#   File
#


def path_parent(path: str) -> str:
    return Path.dir(path=path)


def path_join(parent: str, *children: str) -> str:
    return Path.join(parent, *children)


async def text_file_read(path: str) -> Optional[str]:
    try:
        return await TextFile(path=path).read()
    except Exception as error:
        Log.error(msg='failed to read file: %s, error: %s' % (path, error))


async def text_file_write(text: str, path: str) -> bool:
    try:
        return await TextFile(path=path).write(text=text)
    except Exception as error:
        Log.error(msg='failed to write file: %s (%d bytes), error: %s' % (path, len(text), error))


async def json_file_read(path: str) -> Union[Dict, List, None]:
    text = await text_file_read(path=path)
    if text is None or len(text) < 2:
        return None
    return json_decode(text=text)


async def json_file_write(container: Union[Dict, List], path: str) -> bool:
    text = json_encode(container=container)
    return await text_file_write(text=text, path=path)
