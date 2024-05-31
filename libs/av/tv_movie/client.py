# -*- coding: utf-8 -*-
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

import random
from typing import Optional, List

from dimples import ID
from dimples import Content
from dimples import TextContent
from dimples import CommonFacebook

from ...utils import Runner
from ...chat import ChatRequest
from ...chat import ChatBox, VideoBox, ChatClient
from ...chat.base import get_nickname
from ...client import Emitter
from ...client import Monitor

from .engine import Task, Engine


class SearchBox(VideoBox):
    """ Chat Box """

    def __init__(self, identifier: ID, facebook: CommonFacebook, engines: List[Engine]):
        super().__init__(identifier=identifier, facebook=facebook)
        self.__engines = engines
        self.__task: Optional[Task] = None

    def _cancel_task(self):
        task = self.__task
        if task is not None:
            self.__task = None
            self.warning(msg='cancelling task')
            task.cancel()

    def _new_task(self, keywords: str, request: ChatRequest) -> Task:
        task = Task(keywords=keywords, request=request, box=self)
        self._cancel_task()
        self.__task = task
        return task

    @property
    def service(self) -> str:
        return self.__class__.__name__

    # Override
    async def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        return await emitter.send_content(content=content, receiver=receiver)

    # Override
    async def _ask_question(self, prompt: str, content: TextContent, request: ChatRequest):
        #
        #  0. check group
        #
        sender = request.envelope.sender
        group = request.content.group
        nickname = await get_nickname(identifier=sender, facebook=self.facebook)
        source = '"%s" %s' % (nickname, sender)
        if group is not None:
            name = await get_nickname(identifier=group, facebook=self.facebook)
            if name is None or len(name) == 0:
                source += ' (%s)' % group
            else:
                source += ' (%s)' % name
        self.info(msg='[SEARCHING] received prompt "%s" from %s' % (prompt, source))
        #
        #  1. check keywords
        #
        keywords = prompt.strip()
        kw_len = len(keywords)
        if kw_len == 0:
            return
        elif kw_len == 6 and keywords.lower() == 'cancel':
            self._cancel_task()
            return
        elif kw_len == 4 and keywords.lower() == 'stop':
            self._cancel_task()
            return
        else:
            self._cancel_task()
        #
        #  2. search
        #
        task = self._new_task(keywords=keywords, request=request)
        coro = self._search(task=task)
        thr = Runner.async_thread(coro=coro)
        thr.start()

    async def _search(self, task: Task):
        all_engines = self.__engines
        count = len(all_engines)
        if count == 0:
            self.error(msg='search engines not set')
            return False
        monitor = Monitor()
        failed = 0
        index = 0
        #
        #  1. try to search by each engine
        #
        while index < count:
            engine = all_engines[index]
            try:
                code = await engine.search(task=task)
            except Exception as error:
                self.error(msg='failed to search: %s, %s, error: %s' % (task, engine, error))
                code = -500
            # check return code
            if code > 0:
                # success
                monitor.report_success(service=self.service, agent=engine.agent)
                break
            elif code == Engine.CANCELLED_CODE:  # code == -205:
                # cancelled
                return False
            elif code < 0:  # code in [-404, -500]:
                self.error(msg='search error from engine: %d %s' % (code, engine))
                monitor.report_failure(service=self.service, agent=engine.agent)
                failed += 1
            index += 1
        #
        #  2. check result
        #
        if failed == count:
            # failed to get answer
            monitor.report_crash(service=self.service)
            return False
        elif 0 < index < count:
            # move this handler to the front
            engine = self.__engines.pop(index)
            self.__engines.insert(0, engine)
            self.warning(msg='move engine position: %d, %s' % (index, engine))
        return True


class SearchClient(ChatClient):

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook
        self.__engines: List[Engine] = []

    def add_engine(self, engine: Engine):
        self.__engines.append(engine)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        # copy engines in random order
        engines = self.__engines.copy()
        count = len(engines)
        if count > 1:
            engines = random.sample(engines, count)
        return SearchBox(identifier=identifier, facebook=facebook, engines=engines)
