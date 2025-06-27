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

from typing import Optional, List

from dimples import ID
from dimples import Envelope
from dimples import TextContent, CustomizedContent
from dimples import CommonFacebook

from ...utils import Config
from ...chat import ChatRequest
from ...chat import ChatBox, ChatClient
from ...chat import ChatProxy

from ..engine import Engine

from .box import SearchBox
from .response import VideoResponse
from .handler import SearchHandler
from .handler import HistoryManager


class SearchClient(ChatClient):

    def __init__(self, facebook: CommonFacebook, config: Config):
        super().__init__(facebook=facebook, config=config)
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
        else:
            # others
            return await super().process_customized_content(content=content, envelope=envelope)

    async def _process_video_request(self, content: CustomizedContent, envelope: Envelope):
        request = ChatRequest(content=content, envelope=envelope, facebook=self.facebook)
        box = self._get_box(identifier=request.identifier)
        assert isinstance(box, SearchBox), 'search box error: %s' % box
        vr = VideoResponse(request=request, box=box)
        mod = content.module
        if mod == 'playlist':
            video_list = await box.fetch_playlist()
            total = len(video_list)
            if total > self.MAX_PLAY_ITEMS:
                video_list = video_list[:self.MAX_PLAY_ITEMS]
            self.info(msg='responding %d/%d video(s) to %s' % (len(video_list), total, request.identifier))
            await vr.respond_playlist(video_list=video_list)
        elif mod == 'season':
            url_list = content.get('page_list')
            if url_list is None:
                url = content.get('page')
                if url is None:
                    url_list = []
                else:
                    url_list = [url]
            self.info(msg='loading %d seasons for %s' % (len(url_list), request.identifier))
            for url in url_list:
                season = await box.load_season(url=url)
                if season is None:
                    self.warning(msg='season not found: %s' % url)
                else:
                    self.info(msg='responding season: %s' % url)
                    await vr.respond_video_season(season=season)

    MAX_PLAY_ITEMS = 5 * 7 * 8 * 9  # 2520

    ADMIN_COMMANDS = [
        'help',
        'show history',
        'show keywords',
        'show blocked list',
    ]

    HELP_PROMPT = '## Admin Commands\n' \
                  '* show history\n' \
                  '* show keywords\n' \
                  '* show blocked list\n' \
                  '* block: "{KEYWORD}"\n' \
                  '* allow: "{KEYWORD}"\n'

    # Override
    async def process_text_content(self, content: TextContent, envelope: Envelope):
        request = ChatRequest(content=content, envelope=envelope, facebook=self.facebook)
        text = await request.build()
        text = text.strip()
        if text in self.ADMIN_COMMANDS:
            # system command
            await self._process_admin_command(cmd=text, request=request)
        elif text.startswith('block: ') or text.startswith('allow: '):
            # block / unblock
            await self._process_admin_command(cmd=text, request=request)
        else:
            # others
            return await super().process_text_content(content=content, envelope=envelope)

    async def _process_admin_command(self, cmd: str, request: ChatRequest):
        box = self._get_box(identifier=request.identifier)
        if isinstance(box, SearchBox):
            box.cancel_task()
        else:
            assert False, 'search box error: %s' % box
            # self.error(msg='search box error: %s' % box)
            # return False
        sender = request.envelope.sender
        group = request.content.group
        vr = VideoResponse(request=request, box=box)
        # save command in history
        his_man = HistoryManager()
        his_man.add_command(cmd=cmd, when=request.time, sender=sender, group=group)
        # check permissions before executing command
        supervisors = await self.config.get_supervisors(facebook=self.facebook)
        if sender not in supervisors:
            self.warning(msg='permission denied: "%s", sender: %s' % (cmd, sender))
            await vr.respond_403()
        elif cmd == 'help':
            #
            #  usages
            #
            await box.respond_markdown(text=self.HELP_PROMPT, request=request)
        elif cmd == 'show history':
            #
            #  search history
            #
            array = his_man.commands
            await vr.respond_history(history=array)
        elif cmd == 'show keywords':
            #
            #  search keywords
            #
            results = await box.load_video_results()
            blocked_list = await box.load_blocked_list()
            await vr.respond_keywords(results=results, blocked_list=blocked_list)
        elif cmd == 'show blocked list':
            #
            #  blocked list
            #
            blocked_list = await box.load_blocked_list()
            await vr.respond_blocked_list(keywords=blocked_list)
        elif cmd.startswith('block: '):
            #
            #  append keyword to blocked-list
            #
            pos = cmd.find(':') + 1
            blocked = cmd[pos:]
            text = await self._block_keyword(keyword=blocked, box=box)
            if text is not None:
                await box.respond_text(text=text, request=request)
        elif cmd.startswith('allow: '):
            #
            #  remove keyword from blocked-list
            #
            pos = cmd.find(':') + 1
            blocked = cmd[pos:]
            text = await self._allow_keyword(keyword=blocked, box=box)
            if text is not None:
                await box.respond_text(text=text, request=request)

    async def _block_keyword(self, keyword: str, box: SearchBox) -> Optional[str]:
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

    async def _allow_keyword(self, keyword: str, box: SearchBox) -> Optional[str]:
        # trim keyword
        keyword = keyword.strip()
        keyword = keyword.strip('"')
        if len(keyword) == 0:
            self.error(msg='ignore empty keyword')
            return None
        # check keywords
        array = await box.load_blocked_list()
        if keyword not in array:
            self.warning(msg='ignore non-blocked keyword: %s' % keyword)
            return 'Keyword "%s" not blocked' % keyword
        # remove keywords
        array.remove(keyword)
        ok = await box.save_blocked_list(array=array)
        if not ok:
            self.error(msg='failed to save blocked: %s, %s' % (keyword, array))
            return 'Cannot allow "%s" now' % keyword
        # OK
        return 'Keyword "%s" already allowed, blocked count: %d' % (keyword, len(array))
