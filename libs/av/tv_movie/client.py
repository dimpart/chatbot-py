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
from dimples import Envelope, Content
from dimples import CustomizedContent
from dimples import CommonFacebook

from ...utils import Singleton, Runner
from ...utils import Log
from ...utils import Config
from ...common import Season
from ...chat.base import get_nickname
from ...chat import Request, ChatRequest
from ...chat import ChatBox, ChatClient
from ...chat import ChatContext
from ...chat import ChatProcessor, ChatProxy
from ...client import Emitter
from ...client import Monitor

from .video import VideoBox
from .engine import Task, Engine


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

    # Override
    async def save_response(self, text: str, prompt: str, request: Request) -> bool:
        # return await super().save_response(text=text, prompt=prompt, request=request)
        return False


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
            if sender in his_man.supervisors:
                await _respond_history(history=his_man.commands, request=request, box=context)
            else:
                await _respond_403(request=request, box=context)
            return ''
        elif kw_len == 12 and keywords.lower() == 'blocked list':
            #
            #  blocked list
            #
            if sender in his_man.supervisors:
                blocked_list = await context.load_blocked_list()
                await _respond_blocked_list(keywords=blocked_list, request=request, box=context)
            else:
                await _respond_403(request=request, box=context)
            return ''
        elif 8 <= kw_len <= 128 and keywords.startswith('block: '):
            #
            #  block keyword
            #
            if sender in his_man.supervisors:
                pos = keywords.startswith(':') + 1
                blocked = keywords[pos:]
                text = await self._block_keyword(keyword=blocked, box=context)
                if text is not None:
                    await context.respond_text(text=text, request=request)
            else:
                await _respond_403(request=request, box=context)
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
            await _respond_204(history=tree.keywords, keywords=task.keywords, request=task.request, box=box)
        elif code != Engine.CANCELLED_CODE:  # code != -205:
            self.error(msg='search error from engine: %d %s' % (code, engine))


async def _respond_204(history: List[str], keywords: str, request: ChatRequest, box: VideoBox):
    if history is None:
        history = []
    text = 'No contents for **"%s"**, you can try the following keywords:\n' % keywords
    text += '\n----\n'
    for his in history:
        text += '- **%s**\n' % his
    return await box.respond_markdown(text=text, request=request)


async def _respond_403(request: ChatRequest, box: VideoBox):
    text = 'Forbidden\n'
    text += '\n----\n'
    text += 'Permission Denied'
    return await box.respond_markdown(text=text, request=request)


async def _respond_blocked_list(keywords: List[str], request: ChatRequest, box: VideoBox):
    text = '## Blocked List\n'
    for kw in keywords:
        text += '* %s\n' % kw
    text += '\n'
    text += 'Total %d keyword(s)' % len(keywords)
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


@Singleton
class HistoryManager:

    MAX_LENGTH = 50

    def __init__(self):
        super().__init__()
        self.__config: Config = None
        self.__commands: List[Dict] = []
        self.__lock = threading.Lock()

    @property
    def config(self) -> Optional[Config]:
        return self.__config

    @config.setter
    def config(self, conf: Config):
        self.__config = conf

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


class SearchClient(ChatClient):

    def __init__(self, facebook: CommonFacebook):
        super().__init__(facebook=facebook)
        self.__engines: List[Engine] = []

    def add_engine(self, engine: Engine):
        self.__engines.append(engine)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.facebook
        processors = []
        for engine in self.__engines:
            processors.append(SearchHandler(engine=engine))
        # count = len(processors)
        # if count > 1:
        #     processors = random.sample(processors, count)
        proxy = ChatProxy(service='TV_MOV', processors=processors)
        return SearchBox(identifier=identifier, facebook=facebook, proxy=proxy)

    # Override
    async def process_customized_content(self, content: CustomizedContent, envelope: Envelope):
        app = content.application
        act = content.action
        if app == 'chat.dim.video':
            if act == 'request':
                await self._process_video_request(content=content, envelope=envelope)
            return
        # others
        return await super().process_customized_content(content=content, envelope=envelope)

    async def _process_video_request(self, content: CustomizedContent, envelope: Envelope):
        request = ChatRequest(content=content, envelope=envelope, facebook=self.facebook)
        box = self._get_box(identifier=request.identifier)
        assert isinstance(box, SearchBox), 'search box error: %s' % box
        mod = content.module
        if mod == 'index':
            video_list = await _fetch_video_index(box=box)
            self.info(msg='responding %d video(s) to %s' % (len(video_list), request.identifier))
            await _respond_video_index(video_list=video_list, request=request, box=box)
        elif mod == 'season':
            url_list = content.get('url_list')
            if url_list is None:
                url_list = []
            self.info(msg='loading %d seasons for %s' % (len(url_list), request.identifier))
            for url in url_list:
                season = await box.load_season(url=url)
                if season is None:
                    self.warning(msg='season not found: %s' % url)
                else:
                    self.info(msg='responding season: %s' % url)
                    await _respond_video_season(season=season, request=request, box=box)


async def _fetch_video_index(box: VideoBox) -> List[Dict]:
    tree = await box.load_video_results()
    #
    #  1. get keywords
    #
    keywords = []
    all_keywords = tree.keywords
    for kw in all_keywords:
        if kw in keywords:
            Log.warning(msg='duplicated keyword: %s' % kw)
            continue
        keywords.append(kw)
    #
    #  2. build bar chart
    #
    bars = []
    max_w = 0
    blocked_list = await box.load_blocked_list()
    for kw in keywords:
        if kw in blocked_list:
            Log.warning(msg='ignore blocked keyword: %s' % kw)
            continue
        video_list = tree.video_list(keyword=kw)
        if video_list is None:
            continue
        else:
            video_list = video_list.copy()
        # check blocked name
        pos = len(video_list)
        while pos > 0:
            pos -= 1
            item = video_list[pos]
            assert item is Dict, 'video info error: %s' % item
            if item.get('name') in blocked_list:
                Log.warning(msg='ignore blocked video name: %s' % item)
                video_list.pop(pos)
        # OK
        cnt = len(video_list)
        if cnt > 0:
            bars.append(video_list)
            if cnt > max_w:
                max_w = cnt
    max_h = len(bars)
    n = max_w + max_h - 1
    #
    #  3. build index
    #
    lt_array = []
    x = 0
    y = 0
    while x < n and y < n:
        # pick up item exists
        if y < len(bars):
            video_list = bars[y]
            if x < len(video_list):
                lt_array.append(video_list[x])
        # move pointers to next position
        if y == 0:
            # next slash
            y = x + 1
            x = 0
        else:
            y = y - 1
            x = x + 1
    #
    #   A:
    #       1  2  3  4
    #       5  6  7  8      =>      1 5 2 9 6 3 10 7 4 11 8 12
    #       9 10 11 12
    #
    #   B:
    #       1  2  3
    #       4  5  6         =>      1 4 2 7 5 3 10 8 6 11 9 12
    #       7  8  9
    #      10 11 12
    #
    return lt_array


async def _respond_video_index(video_list: List[Dict], request: ChatRequest, box: VideoBox):
    response = CustomizedContent.create(app='chat.dim.video', mod='index', act='respond')
    response['index'] = video_list
    #
    #  extra param: serial number
    #
    query = request.content
    tag = query.get('tag')
    if tag is None:
        tag = query.sn
    response['tag'] = tag
    #
    #  extra param: visibility
    #
    response['hidden'] = True
    response['muted'] = True
    # OK
    await box.respond_content(content=response, request=request)


async def _respond_video_season(season: Season, request: ChatRequest, box: VideoBox):
    response = CustomizedContent.create(app='chat.dim.video', mod='season', act='respond')
    response['season'] = season.dictionary
    #
    #  extra param: visibility
    #
    response['hidden'] = True
    response['muted'] = True
    # FIXME: respond markdown
    await box.respond_content(content=response, request=request)
