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
from ..video import VideoBox

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
        kw_len = len(keywords)
        if kw_len == 0:
            return ''
        else:
            context.cancel_task()
            # save command in history
            his_man = HistoryManager()
            his_man.add_command(cmd=keywords, when=request.time, sender=sender, group=group)
        # system commands
        if kw_len == 6 and keywords.lower() == 'cancel':
            return ''
        elif kw_len == 4 and keywords.lower() == 'stop':
            return ''
        elif kw_len == 12 and keywords.lower() == 'show history':
            #
            #  search history
            #
            vr = VideoResponse(request=request, box=context)
            if sender in his_man.supervisors:
                await vr.respond_history(history=his_man.commands)
            else:
                await vr.respond_403()
            return ''
        elif kw_len == 13 and keywords.lower() == 'show keywords':
            #
            #  search keywords
            #
            vr = VideoResponse(request=request, box=context)
            if sender in his_man.supervisors:
                results = await context.load_video_results()
                blocked_list = await context.load_blocked_list()
                await vr.respond_keywords(results=results, blocked_list=blocked_list)
            else:
                await vr.respond_403()
            return ''
        elif kw_len == 17 and keywords.lower() == 'show blocked list':
            #
            #  blocked list
            #
            vr = VideoResponse(request=request, box=context)
            if sender in his_man.supervisors:
                blocked_list = await context.load_blocked_list()
                await vr.respond_blocked_list(keywords=blocked_list)
            else:
                await vr.respond_403()
            return ''
        elif 8 <= kw_len <= 128 and keywords.startswith('block: '):
            #
            #  block keyword
            #
            if sender in his_man.supervisors:
                pos = keywords.find(':') + 1
                blocked = keywords[pos:]
                text = await self._block_keyword(keyword=blocked, box=context)
                if text is not None:
                    await context.respond_text(text=text, request=request)
            else:
                vr = VideoResponse(request=request, box=context)
                await vr.respond_403()
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

    async def _block_keyword(self, keyword: str, box: VideoBox) -> Optional[str]:
        # trim keyword
        keyword = keyword.strip()
        keyword = keyword.strip('"')
        if len(keyword) == 0:
            self.error(msg='ignore empty keyword')
            return None
        # check keywords
        array = await box.load_blocked_list()
        if keyword in array:
            self.warning(msg='ignore duplicated keyword: %s' % keyword)
            return 'Keyword "%s" already blocked' % keyword
        # add keywords
        array.append(keyword)
        ok = await box.save_blocked_list(array=array)
        if not ok:
            self.error(msg='failed to save blocked: %s, %s' % (keyword, array))
            return 'Cannot block "%s" now' % keyword
        # OK
        return 'Keyword "%s" already blocked, blocked count: %d' % (keyword, len(array))

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
