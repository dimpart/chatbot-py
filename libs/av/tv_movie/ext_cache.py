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

from abc import abstractmethod
from typing import Optional, List

from dimples import URI
from dimples import DateTime

from ...utils import Log
from ...common import Season

from .video import build_season, build_season_full, build_season_link
from .task import Task
from .parser import SeasonInfo
from .response import VideoResponse
from .ext_base import BaseEngine


class CommonEngine(BaseEngine):
    """ Cached Search Engine """

    UPDATE_EXPIRES = 3600  # seconds

    # Override
    async def search(self, task: Task) -> int:
        keywords = task.keywords
        request = task.request
        box = task.box
        if request is None:
            # it's update task, don't check cache
            # and no need to respond
            code = await super().search(task=task)
            self.info(msg='update task "%s", code: %d' % (keywords, code))
            return code
        # load search results from database
        total = await self._check_cached_results(task=task)
        if total > 0:
            return total
        # do search
        code = await super().search(task=task)
        if code == -205:
            self.warning(msg='task cancelled: %s' % task)
            vr = VideoResponse(request=request, box=box)
            await vr.respond_205(keywords=keywords)
        elif code < 0:  # -404
            vr = VideoResponse(request=request, box=box)
            await vr.respond_404(keywords=keywords)
        return code

    async def _check_cached_results(self, task: Task) -> int:
        keywords = task.keywords
        request = task.request
        box = task.box
        #
        #  load from local cache
        #
        tree = await box.load_video_results()
        results = tree.page_list(keyword=keywords)
        if results is None:
            self.info(msg='cached for keyword: "%s" not found' % keywords)
            return 0
        total = len(results)
        if total > 0:
            self.info(msg='load %d result(s) for "%s"' % (total, keywords))
            tree.touch(keyword=keywords)
            await self._respond_results(results=results, task=task)
            #
            #  check update time
            #
            update_time = tree.last_time(keyword=keywords)
            if update_time is not None:
                now = DateTime.now()
                if now < (update_time + self.UPDATE_EXPIRES):
                    self.info(msg='last update time: %s, "%s", total: %d' % (update_time, keywords, total))
                    return total
            # cache expired, update for new results
            self.info(msg='update for keywords: "%s", %s' % (keywords, request.envelope.sender))
            await self._update_keyword(task=task)
        return total

    @abstractmethod
    async def _update_keyword(self, task: Task):
        raise NotImplemented

    async def _respond_results(self, results: List[URI], task: Task):
        total = len(results)
        keywords = task.keywords
        index = 0
        while index < total and index < 10:
            page_url = results[index]
            season = await self.get_season(url=page_url, task=task)
            if season is None:
                self.warning(msg='failed to load season: %s => %s' % (keywords, page_url))
                text = '(%d/%d) [%s](%s "")' % (index + 1, total, keywords, page_url)
            else:
                self.info(msg='got season: "%s", %s' % (season.name, page_url))
                text = build_season(season=season, index=index, total=total)
            # await box.respond_markdown(text=text, request=request)
            await self._respond_markdown(text=text, sn=0, task=task)
            index += 1
        while index < total:
            batch_text = ''
            # get next batch
            end = index + 20
            end = index + 10 if end < total else total
            while index < end:
                page_url = results[index]
                season = await self.get_season(url=page_url, task=task)
                if season is None:
                    self.warning(msg='failed to load season: %s => %s' % (keywords, page_url))
                    text = '(%d/%d) [%s](%s "")' % (index + 1, total, keywords, page_url)
                else:
                    self.info(msg='got season: "%s", %s' % (season.name, page_url))
                    text = build_season(season=season, index=index, total=total)
                batch_text += '%s\n\n' % text
                index += 1
            # await box.respond_markdown(text=batch_text, request=request)
            await self._respond_markdown(text=batch_text, sn=0, task=task)

    # Override
    async def _respond_markdown(self, text: str, sn: int, task: Task) -> int:
        """ respond text with sn, return the sn """
        request = task.request
        box = task.box
        content = await box.respond_markdown(text=text, request=request, sn=sn, muted='yes')
        return content['sn']

    # Override
    async def _respond_season_names(self, html: str, total: int, sn: int, task: Task):
        keywords = task.keywords
        text = 'Got **%d** records for **"%s"**,' % (total, keywords)
        text += ' please select a name below and search again:\n'
        text += '\n----\n'
        page = 0
        index = 0
        accurate_seasons: List[Season] = []
        while index < total:
            # parse seasons
            season_items = self.parser.parse_seasons(html=html)
            count = len(season_items)
            if count == 0:
                self.error(msg='failed to parse seasons: "%s", page %d' % (keywords, page + 1))
                break
            self.info(msg='got %d/%d seasons for "%s", page %d' % (count, total, keywords, page + 1))
            # check items
            for i in range(count):
                item = season_items[i]
                if item.name == keywords:
                    # exactly!!
                    accurate = await self.get_season(url=item.page, task=task)
                    if accurate is not None:
                        self.info(msg='got accurate season (%d/%d): %s' % (index, total, accurate))
                        acc_text = build_season_full(season=accurate, index=index, total=total)
                        await self._respond_markdown(text=acc_text, sn=0, task=task)
                        # add to candidates
                        accurate = Season(info=accurate.dictionary)
                        accurate.index = index
                        accurate.total = total
                        accurate_seasons.append(accurate)
                    self.info(msg='got accurate season "%s" (%d/%d): %s' % (keywords, index, total, accurate))
                index += 1
            # respond partially
            text += _build_partial_seasons(season_items=season_items, start=0, total=total, candidates=accurate_seasons)
            partial = '%s\n\n----\n\n' % text
            partial += '_**%d/%d** received, waiting for more results..._\n\n' % (index, total)
            partial += Task.CANCEL_PROMPT
            sn = await self._respond_markdown(text=partial, sn=sn, task=task)
            # check index
            if index >= total:
                # done
                break
            elif index > 100 and total > 200:
                self.warning(msg='too many results: %d, %d' % (index, total))
                break
            # next page
            page += 1
            html = await self.get_search_page(keywords=keywords, page=page, task=task)
            if html is None:
                self.error(msg='failed to get page %d for keywords: "%s"' % (page + 1, keywords))
                break
        if task.cancelled:
            text += '\n\n----\n\n'
            text += '_This searching task has been interrupted._'
        elif index < total:
            text += '\n\n----\n\n'
            text += '_Too many results, only the top **%d** of **%d** shown._' % (index, total)
        # await box.respond_markdown(text=text, request=request)
        await self._respond_markdown(text=text, sn=sn, task=task)
        # check accurate result
        if index < total:
            # copy non-cancelable task to continue the searching
            await self._seek_accurate_season(keywords=keywords, page=page, index=index, total=total, task=task.copy())
        elif len(accurate_seasons) == 0:
            self.warning(msg='searching task "%s" failed.' % keywords)

    # private
    async def _seek_accurate_season(self, keywords: str, page: int, index: int, total: int, task: Task):
        accurate: Optional[Season] = None
        while index < total:
            # next page
            page += 1
            html = await self.get_search_page(keywords=keywords, page=page, task=task)
            if html is None:
                self.error(msg='failed to get page %d for keywords: "%s"' % (page + 1, keywords))
                break
            # parse seasons
            season_items = self.parser.parse_seasons(html=html)
            count = len(season_items)
            if count == 0:
                self.error(msg='failed to seek accurate season: "%s", page %d' % (keywords, page + 1))
                break
            self.info(msg='got %d/%d seasons for "%s", page %d' % (count, total, keywords, page + 1))
            # check items
            for i in range(count):
                item = season_items[i]
                if item.name == keywords:
                    # exactly!!
                    accurate = await self.get_season(url=item.page, task=task)
                    if accurate is not None:
                        self.info(msg='got accurate season (%d/%d): %s' % (index, total, accurate))
                        text = build_season_full(season=accurate, index=index, total=total)
                        await self._respond_markdown(text=text, sn=0, task=task)
                    self.info(msg='got accurate season "%s" (%d/%d): %s' % (keywords, index, total, accurate))
                index += 1
        # check accurate result
        if accurate is None:
            self.warning(msg='bg searching task "%s" failed.' % keywords)


def _build_partial_seasons(season_items: List[SeasonInfo], start: int, total: int, candidates: List[Season]) -> str:
    count = len(season_items)
    text = ''
    if total < 100:
        for index in range(count):
            item = season_items[index]
            page = item.page
            name = item.name
            tags = item.tags
            link = _fetch_season_link(page=page, candidates=candidates)
            # name/link
            if link is not None:
                text += '%d. %s' % (start + index + 1, link)
            else:
                text += '%d. **%s**' % (start + index + 1, name)
            # tags
            if tags is not None and len(tags) > 0:
                text += ' _[%s]_' % tags
            text += '\n'

    else:
        for index in range(count):
            item = season_items[index]
            page = item.page
            name = item.name
            tags = item.tags
            link = _fetch_season_link(page=page, candidates=candidates)
            # name/link
            if link is not None:
                text += '- %s' % link
            else:
                text += '- **%s**' % name
            # tags
            if tags is not None and len(tags) > 0:
                text += ' _[%s]_' % tags
            text += '\n'
    return text


def _fetch_season_link(page: URI, candidates: List) -> Optional[str]:
    for item in candidates:
        Log.info(msg='comparing season page: %s, %s' % (item.page, page))
        if item.page == page:
            return build_season_link(season=item, index=item.index, total=item.total)
