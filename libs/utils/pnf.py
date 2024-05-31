# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    PNF Helper
    ~~~~~~~~~~

"""

import re
from typing import Optional, Dict

from dimples import md5, hex_encode, utf8_encode
from dimples import URI
from dimples import PortableNetworkFile


#
#   Path Helper
#


def get_filename(path: str) -> Optional[str]:
    pos = path.find('?')
    if pos >= 0:
        path = path[:pos]  # cut query string
    pos = path.find('#')
    if pos >= 0:
        path = path[:pos]  # cut URL fragment
    # get last component
    pos = path.rfind('/')
    if pos < 0:
        pos = path.rfind('\\')
    if pos < 0:
        return path
    else:
        return path[pos+1:]


def get_extension(filename: str) -> Optional[str]:
    pos = filename.rfind('.')
    if pos < 0:
        return None
    else:
        return filename[pos+1:]


#
#   PNF Helper
#


def get_cache_name(info: Dict) -> Optional[str]:
    """ cache filename for PNF """
    pnf = PortableNetworkFile.parse(info)
    if pnf is None:
        # assert False, 'PNF error: %s' % info
        return None
    filename = pnf.filename
    url = pnf.url
    if url is None:
        return filename
    else:
        return filename_from_url(url=url, filename=filename)


def filename_from_url(url: URI, filename: Optional[str]) -> str:
    url_filename = get_filename(path=url)
    # check URL extension
    url_ext = None
    if url_filename is not None:
        url_ext = get_extension(filename=url_filename)
        if _is_encoded(filename=url_filename, ext=url_ext):
            # URL filename already encoded
            return url_filename
    # check filename extension
    ext = None
    if filename is not None:
        ext = get_extension(filename=filename)
        if _is_encoded(filename=filename, ext=ext):
            # filename already encoded
            return filename
    if ext is None:
        ext = url_ext
    # get filename from URL
    data = utf8_encode(string=url)
    filename = hex_encode(data=md5(data=data))
    if ext is None or len(ext) == 0:
        return filename
    else:
        return '%s.%s' % (filename, ext)


def filename_from_data(data: bytes, filename: str) -> str:
    # split file extension
    ext = get_extension(filename=filename)
    if _is_encoded(filename=filename, ext=ext):
        # already encoded
        return filename
    # get filename from data
    filename = hex_encode(data=md5(data=data))
    if ext is None or len(ext) == 0:
        return filename
    else:
        return '%s.%s' % (filename, ext)


def _is_encoded(filename: str, ext: Optional[str]) -> bool:
    if ext is not None and len(ext) > 0:
        pos = len(filename) - len(ext) - 1
        filename = filename[:pos]
    return len(filename) == 32 and _hex.match(filename) is not None


_hex = re.compile(r'^[\dA-Fa-f]+$')
