#! /usr/bin/env python3
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

import random
import time
from typing import Optional, List

from mkm.types import Converter


from ...utils import HttpClient, HttpSession, show_response


class SharedToken(HttpClient):
    """
        Shared Tokens
        ~~~~~~~~~~~~~

        https://chat-shared.zhile.io/api/loads
    """

    EXPIRES = 300.0  # seconds

    def __init__(self, url: str, session: HttpSession = None):
        super().__init__(session=session)
        self.__url = url
        self.__loads = None
        self.__expired = 0

    @property
    def any(self) -> Optional[dict]:
        loads = self.all
        count = len(loads)
        if count == 0:
            return None
        elif count == 1:
            return loads[0]
        elif count > 1024:
            loads = loads[:count >> 1]
        elif count >= 512:
            loads = loads[:512]
        return random.choice(loads)

    @property
    def all(self) -> List[dict]:
        cached_loads = self.__loads
        now = time.time()
        if cached_loads is not None and now < self.__expired:
            return cached_loads
        self.__expired = now + self.EXPIRES
        # request new records
        info = self.__request()
        new_loads = info.get('loads')
        if isinstance(new_loads, List):
            self.info(msg='GOT %d token(s) from URL: %s' % (len(new_loads), self.__url))
            new_loads.sort(key=comp)
            cached_loads = new_loads
            self.__loads = new_loads
        return [] if cached_loads is None else cached_loads

    def __request(self) -> dict:
        try:
            response = self.http_get(url=self.__url)
            show_response(response=response)
            return response.json()
        except Exception as e:
            self.error(msg='failed to get tokens: %s' % e)
            return {}


def comp(item: dict) -> int:
    count = item.get('count')
    return Converter.get_int(value=count, default=0)
