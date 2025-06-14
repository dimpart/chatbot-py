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
from dimples import CustomizedContent
from dimples import CommonFacebook

from ...chat import ChatRequest
from ...chat import ChatBox, ChatClient
from ...chat import ChatProxy

from ..engine import Engine

from .box import SearchBox
from .response import VideoResponse
from .handler import SearchHandler


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
        vr = VideoResponse(request=request, box=box)
        mod = content.module
        if mod == 'playlist':
            video_list = await box.fetch_playlist()
            self.info(msg='responding %d video(s) to %s' % (len(video_list), request.identifier))
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
