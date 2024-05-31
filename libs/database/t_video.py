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

from typing import Optional, List, Tuple

from dimples import URI
from dimples import DateTime
from dimples.utils import CacheManager

from ..common import Season
from .redis import SeasonCache, VideoSearchCache


class SeasonTable:
    """ Implementations of VideoDBI """

    CACHE_EXPIRES = 3600  # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = SeasonCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='video_seasons')  # URL => Season

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  seasons cached in memory only !!!')

    #
    #   Video DBI
    #

    async def save_season(self, season: Season, url: URI) -> bool:
        # 1. store into redis server
        if await self.__redis.save_season(season=season, url=url):
            # 2. clear cache to reload
            self.__cache.erase(key=url)
            return True

    async def load_season(self, url: URI) -> Optional[Season]:
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=url, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__cache.update(key=url, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = await self.__redis.load_season(url=url)
            # 3. update memory cache
            self.__cache.update(key=url, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value


class VideoSearchTable:
    """ Implementations of VideoDBI """

    CACHE_EXPIRES = 3600  # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = VideoSearchCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='video_search')  # URL => Season

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  seasons cached in memory only !!!')

    #
    #   Video DBI
    #

    async def save_results(self, results: List[URI], keywords: str) -> bool:
        # 1. store into redis server
        if await self.__redis.save_results(results=results, keywords=keywords):
            # 2. clear cache to reload
            self.__cache.erase(key=keywords)
            return True

    async def load_results(self, keywords: str) -> Tuple[Optional[List[URI]], Optional[DateTime]]:
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=keywords, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__cache.update(key=keywords, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None, None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = await self.__redis.load_results(keywords=keywords)
            # 3. update memory cache
            self.__cache.update(key=keywords, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value
