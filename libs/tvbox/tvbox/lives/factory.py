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
from .channel import LiveChannel
from .genre import LiveGenre


class LiveChecker:

    def clear_caches(self):
        pass

    # noinspection PyMethodMayBeStatic
    async def check_stream(self, stream: LiveStream, timeout: float = None) -> Optional[float]:
        return await _check_stream(stream=stream, timeout=timeout)


class LiveCreator:
    """ Customizable Creator """

    # noinspection PyMethodMayBeStatic
    def create_stream(self, info: Dict = None, url: URI = None, label: str = None) -> LiveStream:
        return LiveStream(info=info, url=url, label=label)

    # noinspection PyMethodMayBeStatic
    def create_channel(self, info: Dict = None, name: str = None) -> LiveChannel:
        return LiveChannel(info=info, name=name)

    # noinspection PyMethodMayBeStatic
    def create_genre(self, info: Dict = None, title: str = None) -> LiveGenre:
        return LiveGenre(info=info, title=title)


@Singleton
class LiveFactory:

    def __init__(self):
        super().__init__()
        self.__checker = LiveChecker()
        self.__creator = LiveCreator()
        # caches
        self.__streams: Dict[URI, LiveStream] = {}
        self.__lock = threading.Lock()

    def clear_caches(self):
        with self.__lock:
            self.__checker.clear_caches()
            self.__streams.clear()

    @property
    def checker(self) -> LiveChecker:
        return self.__checker

    @checker.setter
    def checker(self, delegate: LiveChecker):
        self.__checker = delegate

    @property
    def creator(self) -> LiveCreator:
        return self.__creator

    @creator.setter
    def creator(self, creator: LiveCreator):
        self.__creator = creator

    #
    #   Genre
    #

    def create_genre(self, info: Dict) -> Optional[LiveGenre]:
        title = info.get('title')
        if title is None:  # or len(title) == 0:
            return None
        return self.creator.create_genre(info=info)

    def new_genre(self, title: str) -> LiveGenre:
        # assert len(title) > 0, 'genre title should not be empty'
        return self.creator.create_genre(title=title)

    #
    #   Live Channel
    #

    def create_channel(self, info: Dict) -> Optional[LiveChannel]:
        name = info.get('name')
        if name is None or len(name) == 0:
            return None
        return self.creator.create_channel(info=info)

    def new_channel(self, name: str) -> LiveChannel:
        assert len(name) > 0, 'channel name should not be empty'
        return self.creator.create_channel(name=name)

    #
    #   Live Stream Source
    #

    def create_stream(self, info: Dict) -> Optional[LiveStream]:
        url = info.get('url')
        url = LiveStream.parse_url(url=url)
        if url is None:
            return None
        with self.__lock:
            src = self.__streams.get(url)
            if src is None:
                src = self.creator.create_stream(info=info)
                self.__streams[url] = src
            return src

    def new_stream(self, url: URI, label: Optional[str]) -> LiveStream:
        with self.__lock:
            src = self.__streams.get(url)
            if src is None:
                src = self.creator.create_stream(url=url, label=label)
                self.__streams[url] = src
            return src

    def set_stream(self, stream: LiveStream):
        url = stream.url
        with self.__lock:
            old = self.__streams.get(url)
            if old is not None:
                _merge_stream(new=stream, old=old)
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
