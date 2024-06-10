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
from typing import Optional, List

from ..utils import DateTime
from ..utils import AsyncRunner as Runner
from .stream import LiveStream


class LiveStreamScanner(Runner):

    def __init__(self):
        super().__init__(interval=2)
        # caches
        self.__queue: List[LiveStream] = []
        self.__lock = threading.Lock()
        # background thread
        thr = Runner.async_thread(coro=self.start())
        thr.start()

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
        now = DateTime.current_timestamp()
        with self.__lock:
            if not stream.is_expired(now=now):
                # this stream was checked recently,
                # no need to check again.
                is_first = False
            elif stream.time is not None:
                # this stream was checked before, but expired now; so
                # add it in the waiting queue to check it in background thread.
                self.__queue.append(stream)
                is_first = False
            else:
                # first check
                is_first = True
        if is_first:
            await stream.check(now=now, timeout=timeout)
        if stream.available:
            return stream

    # Override
    async def process(self) -> bool:
        with self.__lock:
            if len(self.__queue) == 0:
                # nothing to do now
                return False
            stream = self.__queue.pop(0)
        try:
            await stream.check(timeout=64)
        except Exception as error:
            print('[TVBox] failed to scan stream: %s, error: %s' % (stream, error))
