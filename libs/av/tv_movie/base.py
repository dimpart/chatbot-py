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

from abc import ABC, abstractmethod
from typing import Optional

from dimples import URI

from ...common import Season, Tube, Episode

from ..video import build_season
from ..task import Task
from ..engine import Engine
from ..parser import TubeInfo, EpisodeInfo
from ..parser import Parser


class BaseEngine(Engine, ABC):
    """ Search Engine """

    @property
    @abstractmethod
    def parser(self) -> Parser:
        """ page parser """
        raise NotImplemented

    #
    #   Episodes
    #

    # Override
    async def _query_episode(self, url: URI, title: Optional[str], task: Task) -> Optional[Episode]:
        if task.cancelled:
            self.warning(msg='task cancelled: %s, stop querying episode: "%s" -> %s' % (task, title, url))
            return None
        html = await self._http_get(url=url)
        if html is None:
            return None
        # 1. check episode title
        if title is None or len(title) == 0:
            title = self.parser.fetch_episode_title(html=html)
        # 2. decode m3u8 URL
        m3u8 = self.parser.fetch_m3u8(html=html)
        if m3u8 is not None:
            return Episode(title=title, url=m3u8)

    #
    #   Seasons
    #

    # Override
    async def _query_season(self, url: URI, task: Task) -> Optional[Season]:
        if task.cancelled:
            self.warning(msg='task cancelled: %s, stop querying season: %s' % (task, url))
            return None
        html = await self._http_get(url=url)
        if html is None:
            return None
        # 1. check movie name
        name = self.parser.fetch_season_name(html=html)
        # 2. check movie cover
        cover = self.parser.fetch_season_cover(html=html)
        # 3. fetch movie description
        desc = self.parser.fetch_season_description(html=html)
        # 4. parse episodes in tubes
        all_tubes = []
        tube_items = self.parser.parse_tubes(html=html)
        for t_item in tube_items:
            assert isinstance(t_item, TubeInfo), 'tube error: %s' % t_item
            all_episodes = []
            episode_items = t_item.episodes
            for e_item in episode_items:
                assert isinstance(e_item, EpisodeInfo), 'episode error: %s' % e_item
                episode = await self._get_episode(url=e_item.page, title=e_item.title, task=task)
                if episode is not None:
                    all_episodes.append(episode)
                elif task.cancelled:
                    self.warning(msg='task cancelled: %s, stop building tube: "%s" -> "%s"'
                                     % (task, t_item.title, name))
                    return None
            all_tubes.append(Tube(title=t_item.title, episodes=all_episodes))
        # OK
        return Season(page=url, name=name, cover=cover, details=desc, tubes=all_tubes)

    #
    #   Searching
    #

    # Override
    async def search(self, task: Task) -> int:
        keywords = task.keywords
        request = task.request
        box = task.box
        #
        #  1. search with keyword
        #
        page = 0
        if request is None:
            self.info(msg='update keywords: "%s"' % keywords)
        else:
            self.info(msg='search with keywords: "%s", %s' % (keywords, request.envelope.sender))
        html = await self.get_search_page(keywords=keywords, page=page, task=task)
        if html is None:
            # error
            return -404
        # get total count
        total = self.parser.fetch_total_seasons(html=html)
        if total > 0:
            self.info(msg='got %d result(s) for "%s"' % (total, keywords))
        if request is not None:
            sn = 0
            # respond digest
            if total > 1:
                text = 'Got **%d** results for **"%s"**, waiting for details...' % (total, keywords)
                text += '\n\n----\n\n'
                text += Task.CANCEL_PROMPT
                # await box.respond_markdown(text=text, request=request)
                sn = await self._respond_markdown(text=text, sn=0, task=task)
            if total > 60:
                # too many results, respond name list only
                await self._respond_season_names(html=html, total=total, sn=sn, task=task)
                return total
        #
        #  2. parse seasons
        #
        season_page_list = []
        index = 0
        season_items = self.parser.parse_seasons(html=html)
        count = len(season_items)
        self.info(msg='got %d/%d seasons for "%s", first page %d' % (count, total, keywords, page + 1))
        for i in range(count):
            s_item = season_items[i]
            page_url = s_item.page
            if request is None or index == 0:
                sn = 0
            else:
                partial = '_Searching [%d/%d] **"%s"** for **"%s"**, please wait a moment..._'\
                          % (index + 1, total, s_item.name, keywords)
                partial += '\n\n----\n\n'
                partial += Task.CANCEL_PROMPT
                sn = await self._respond_markdown(text=partial, sn=0, task=task)
            # query season info
            season = await self.get_season(url=page_url, task=task)
            if season is not None:
                season_page_list.append(page_url)
                await box.save_season(season=season)
            elif task.cancelled:
                self.warning(msg='task cancelled: %s, stop searching seasons: %s' % (task, season_items))
                return -205
            # if request exists, build response
            if request is not None:
                if season is None:
                    self.warning(msg='failed to query season: %s => %s' % (keywords, page_url))
                    text = '(%d/%d) [%s](%s "")' % (index + 1, total, keywords, page_url)
                else:
                    self.info(msg='got season: "%s", %s' % (season.name, page_url))
                    text = build_season(season=season, index=index, total=total)
                # await box.respond_markdown(text=text, request=request)
                await self._respond_markdown(text=text, sn=sn, task=task)
            # next page url
            index += 1
        #
        #  3. parse next page
        #
        while index < total:
            page += 1
            html = await self.get_search_page(keywords=keywords, page=page, task=task)
            if html is None:
                # error
                break
            batch_text = ''
            sn = 0
            season_items = self.parser.parse_seasons(html=html)
            count = len(season_items)
            if count == 0:
                self.error(msg='failed to parse seasons: "%s", page %d' % (keywords, page + 1))
                break
            self.info(msg='got %d/%d seasons for "%s", page %d' % (count, total, keywords, page + 1))
            for i in range(count):
                s_item = season_items[i]
                page_url = s_item.page
                if request is not None and sn == 0:
                    partial = '_Searching [%d/%d] **"%s"** for **"%s"**, please wait a moment..._'\
                              % (index + 1, total, s_item.name, keywords)
                    partial += '\n\n----\n\n'
                    partial += Task.CANCEL_PROMPT
                    sn = await self._respond_markdown(text=partial, sn=0, task=task)
                # query season info
                season = await self.get_season(url=page_url, task=task)
                if season is not None:
                    season_page_list.append(page_url)
                    await box.save_season(season=season)
                elif task.cancelled:
                    self.warning(msg='task cancelled: %s, stop searching seasons: %s' % (task, season_items))
                    return -205
                # if request exists, build response
                if request is not None:
                    if season is None:
                        self.warning(msg='failed to query season: %s => %s' % (keywords, page_url))
                        text = '(%d/%d) [%s](%s "")' % (index + 1, total, keywords, page_url)
                    else:
                        self.info(msg='got season: "%s", %s' % (season.name, page_url))
                        text = build_season(season=season, index=index, total=total)
                    batch_text += '%s\n\n' % text
                    if (i + 1) < count:
                        # respond partially
                        next_name = season_items[i + 1].name
                        partial = '%s\n\n----\n\n' % batch_text
                        partial += '_Searching [%d/%d] **"%s"** for **"%s"**, please wait a moment..._'\
                                   % (index + 1, total, next_name, keywords)
                        partial += '\n\n'
                        partial += Task.CANCEL_PROMPT
                        sn = await self._respond_markdown(text=partial, sn=sn, task=task)
                # next page url
                index += 1
            # respond this batch
            if request is not None:
                await self._respond_markdown(text=batch_text, sn=sn, task=task)
        # done
        if task.cancelled:
            self.warning(msg='task cancelled: %s, stop saving season urls: "%s" -> %s'
                             % (task, keywords, season_page_list))
            return -205
        count = len(season_page_list)
        if count > 0:
            tree = await box.load_video_results()
            tree.update_results(keyword=keywords, page_list=season_page_list)
            await box.save_video_results(results=tree)
        return count

    @abstractmethod
    async def get_search_page(self, keywords: str, page: int, task: Task) -> Optional[str]:
        """ query search page with keywords and page number """
        raise NotImplemented

    @abstractmethod
    async def _respond_season_names(self, html: str, total: int, sn: int, task: Task):
        """ respond season name list """
        raise NotImplemented

    @abstractmethod
    async def _respond_markdown(self, text: str, sn: int, task: Task) -> int:
        """ respond text with sn, return the sn """
        raise NotImplemented
