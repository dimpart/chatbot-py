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
from abc import abstractmethod
from typing import Optional, List

from dimples import URI

from ...utils import Singleton, Logging
from ...utils import HttpClient
from ...common import Season

from ...chat import ChatRequest, VideoBox


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
    #   Query Season
    #
    async def get_season(self, url: URI, task: Task) -> Optional[Season]:
        box = task.box
        season = await box.load_season(url=url)
        if season is None:
            season = await self._query_season(url=url, task=task)
            if season is not None:
                await box.save_season(season=season, url=url)
        elif season.is_expired():
            self._update_season(season=season, task=task)
        return season

    @abstractmethod
    async def _query_season(self, url: URI, task: Task) -> Optional[Season]:
        raise NotImplemented

    def _update_season(self, season: Season, task: Task):
        """ add update task to the shared engine """
        pass


@Singleton
class KeywordManager:

    MAX_LENGTH = 20

    def __init__(self):
        super().__init__()
        self.__keywords: List[str] = []
        self.__lock = threading.Lock()

    @property
    def keywords(self) -> List[str]:
        with self.__lock:
            return self.__keywords.copy()

    def add_keyword(self, keyword: str):
        with self.__lock:
            count = len(self.__keywords)
            index = 0
            while index < count:
                item = self.__keywords[index]
                if item != keyword:
                    index += 1
                    continue
                # keyword found
                if index > 0:
                    # move to the front
                    self.__keywords.pop(index)
                    self.__keywords.insert(0, keyword)
                return False
            # keyword not exists
            self.__keywords.insert(0, keyword)
            if count > self.MAX_LENGTH:
                # remove the last one
                self.__keywords.pop(count)
