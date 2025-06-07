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

from abc import abstractmethod
from typing import Optional

from dimples import URI

from ...utils import Logging
from ...utils import HttpClient
from ...common import Episode, Season
from ...chat import ChatRequest

from .video import VideoBox


class Task:
    """ Search Task """

    CANCEL_PROMPT = '_If this task takes too long, you can input the commands below to stop it:_\n' \
                    '- **cancel**\n' \
                    '- **stop**\n' \
                    '\n' \
                    '### NOTICE:\n' \
                    '_Another new task will interrupt the previous task too._'

    def __init__(self, keywords: str, request: Optional[ChatRequest], box: VideoBox):
        super().__init__()
        self.__keywords = keywords
        self.__request = request
        self.__box = box
        self.__cancelled = False

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s id="%s" keywords="%s" />' % (cname, self.box.identifier, self.keywords)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s id="%s" keywords="%s" />' % (cname, self.box.identifier, self.keywords)

    @property
    def keywords(self) -> str:
        return self.__keywords

    @property
    def request(self) -> Optional[ChatRequest]:
        return self.__request

    @property
    def box(self) -> VideoBox:
        return self.__box

    @property
    def cancelled(self) -> bool:
        return self.__cancelled

    def cancel(self):
        """ stop the task """
        self.__cancelled = True

    def copy(self):
        return Task(keywords=self.keywords, request=self.request, box=self.box)


class Engine(Logging):
    """ Search Engine """

    CANCELLED_CODE = -205

    def __init__(self):
        super().__init__()
        self.__http_client = HttpClient(long_connection=True, verify=True, base_url=self.base_url)

    @property  # protected
    def http_client(self) -> HttpClient:
        return self.__http_client

    @property
    def agent(self) -> str:
        return self.__class__.__name__

    # Override
    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s</%s module="%s">' % (cname, self.base_url, cname, mod)

    # Override
    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s</%s module="%s">' % (cname, self.base_url, cname, mod)

    @property
    @abstractmethod
    def base_url(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def referer_url(self) -> str:
        raise NotImplemented

    def _clear_cookies(self):
        self.info(msg='clearing cookies')
        self.http_client.clear_cookies()

    async def _http_get(self, url: str, headers: dict = None) -> Optional[str]:
        if headers is None:
            headers = {
                'Accept': '*/*',
                # 'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Cache-Control': 'max-age=0',
                # 'Content-Type': 'application/json',
                # 'Origin': self.base_url,
                'Referer': self.referer_url,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                              ' AppleWebKit/537.36 (KHTML, like Gecko)'
                              ' Chrome/116.0.0.0 Safari/537.36',
            }
        try:
            return self.http_client.cache_get(url=url, headers=headers)
        except Exception as error:
            self.error(msg='failed to query url: %s, error: %s' % (url, error))

    #
    #   Searching
    #

    @abstractmethod
    async def search(self, task: Task) -> int:
        raise NotImplemented

    #
    #   Seasons
    #

    async def get_season(self, url: URI, task: Task) -> Optional[Season]:
        # self.info(msg='getting season: %s' % url)
        season = await self._load_season(url=url, task=task)
        if season is None:
            season = await self._query_season(url=url, task=task)
            if season is not None:
                self.info(msg='saving new season: %s' % season)
                await self._save_season(season=season, task=task)
        return season

    async def _save_season(self, season: Season, task: Task) -> bool:
        ok = await task.box.save_season(season=season)
        if not ok:
            self.error(msg='failed to save season: %s' % season)
        return ok

    async def _load_season(self, url: URI, task: Task) -> Optional[Season]:
        season = await task.box.load_season(url=url)
        if season is not None and season.is_expired():
            await self._update_season(season=season, task=task)
        return season

    async def _update_season(self, season: Season, task: Task):
        """ add update task to the shared engine """
        pass

    @abstractmethod
    async def _query_season(self, url: URI, task: Task) -> Optional[Season]:
        raise NotImplemented

    #
    #   Episodes
    #

    async def _get_episode(self, url: URI, title: Optional[str], task: Task) -> Optional[Episode]:
        # self.info(msg='getting episode: "%s" %s' % (title, url))
        episode = await self._load_episode(url=url, task=task)
        if episode is None:
            episode = await self._query_episode(url=url, title=title, task=task)
            if episode is not None:
                self.info(msg='saving new episode: "%s" %s -> %s' % (title, url, episode))
                await self._save_episode(episode=episode, url=url, task=task)
        return episode

    async def _save_episode(self, episode: Episode, url: URI, task: Task) -> bool:
        ok = await task.box.save_episode(episode=episode, url=url)
        if not ok:
            self.error(msg='failed to save episode: %s' % episode)
        return ok

    async def _load_episode(self, url: URI, task: Task) -> Optional[Episode]:
        episode = await task.box.load_episode(url=url)
        if episode is not None and episode.is_expired():
            await self._update_episode(episode=episode, task=task)
        return episode

    async def _update_episode(self, episode: Episode, task: Task):
        """ add update task to the shared engine """
        pass

    @abstractmethod
    async def _query_episode(self, url: URI, title: Optional[str], task: Task) -> Optional[Episode]:
        raise NotImplemented
