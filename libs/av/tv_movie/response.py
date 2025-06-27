# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2025 Albert Moky
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

from typing import List, Dict

from dimples import DateTime
from dimples import ID
from dimples import CustomizedContent

from ...utils import Logging
from ...common import Season, VideoTree
from ...chat import ChatRequest

from ..video import build_season_link
from ..video import VideoBox


class VideoResponse(Logging):

    def __init__(self, request: ChatRequest, box: VideoBox):
        super().__init__()
        self.__request = request
        self.__box = box

    @property
    def request(self) -> ChatRequest:
        return self.__request

    @property
    def box(self) -> VideoBox:
        return self.__box

    async def respond_204(self, history: List[str], keywords: str):
        if history is None:
            history = []
        text = 'No contents for **"%s"**, you can try the following keywords:\n' % keywords
        text += '\n----\n'
        for his in history:
            text += '- **%s**\n' % his
        return await self.box.respond_markdown(text=text, request=self.request)

    async def respond_205(self, keywords: str):
        text = 'Searching for "%s" is cancelled.' % keywords
        return await self.box.respond_text(text=text, request=self.request)

    async def respond_403(self):
        text = 'Forbidden\n'
        text += '\n----\n'
        text += 'Permission Denied'
        return await self.box.respond_markdown(text=text, request=self.request)

    async def respond_404(self, keywords: str):
        text = 'Failed to search for "%s", please try again later.' % keywords
        return await self.box.respond_text(text=text, request=self.request)

    #
    #   Keywords
    #

    async def respond_keywords(self, results: VideoTree, blocked_list: List[str]):
        text = '## Keywords\n'
        text += '\n----\n'
        total_pages = 0
        keywords = results.keywords
        for kw in keywords:
            # get video list
            page_list = results.page_list(keyword=kw)
            count = 0 if page_list is None else len(page_list)
            total_pages += count
            # show keyword
            if kw in blocked_list:
                text += '* %s, count = %d (BLOCKED)\n' % (kw, count)
            else:
                text += '* %s, count = %d\n' % (kw, count)
            # show video names
            if count > 0:
                pos = 0
                for url in page_list:
                    pos += 1
                    if pos > 10:
                        text += '  %d. ...\n' % pos
                        break
                    season = await self.box.load_season(url=url)
                    if season is None:
                        text += '  %d. %s\n' % (pos, url)
                    else:
                        name = season.name
                        if name in blocked_list:
                            text += '  %d. %s (BLOCKED)\n' % (pos, name)
                        else:
                            text += '  %d. %s\n' % (pos, name)
        text += '\n----\n'
        text += 'Total %d keyword(s), %d result(s).' % (len(keywords), total_pages)
        return await self.box.respond_markdown(text=text, request=self.request)

    async def respond_blocked_list(self, keywords: List[str]):
        text = '## Blocked List\n'
        text += '\n----\n'
        for kw in keywords:
            text += '* %s\n' % kw
        text += '\n----\n'
        text += 'Total %d keyword(s)' % len(keywords)
        return await self.box.respond_markdown(text=text, request=self.request)

    async def respond_history(self, history: List[Dict]):
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
            user = '**"%s"**' % await self.box.get_name(identifier=sender)
            if group is not None:
                user += ' (%s)' % await self.box.get_name(identifier=group)
            text += '| %s | %s | %s |\n' % (user, cmd, when)
        return await self.box.respond_markdown(text=text, request=self.request)

    #
    #   Playlist
    #

    async def respond_playlist(self, video_list: List[Dict]):
        response = CustomizedContent.create(app='chat.dim.video', mod='playlist', act='respond')
        response['playlist'] = video_list
        #
        #  extra param: serial number
        #
        query = self.request.content
        tag = query.get('tag')
        if tag is None:
            tag = query.sn
        response['tag'] = tag
        #
        #  query title
        #
        title = query.get('title')
        if title is not None:
            response['title'] = title
        #
        #  query keywords
        #
        keywords = query.get('keywords')
        if keywords is not None:
            response['keywords'] = keywords
        #
        #  extra param: visibility
        #
        response['hidden'] = True
        response['muted'] = True
        # OK
        await self.box.respond_content(content=response, request=self.request)

    async def respond_video_season(self, season: Season):
        response = CustomizedContent.create(app='chat.dim.video', mod='season', act='respond')
        #
        #  extra param: visibility
        #
        response['hidden'] = True
        response['muted'] = True
        #
        #  extra param: format
        #
        query = self.request.content
        txt_fmt = query.get('format')  # markdown
        if txt_fmt == 'markdown':
            link = build_season_link(season=season, index=0, total=1)
            cover = season.cover
            if cover is None or cover.find('://') < 0:
                self.warning(msg='season cover not found: %s' % season)
                text = link
            else:
                text = '![](%s "")\n\n%s' % (cover, link)
            response['text'] = text
            response['format'] = 'markdown'
            # digest
            time = season.time
            if time is None:
                time = DateTime.now()
            response['season'] = {
                'page': season.page,
                'name': season.name,
                'time': time.timestamp,
            }
        else:
            response['season'] = season.dictionary
        # OK
        await self.box.respond_content(content=response, request=self.request)
