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
from typing import Optional, List, Tuple

from dimples import URI
from dimples import DateTime
from dimples.utils import SharedCacheManager
from dimples.utils import CachePool
from dimples.database import DbInfo, DbTask

from ..common import Season

from .redis import SeasonCache, VideoSearchCache


class SeaTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, url: URI,
                 cache_pool: CachePool, redis: SeasonCache,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._url = url
        self._redis = redis

    # Override
    def cache_key(self) -> URI:
        return self._url

    async def _load_redis_cache(self) -> Optional[Season]:
        return await self._redis.load_season(url=self._url)

    async def _save_redis_cache(self, value: Season) -> bool:
        pass

    async def _load_local_storage(self) -> Optional[Season]:
        pass

    async def _save_local_storage(self, value: Season) -> bool:
        pass


class VidTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, keywords: str,
                 cache_pool: CachePool, redis: VideoSearchCache,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._keywords = keywords
        self._redis = redis

    # Override
    def cache_key(self) -> str:
        return self._keywords

    async def _load_redis_cache(self) -> Optional[Tuple[Optional[List[URI]], Optional[DateTime]]]:
        return await self._redis.load_results(keywords=self._keywords)

    async def _save_redis_cache(self, value: Tuple[Optional[List[URI]], Optional[DateTime]]) -> bool:
        pass

    async def _load_local_storage(self) -> Optional[Tuple[Optional[List[URI]], Optional[DateTime]]]:
        pass

    async def _save_local_storage(self, value: Tuple[Optional[List[URI]], Optional[DateTime]]) -> bool:
        pass


class SeasonTable:
    """ Implementations of VideoDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_seasons')  # URL => Season
        self._redis = SeasonCache(connector=info.redis_connector)
        self._lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  seasons cached in memory only !!!')

    def _new_task(self, url: URI) -> SeaTask:
        return SeaTask(url=url,
                       cache_pool=self._cache, redis=self._redis,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_season(self, season: Season, url: URI) -> bool:
        with self._lock:
            # 1. store into redis server
            if await self._redis.save_season(season=season, url=url):
                # 2. clear cache to reload
                self._cache.erase(key=url)
                return True

    async def load_season(self, url: URI) -> Optional[Season]:
        task = self._new_task(url=url)
        return await task.load()


class VideoSearchTable:
    """ Implementations of VideoDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_search')  # URL => Season
        self._redis = VideoSearchCache(connector=info.redis_connector)
        self._lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  seasons cached in memory only !!!')

    def _new_task(self, keywords: str) -> VidTask:
        return VidTask(keywords=keywords,
                       cache_pool=self._cache, redis=self._redis,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_results(self, results: List[URI], keywords: str) -> bool:
        with self._lock:
            # 1. store into redis server
            if await self._redis.save_results(results=results, keywords=keywords):
                # 2. clear cache to reload
                self._cache.erase(key=keywords)
                return True

    async def load_results(self, keywords: str) -> Tuple[Optional[List[URI]], Optional[DateTime]]:
        task = self._new_task(keywords=keywords)
        return await task.load()
