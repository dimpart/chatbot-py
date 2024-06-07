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

import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Coroutine


class AsyncRunner(ABC):
    """ Daemon Runner """

    def __init__(self, interval: float):
        super().__init__()
        assert interval > 0, 'interval error: %s' % interval
        self.__interval = interval
        self.__running = False

    @property
    def interval(self) -> float:
        return self.__interval

    @property
    def running(self) -> bool:
        return self.__running

    async def start(self):
        self.__running = True
        await self.run()

    async def stop(self):
        self.__running = False

    # protected
    async def run(self):
        while self.running:
            try:
                ok = await self.process()
            except Exception as error:
                print('[TVBox] process failed: %s' % error)
                ok = False
            if ok:
                # runner is busy, return True to go on.
                continue
            else:
                # if nothing to do now, return False here
                # to let the thread have a rest.
                await self._idle()

    @abstractmethod  # protected
    async def process(self) -> bool:
        raise NotImplemented

    # protected
    async def _idle(self):
        await self.sleep(seconds=self.interval)
        # time.sleep(self.interval)

    @classmethod
    async def sleep(cls, seconds: float):
        await asyncio.sleep(seconds)

    @classmethod
    def sync_run(cls, main: Coroutine):
        """ Run main coroutine until complete """
        return asyncio.run(main)

    @classmethod
    def async_task(cls, coro: Coroutine) -> asyncio.Task:
        """ Create an async task to run the coroutine """
        return asyncio.create_task(coro)

    @classmethod
    def async_thread(cls, coro: Coroutine) -> threading.Thread:
        """ Create a daemon thread to run the coroutine """
        return threading.Thread(target=cls.sync_run, args=(coro,), daemon=True)
