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

import threading
from typing import Optional, Dict

from ..types import URI
from ..utils import DateTime
from ..utils import Singleton
from ..utils import http_check_m3u8

from .stream import LiveStream


class LiveStreamChecker:

    def clear_caches(self):
        pass

    # noinspection PyMethodMayBeStatic
    async def check_stream(self, stream: LiveStream, timeout: float = None) -> Optional[float]:
        return await _check_stream(stream=stream, timeout=timeout)


class LiveStreamCreator:

    # noinspection PyMethodMayBeStatic
    def create_stream(self, info: Dict = None, url: URI = None) -> Optional[LiveStream]:
        if info is None:
            assert isinstance(url, str), 'stream url error: %s' % url
            return LiveStream(url=url)
        else:
            assert isinstance(info, Dict), 'stream info error: %s' % info
            assert url is None, 'stream params error: %s, %s' % (info, url)
        # check url
        url: URI = info.get('url')
        if url is None or not isinstance(url, str):
            return None
        elif url.find(r'://') < 0:
            return None
        # OK
        return LiveStream(info=info)

    # noinspection PyMethodMayBeStatic
    def merge_stream(self, new: LiveStream, old: LiveStream) -> LiveStream:
        return _merge_stream(new=new, old=old)


@Singleton
class LiveStreamFactory:

    def __init__(self):
        super().__init__()
        self.__checker = LiveStreamChecker()
        self.__creator = LiveStreamCreator()
        # caches
        self.__streams: Dict[URI, LiveStream] = {}
        self.__lock = threading.Lock()

    def clear_caches(self):
        with self.__lock:
            self.__checker.clear_caches()
            self.__streams.clear()

    @property
    def stream_checker(self) -> LiveStreamChecker:
        return self.__checker

    @stream_checker.setter
    def stream_checker(self, checker: LiveStreamChecker):
        self.__checker = checker

    @property
    def stream_creator(self) -> LiveStreamCreator:
        return self.__creator

    @stream_creator.setter
    def stream_creator(self, creator: LiveStreamCreator):
        self.__creator = creator

    def new_stream(self, info: Dict) -> Optional[LiveStream]:
        url: str = info.get('url')
        with self.__lock:
            src = self.__streams.get(url)
            if src is None:
                src = self.stream_creator.create_stream(info=info)
                if src is not None:
                    self.__streams[url] = src
            return src

    def get_stream(self, url: URI) -> Optional[LiveStream]:
        with self.__lock:
            src = self.__streams.get(url)
            if src is None:
                src = self.stream_creator.create_stream(url=url)
                if str is not None:
                    self.__streams[url] = src
            return src

    def set_stream(self, stream: LiveStream):
        url = stream.url
        with self.__lock:
            old = self.__streams.get(url)
            if old is not None:
                self.stream_creator.merge_stream(new=stream, old=old)
            self.__streams[url] = stream


def _merge_stream(new: LiveStream, old: LiveStream) -> LiveStream:
    if new is old:
        return new
    new_time = new.time
    old_time = old.time
    if new_time is None and old_time is None:
        # neither of them were checked
        return new
    elif new_time is None:
        # copy old info
        new.set_ttl(ttl=old.ttl, now=old_time)
    elif old_time is None:
        # copy new info
        old.set_ttl(ttl=new.ttl, now=new_time)
    elif new_time < old_time:
        # copy old info
        new.set_ttl(ttl=old.ttl, now=old_time)
    elif old_time < new_time:
        # copy new info
        old.set_ttl(ttl=new.ttl, now=new_time)
    # OK
    return new


async def _check_stream(stream: LiveStream, timeout: float = None) -> Optional[float]:
    start_time = DateTime.current_timestamp()
    available = await http_check_m3u8(url=stream.url, timeout=timeout)
    end_time = DateTime.current_timestamp()
    if available:
        ttl = end_time - start_time
    else:
        ttl = None
    stream.set_ttl(ttl=ttl, now=end_time)
    return ttl
