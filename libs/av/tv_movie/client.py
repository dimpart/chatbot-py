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

# import random
import threading
from typing import Optional, List, Dict

from dimples import DateTime
from dimples import ID
from dimples import Content
from dimples import TextContent
from dimples import CommonFacebook

from ...utils import Log
from ...utils import Singleton, Runner
from ...chat import Request, ChatRequest
from ...chat import ChatBox, VideoBox, ChatClient
from ...chat import ChatContext
from ...chat import ChatProcessor, ChatProxy
from ...chat.base import get_nickname
from ...client import Emitter
from ...client import Monitor

from .engine import Task, Engine
from .engine import KeywordManager
from .tvscan import TVScan, LiveConfig
from .page import WebMaster


class SearchBox(VideoBox):

    def __init__(self, identifier: ID, facebook: CommonFacebook, proxy: ChatProxy):
        super().__init__(identifier=identifier, facebook=facebook, proxy=proxy)
        self.__task: Optional[Task] = None
        self.__lock = threading.Lock()

    def cancel_task(self):
        with self.__lock:
            self._cancel_task()

    def _cancel_task(self):
        task = self.__task
        if task is not None:
            self.__task = None
            self.warning(msg='cancelling task')
            task.cancel()

    def new_task(self, keywords: str, request: ChatRequest) -> Task:
        with self.__lock:
            task = Task(keywords=keywords, request=request, box=self)
            self._cancel_task()
            self.__task = task
            return task

    # Override
    def report_success(self, service: str, agent: str):
        monitor = Monitor()
        monitor.report_success(service=service, agent=agent)

    # Override
    def report_failure(self, service: str, agent: str):
        monitor = Monitor()
        monitor.report_failure(service=service, agent=agent)

    # Override
    def report_crash(self, service: str):
        monitor = Monitor()
        monitor.report_crash(service=service)

    # Override
    async def process_request(self, request: Request) -> Optional[ChatProcessor]:
        coro = super().process_request(request=request)
        # searching in background
        thr = Runner.async_thread(coro=coro)
        thr.start()
        # FIXME:
        return None

    # Override
    async def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        return await emitter.send_content(content=content, receiver=receiver)


class SearchHandler(ChatProcessor):

    def __init__(self, engine: Engine):
        super().__init__(agent=engine.agent)
        self.__engine = engine
        # TODO: LiveConfig for TV channels
        config = LiveConfig(info={
            'tvbox': {
                'sources': [
                    TVScan.INDEX_URI,
                ],
            }
        })
        self.__tv = TVScan(config=config)
        self.__wm = WebMaster()

    # Override
    async def _query(self, prompt: str, content: TextContent, request: ChatRequest, context: ChatContext) -> bool:
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
            return True
        else:
            context.cancel_task()
            # save command in history
            his_man = HistoryManager()
            his_man.add_command(cmd=keywords, when=request.time, sender=sender, group=group)
        # system commands
        if kw_len == 6 and keywords.lower() == 'cancel':
            return True
        elif kw_len == 4 and keywords.lower() == 'stop':
            return True
        elif kw_len == 12 and keywords.lower() == 'show history':
            await _respond_history(history=his_man.commands, request=request, box=context)
            return True
        #
        #  2. search
        #
        task = context.new_task(keywords=keywords, request=request)
        if kw_len == 11 and keywords.lower() == 'tv channels':
            tv = self.__tv
            tv.clear_caches()
            coro = tv.search(task=task)
        elif kw_len == 19 and keywords.lower() == 'live stream sources':
            tv = self.__tv
            tv.clear_caches()
            array = await tv.get_lives()
            await _respond_live_urls(lives=array, request=request, box=context)
            return True
        elif kw_len == 12 and keywords.lower() == 'china travel':
            wm = self.__wm
            text = await wm.load_homepage()
            text_format = wm.format
            await _respond_homepage(text=text, text_format=text_format, request=request, box=context)
            return True
        else:
            coro = self._search(task=task, box=context)
        # searching in background
        return await coro
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
            key_man = KeywordManager()
            await _respond_204(history=key_man.keywords, keywords=task.keywords, request=task.request, box=box)
        elif code != Engine.CANCELLED_CODE:  # code != -205:
            self.error(msg='search error from engine: %d %s' % (code, engine))


async def _respond_204(history: List[str], keywords: str, request: ChatRequest, box: VideoBox):
    if history is None:
        history = []
    text = 'No contents for **"%s"**, you can try the following keywords:\n' % keywords
    text += '\n----\n'
    for his in history:
        text += '- **%s**\n' % his
    text += '\n'
    text += 'You can also input this command to scan TV channels:\n'
    text += '\n- **TV channels**'
    return await box.respond_markdown(text=text, request=request)


async def _respond_history(history: List[Dict], request: ChatRequest, box: VideoBox):
    text = 'Search history:\n'
    text += '| From | Keyword | Time |\n'
    text += '|------|---------|------|\n'
    for his in history:
        sender = his.get('sender')
        group = his.get('group')
        when = his.get('when')
        cmd = his.get('cmd')
        assert sender is not None and cmd is not None, 'history error: %s' % his
        sender = ID.parse(identifier=sender)
        group = ID.parse(identifier=group)
        user = '**"%s"**' % await box.get_name(identifier=sender)
        if group is not None:
            user += ' (%s)' % await box.get_name(identifier=group)
        text += '| %s | %s | %s |\n' % (user, cmd, when)
    return await box.respond_markdown(text=text, request=request)


async def _respond_live_urls(lives: List[Dict], request: ChatRequest, box: VideoBox):
    count = len(lives)
    text = 'Live Stream Sources:\n'
    text += '\n----\n'
    for item in lives:
        url = item.get('url')
        text += '- [%s](%s#lives.txt "LIVE")\n' % (url, url)
    text += '\n----\n'
    text += 'Total %d source(s).' % count
    # search tag
    tag = request.content.get('tag')
    title = request.content.get('title')
    hidden = request.content.get('hidden')
    cid = request.identifier
    Log.info(msg='respond %d sources with tag %s to %s' % (count, tag, cid))
    return await box.respond_markdown(text=text, request=request, muted='yes', extra={
        'hidden': hidden,

        'app': 'chat.dim.tvbox',
        'mod': 'lives',
        'act': 'respond',
        'expires': 600,

        'tag': tag,
        'title': title,
        'lives': lives,
        'description': TVScan.LIST_DESC,
    })


async def _respond_homepage(text: Optional[str], text_format: Optional[str], request: ChatRequest, box: VideoBox):
    if text is None:
        text = '## 404 Not Found\n' \
               'The requested resource could not be found but may be available in the future.'
        text_format = 'markdown'
    elif text_format is None:
        text_format = 'markdown'
    # search tag
    tag = request.content.get('tag')
    title = request.content.get('title')
    hidden = request.content.get('hidden')
    cid = request.identifier
    Log.info(msg='respond %d bytes with tag %s to %s' % (len(text), tag, cid))
    return await box.respond_text(text=text, request=request, extra={
        'format': text_format,
        'muted': 'yes',
        'hidden': hidden,

        'app': 'chat.dim.sites',
        'mod': 'homepage',
        'act': 'respond',
        'expires': 600,

        'tag': tag,
        'title': title,
    })


@Singleton
class HistoryManager:

    MAX_LENGTH = 50

    def __init__(self):
        super().__init__()
        self.__commands: List[Dict] = []
        self.__lock = threading.Lock()

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
        processors = []
        for engine in self.__engines:
            processors.append(SearchHandler(engine=engine))
        # count = len(processors)
        # if count > 1:
        #     processors = random.sample(processors, count)
        proxy = ChatProxy(service='TV_MOV', processors=processors)
        return SearchBox(identifier=identifier, facebook=facebook, proxy=proxy)
