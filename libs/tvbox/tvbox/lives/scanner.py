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
from typing import Optional, List, Dict

import requests

from ..types import URI
from ..utils import DateTime
from ..utils import AsyncRunner as Runner
from .stream import LiveStream


class LiveStreamScanner(Runner):

    def __init__(self):
        super().__init__(interval=2)
        # caches
        self.__checkers: Dict[URI, LiveStreamChecker] = {}
        self.__queue: List[LiveStreamChecker] = []
        self.__lock = threading.Lock()
        # background thread
        thr = Runner.async_thread(coro=self.start())
        thr.start()

    # noinspection PyMethodMayBeStatic
    def _create_stream_checker(self, stream: LiveStream):
        # TODO: override for customized checker
        return LiveStreamChecker(stream=stream)

    def clear_caches(self):
        with self.__lock:
            self.__checkers.clear()

    def _get_stream_checker(self, stream: LiveStream):
        with self.__lock:
            url = stream.url
            checker = self.__checkers.get(url)
            if checker is None:
                checker = self._create_stream_checker(stream=stream)
                self.__checkers[url] = checker
            return checker

    async def scan_stream(self, stream: LiveStream, timeout: float = None) -> Optional[LiveStream]:
        """
        Check whether the stream source is available

            1. when it's available and not expired,
               return itself immediately;
            2. when it's checked before, add an update task in background thread,
               and return the stream itself immediately;
            3. otherwise, check the url, if respond nothing/error,
               return None, else return the stream.

        :param stream: live stream
        :param timeout:
        :return: None on invalid
        """
        checker = self._get_stream_checker(stream=stream)
        with self.__lock:
            if checker.is_checked():
                # this stream was checked recently,
                # no need to check again.
                is_first = False
            elif stream.time is not None:
                # this stream was checked before, but expired now; so
                # add it in the waiting queue to check it in background thread.
                self.__queue.append(checker)
                is_first = False
            else:
                # first check
                is_first = True
        if is_first:
            await checker.check(timeout=timeout)
        if stream.available:
            return stream

    # Override
    async def process(self) -> bool:
        with self.__lock:
            if len(self.__queue) == 0:
                # nothing to do now
                return False
            checker = self.__queue.pop(0)
        try:
            await checker.check(timeout=64)
        except Exception as error:
            print('[TVBox] failed to scan stream: %s, error: %s' % (checker.stream, error))


class LiveStreamChecker:

    SCAN_INTERVAL = 3600 * 2

    def __init__(self, stream: LiveStream):
        super().__init__()
        self.__stream = stream
        self.__lock = threading.Lock()

    @property
    def stream(self) -> LiveStream:
        return self.__stream

    def is_checked(self, now: float = None) -> bool:
        """ whether checked recently """
        last_time = self.stream.time
        if last_time is None:
            # never checked yet
            return False
        elif now is None:
            now = DateTime.current_timestamp()
        # check interval
        return now < (last_time + self.SCAN_INTERVAL)

    async def check(self, timeout: float = None) -> bool:
        stream = self.stream
        with self.__lock:
            if self.is_checked():
                # no need to check again now
                return True
            # check it again
            ttl = await self._check_stream(stream=stream, timeout=timeout)
            return ttl is not None and ttl > 0

    # noinspection PyMethodMayBeStatic
    async def _check_stream(self, stream: LiveStream, timeout: float = None) -> Optional[float]:
        # TODO: override for customized checking
        return await check_stream(stream=stream, timeout=timeout)


async def check_stream(stream: LiveStream, timeout: float = None) -> Optional[float]:
    start_time = DateTime.current_timestamp()
    available = await _http_check(url=stream.url, timeout=timeout)
    end_time = DateTime.current_timestamp()
    if available:
        ttl = end_time - start_time
    else:
        ttl = None
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
