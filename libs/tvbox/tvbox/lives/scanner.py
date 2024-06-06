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
import time
from typing import Optional, List, Dict

import requests

from ..types import URI
from ..types import AsyncRunner as Runner
from .stream import LiveStream


class LiveStreamScanner(Runner):

    def __init__(self):
        super().__init__(interval=2)
        self.__caches: Dict[URI, LiveStream] = {}
        self.__queue: List[LiveStream] = []
        self.__lock = threading.Lock()
        # background thread
        thr = Runner.async_thread(coro=self.start())
        thr.start()

    async def scan_stream(self, stream: LiveStream) -> Optional[LiveStream]:
        """
        Check whether the stream source is available

            1. when it's available and not expired,
               return itself immediately;
            2. when it's checked before, add an update task in background thread,
               and return the stream itself immediately;
            3. otherwise, check the url, if respond nothing/error,
               return None, else return the stream.

        :param stream: live stream
        :return: None on invalid
        """
        if stream.available and not stream.is_expired():
            # no need to check again now
            return stream
        url = stream.url
        with self.__lock:
            #
            #  cache stream
            #
            old = self.__caches.get(url)
            if old is not None:
                stream = merge_stream(new=stream, old=old)
            self.__caches[url] = stream
            #
            #  check stream
            #
            if stream.available and not stream.is_expired():
                # no need to check again now
                return stream
            elif not (stream.ttl is None or stream.time is None):
                # this stream was checked before, but expired not
                # so add it in the waiting queue to check it in background thread
                self.__queue.append(stream)
            elif await check_stream(stream=stream) is None:
                # first check, failed
                return None
            # OK
            return stream

    # Override
    async def process(self) -> bool:
        # get next task
        with self.__lock:
            if len(self.__queue) > 0:
                stream = self.__queue.pop(0)
            else:
                stream = None
        if stream is None:
            return False
        # scan it
        await self.scan_stream(stream=stream)
        return True


def merge_stream(new: LiveStream, old: LiveStream) -> LiveStream:
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


async def check_stream(stream: LiveStream) -> Optional[float]:
    start_time = time.time()
    available = await _http_check(url=stream.url, timeout=64)
    if available:
        end_time = time.time()
        ttl = end_time - start_time
        stream.set_ttl(ttl=ttl, now=end_time)
        return ttl


async def _http_check(url: URI, timeout: float = None, is_m3u8: bool = None) -> bool:
    if is_m3u8 is None and url.lower().find('m3u8') > 0:
        is_m3u8 = True
    try:
        response = requests.head(url, timeout=timeout)
        status_code = response.status_code
        if status_code == 302:
            redirected_url = response.headers.get('Location')
            return await _http_check(url=redirected_url, is_m3u8=is_m3u8, timeout=timeout)
        elif status_code != 200:
            # HTTP error
            return False
        elif is_m3u8:
            return True
        # check content type
        content_type = response.headers.get('Content-Type')
        content_type = '' if content_type is None else str(content_type).lower()
        if content_type.find('application/vnd.apple.mpegurl') >= 0:
            return True
        elif content_type.find('application/x-mpegurl') >= 0:
            return True
    except Exception as error:
        print('[TVBox] failed to query URL: %s, error: %s' % (url, error))
    return False
