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

import threading
from typing import Optional, List, Dict

from dimples import DateTime
from dimples import ID

from ...utils import Singleton
from ...utils import Config
from ...chat.base import get_nickname
from ...chat import Request, ChatRequest
from ...chat import ChatContext
from ...chat import ChatProcessor
from ...client import Monitor

from ..task import Task
from ..engine import Engine

from .box import SearchBox
from .response import VideoResponse


class SearchHandler(ChatProcessor):

    def __init__(self, engine: Engine):
        super().__init__(agent=engine.agent)
        self.__engine = engine

    # Override
    async def _query(self, prompt: str, request: Request, context: ChatContext) -> Optional[str]:
        assert isinstance(request, ChatRequest), 'request error: %s' % request
        assert isinstance(context, SearchBox), 'chat context error: %s' % context
        #
        #  0. check group
        #
        sender = request.envelope.sender
        group = request.content.group
        nickname = await get_nickname(identifier=sender, facebook=context.facebook)
        source = '"%s" %s' % (nickname, sender)
        if group is not None:
            name = await get_nickname(identifier=group, facebook=context.facebook)
            if name is None or len(name) == 0:
                source += ' (%s)' % group
            else:
                source += ' (%s)' % name
        self.info(msg='[SEARCHING] received prompt "%s" from %s' % (prompt, source))
        #
        #  1. check keywords
        #
        keywords = prompt.strip()
        if len(keywords) == 0:
            return ''
        else:
            context.cancel_task()
            # save command in history
            his_man = HistoryManager()
            his_man.add_command(cmd=keywords, when=request.time, sender=sender, group=group)
        # system commands
        if keywords in Task.CANCEL_COMMANDS:
            return ''
        #
        #  2. search
        #
        task = context.new_task(keywords=keywords, request=request)
        coro = self._search(task=task, box=context)
        # searching in background
        ok = await coro
        return '' if ok else None
        # thr = Runner.async_thread(coro=coro)
        # thr.start()
        # return True

    async def _search(self, task: Task, box: SearchBox) -> bool:
        engine = self.__engine
        # try to search by engine
        try:
            code = await engine.search(task=task)
            if code > 0:
                return True
        except Exception as error:
            self.error(msg='failed to search: %s, %s, error: %s' % (task, engine, error))
            return True
        # check error code
        if code == 0:
            tree = await box.load_video_results()
            vr = VideoResponse(request=task.request, box=box)
            await vr.respond_204(history=tree.keywords, keywords=task.keywords)
        elif code != Engine.CANCELLED_CODE:  # code != -205:
            self.error(msg='search error from engine: %d %s' % (code, engine))


@Singleton
class HistoryManager:

    MAX_LENGTH = 50

    def __init__(self):
        super().__init__()
        self.__commands: List[Dict] = []
        self.__lock = threading.Lock()

    @property
    def config(self) -> Optional[Config]:
        monitor = Monitor()
        return monitor.config

    @property
    def supervisors(self) -> List[ID]:
        conf = self.config
        if conf is not None:
            array = conf.get_list(section='admin', option='supervisors')
            if array is not None:
                return ID.convert(array=array)
        return []

    @property
    def commands(self) -> List[Dict]:
        with self.__lock:
            return self.__commands.copy()

    def add_command(self, cmd: str, when: DateTime, sender: ID, group: Optional[ID]):
        with self.__lock:
            self.__commands.append({
                'sender': sender,
                'group': group,
                'when': when,
                'cmd': cmd,
            })
