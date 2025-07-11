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
from dimples.utils import CachePool
from dimples.utils import Config
from dimples.database import DbTask
from dimples.database.t_base import DataCache

from ..common import Episode, Season

from .dos import SeasonStorage
from .redis import SeasonCache, EpisodeCache


class EpiTask(DbTask[URI, Episode]):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID, url: URI,
                 redis: EpisodeCache,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH)
        self._id = identifier
        self._url = url
        self._redis = redis

    @property  # Override
    def cache_key(self) -> URI:
        return self._url

    # Override
    async def _read_data(self) -> Optional[Episode]:
        return await self._redis.load_episode(url=self._url)

    # Override
    async def _write_data(self, value: Episode) -> bool:
        return await self._redis.save_episode(episode=value, url=self._url)


class SeaTask(DbTask[URI, Season]):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID, url: URI,
                 redis: SeasonCache, storage: SeasonStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH)
        self._id = identifier
        self._url = url
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> URI:
        return self._url

    # Override
    async def _read_data(self) -> Optional[Season]:
        # 1. get from redis server
        season = await self._redis.load_season(url=self._url)
        if season is not None:
            return season
        # 2. get from local storage
        season = await self._dos.load_season(url=self._url, identifier=self._id)
        if season is not None:
            # 3. update redis server
            await self._redis.save_season(season=season)
            return season

    # Override
    async def _write_data(self, value: Season) -> bool:
        # 1. store into redis server
        ok1 = await self._redis.save_season(season=value)
        # 2. save into local storage
        ok2 = await self._dos.save_season(season=value, identifier=self._id)
        return ok1 or ok2


class EpisodeTable(DataCache):
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__(pool_name='video_episodes')  # URL => Episode
        self._redis = EpisodeCache(config=config)

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  episode cached in memory only !!!')

    def _new_task(self, url: URI, identifier: ID) -> EpiTask:
        return EpiTask(url=url, identifier=identifier,
                       redis=self._redis,
                       mutex_lock=self._mutex_lock, cache_pool=self._cache_pool)

    #
    #   Video DBI
    #

    async def save_episode(self, episode: Episode, url: URI, identifier: ID) -> bool:
        if url is None:
            url = episode.url
            assert url is not None, 'episode url not found: %s' % episode
        #
        #  1. check time
        #
        new_time = episode.time
        if new_time is not None:
            # check old record
            task = self._new_task(url=url, identifier=identifier)
            old = await task.load()
            if old is not None:
                # check time
                old_time = old.time
                if old_time is not None and old_time.after(other=new_time):
                    self.warning(msg='ignore expired episode: %s' % episode)
                    return False
        #
        #  2. save new record
        #
        task = self._new_task(url=url, identifier=identifier)
        ok = await task.save(value=episode)
        if not ok:
            self.error(msg='failed to save episode: %s' % episode)
        return ok

    async def load_episode(self, url: URI, identifier: ID) -> Optional[Episode]:
        task = self._new_task(url=url, identifier=identifier)
        return await task.load()


class SeasonTable(DataCache):
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__(pool_name='video_seasons')  # URL => Season
        self._redis = SeasonCache(config=config)
        self._dos = SeasonStorage(config=config)

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, url: URI, identifier: ID) -> SeaTask:
        return SeaTask(url=url, identifier=identifier,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._mutex_lock, cache_pool=self._cache_pool)

    #
    #   Video DBI
    #

    async def save_season(self, season: Season, identifier: ID) -> bool:
        url = season.page
        assert url is not None, 'season url not found: %s' % season
        #
        #  1. check time
        #
        new_time = season.time
        if new_time is not None:
            # check old record
            task = self._new_task(url=url, identifier=identifier)
            old = await task.load()
            if old is not None:
                # check time
                old_time = old.time
                if old_time is not None and old_time.after(other=new_time):
                    self.warning(msg='ignore expired season: %s' % season)
                    return False
        #
        #  2. save new record
        #
        task = self._new_task(url=url, identifier=identifier)
        ok = await task.save(value=season)
        if not ok:
            self.error(msg='failed to save season: %s' % season)
        return ok

    async def load_season(self, url: URI, identifier: ID) -> Optional[Season]:
        task = self._new_task(url=url, identifier=identifier)
        return await task.load()
