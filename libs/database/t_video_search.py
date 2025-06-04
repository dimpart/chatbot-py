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

import threading
from typing import Optional, List, Dict

from dimples import ID
from dimples.utils import SharedCacheManager
from dimples.utils import CachePool
from dimples.utils import Config
from dimples.database import DbTask

from .dos import VideoStorage


class BlkTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, storage: VideoStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._id = identifier
        self._dos = storage

    # Override
    def cache_key(self) -> str:
        return 'video_blocked'

    async def _load_redis_cache(self) -> Optional[List[str]]:
        pass

    async def _save_redis_cache(self, value: List[str]) -> bool:
        pass

    async def _load_local_storage(self) -> Optional[List[str]]:
        return await self._dos.load_blocked_list(identifier=self._id)

    async def _save_local_storage(self, value: List[str]) -> bool:
        return await self._dos.save_blocked_list(array=value, identifier=self._id)


class VidTask(DbTask):

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 32    # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, storage: VideoStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._id = identifier
        self._dos = storage

    # Override
    def cache_key(self) -> str:
        return 'video_results'

    async def _load_redis_cache(self) -> Optional[Dict[str, List]]:
        pass

    async def _save_redis_cache(self, value: Dict[str, List]) -> bool:
        pass

    async def _load_local_storage(self) -> Optional[Dict[str, List]]:
        return await self._dos.load_video_results(identifier=self._id)

    async def _save_local_storage(self, value: Dict[str, List]) -> bool:
        return await self._dos.save_video_results(results=value, identifier=self._id)


class VideoBlockTable:
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_blocked')  # 'video_blocked' => []
        self._dos = VideoStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID) -> BlkTask:
        return BlkTask(identifier=identifier,
                       cache_pool=self._cache, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_blocked_list(self, array: List[str], identifier: ID) -> bool:
        task = self._new_task(identifier=identifier)
        return await task.save(value=array)

    async def load_blocked_list(self, identifier: ID) -> List[str]:
        task = self._new_task(identifier=identifier)
        return await task.load()


class VideoSearchTable:
    """ Implementations of VideoDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='video_results')  # 'video_blocked' => {}
        self._dos = VideoStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID) -> VidTask:
        return VidTask(identifier=identifier,
                       cache_pool=self._cache, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   Video DBI
    #

    async def save_video_results(self, results: Dict[str, List], identifier: ID) -> bool:
        task = self._new_task(identifier=identifier)
        return await task.save(value=results)

    async def load_video_results(self, identifier: ID) -> Dict[str, List]:
        task = self._new_task(identifier=identifier)
        return await task.load()
