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
from typing import Optional

from dimples import URI
from dimples import ID
from dimples.utils import SharedCacheManager
from dimples.utils import CachePool
from dimples.utils import Config
from dimples.database import DbTask

from ..common import Episode, Season

from .dos import SeasonStorage
from .redis import SeasonCache, EpisodeCache


class EpiTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID, url: URI,
                 cache_pool: CachePool, redis: EpisodeCache,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._id = identifier
        self._url = url
        self._redis = redis

    # Override
    def cache_key(self) -> URI:
        return self._url

    async def _load_redis_cache(self) -> Optional[Episode]:
        return await self._redis.load_episode(url=self._url)

    async def _save_redis_cache(self, value: Episode) -> bool:
        return await self._redis.save_episode(episode=value)

    async def _load_local_storage(self) -> Optional[Episode]:
        pass

    async def _save_local_storage(self, value: Episode) -> bool:
        pass


class SeaTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID, url: URI,
                 cache_pool: CachePool, redis: SeasonCache, storage: SeasonStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._id = identifier
        self._url = url
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> URI:
        return self._url

    async def _load_redis_cache(self) -> Optional[Season]:
        return await self._redis.load_season(url=self._url)

    async def _save_redis_cache(self, value: Season) -> bool:
        return await self._redis.save_season(season=value)

    async def _load_local_storage(self) -> Optional[Season]:
        return await self._dos.load_season(url=self._url, identifier=self._id)

    async def _save_local_storage(self, value: Season) -> bool:
        return await self._dos.save_season(season=value, identifier=self._id)


class EpisodeTable:
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_episodes')  # URL => Episode
        self._redis = EpisodeCache(config=config)
        self._lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  episode cached in memory only !!!')

    def _new_task(self, url: URI, identifier: ID) -> EpiTask:
        return EpiTask(url=url, identifier=identifier,
                       cache_pool=self._cache, redis=self._redis,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_episode(self, episode: Episode, identifier: ID) -> bool:
        task = self._new_task(url=episode.url, identifier=identifier)
        return await task.save(value=episode)

    async def load_episode(self, url: URI, identifier: ID) -> Optional[Episode]:
        task = self._new_task(url=url, identifier=identifier)
        return await task.load()


class SeasonTable:
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_seasons')  # URL => Season
        self._redis = SeasonCache(config=config)
        self._dos = SeasonStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, url: URI, identifier: ID) -> SeaTask:
        return SeaTask(url=url, identifier=identifier,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_season(self, season: Season, identifier: ID) -> bool:
        task = self._new_task(url=season.page, identifier=identifier)
        return await task.save(value=season)

    async def load_season(self, url: URI, identifier: ID) -> Optional[Season]:
        task = self._new_task(url=url, identifier=identifier)
        return await task.load()
