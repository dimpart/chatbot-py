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

import time
from typing import Optional, Any, List, Dict
from typing import Iterable

from ..types import URI, MapInfo


def _get_time_str(timestamp: float) -> str:
    localtime = time.localtime(timestamp)
    return time.strftime('%Y-%m-%d %H:%M:%S', localtime)


class LiveStream(MapInfo):
    """ M3U8 """

    EXPIRES = 3600 * 6

    def __init__(self, info: Dict = None, url: URI = None):
        """
        Create Live Stream

        :param info: stream info
        :param url:  m3u8
        """
        super().__init__(info=info)
        if url is not None:
            self.set(key='url', value=url)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        when = self.time
        if when is not None:
            when = _get_time_str(timestamp=when)
        return '<%s time="%s" ttl=%d url="%s" />' % (cname, when, self.ttl, self.url)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        when = self.time
        if when is not None:
            when = _get_time_str(timestamp=when)
        return '<%s time="%s" ttl=%d url="%s" />' % (cname, when, self.ttl, self.url)

    @property
    def url(self) -> URI:
        """ m3u8 """
        return self.get(key='url', default='')

    @property
    def available(self) -> bool:
        ttl = self.get(key='ttl', default=0)
        return ttl > 0

    @property
    def ttl(self) -> Optional[float]:
        """ time to load (network speed) """
        return self.get(key='ttl', default=None)

    @property
    def time(self) -> Optional[time]:
        return self.get(key='time', default=None)

    def set_ttl(self, ttl: float, now: float = None):
        """ update speed """
        if now is None:
            now = time.time()
        self.set(key='ttl', value=ttl)
        self.set(key='time', value=now)

    def is_expired(self, now: float = None) -> bool:
        last_time = self.time
        if last_time is None:
            return False
        elif now is None:
            now = time.time()
        return now > (last_time + self.EXPIRES)

    #
    #   Factories
    #

    @classmethod
    def parse(cls, info: Any):  # -> Optional[LiveStream]:
        if info is None:
            return None
        elif isinstance(info, LiveStream):
            return info
        elif isinstance(info, MapInfo):
            info = info.dictionary
        if 'url' in info:
            return cls(info=info)

    @classmethod
    def convert(cls, array: Iterable[Dict]):  # -> List[LiveStream]:
        streams: List[LiveStream] = []
        for item in array:
            info = cls.parse(info=item)
            if info is not None:
                streams.append(info)
        return streams

    @classmethod
    def revert(cls, streams: Iterable) -> List[Dict]:
        array: List[Dict] = []
        for item in streams:
            if isinstance(item, MapInfo):
                array.append(item.dictionary)
        return array
