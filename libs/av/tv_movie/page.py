import threading
import time
from typing import Optional

from dimples.utils import SharedCacheManager
from dimples.database import Storage

from ...utils import Singleton, Config


@Singleton
class WebMaster:

    MEM_CACHE_EXPIRES = 600  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self):
        self.__config: Config = None
        man = SharedCacheManager()
        self.__cache = man.get_pool(name='web_pages')  # path => text
        self.__lock = threading.Lock()

    @property
    def config(self) -> Optional[Config]:
        return self.__config

    @config.setter
    def config(self, info: Config):
        self.__config = info

    @property
    def homepage(self) -> Optional[str]:
        config = self.config
        if config is not None:
            return config.get_string(section='webmaster', option='homepage')

    @property
    def format(self) -> Optional[str]:
        config = self.config
        if config is not None:
            return config.get_string(section='webmaster', option='format')

    async def load_homepage(self) -> Optional[str]:
        path = self.homepage
        if path is None:
            return None
        else:
            now = time.time()
            key = path
            cache_pool = self.__cache
        #
        #  1. check memory cache
        #
        value, holder = cache_pool.fetch(key=key, now=now)
        if value is not None:
            # got it from cache
            return value
        elif holder is None:
            # holder not exists, means it is the first querying
            pass
        elif holder.is_alive(now=now):
            # holder is not expired yet,
            # means the value is actually empty,
            # no need to check it again.
            return None
        #
        #  2. lock for querying
        #
        with self.__lock:
            # locked, check again to make sure the cache not exists.
            # (maybe the cache was updated by other threads while waiting the lock)
            value, holder = cache_pool.fetch(key=key, now=now)
            if value is not None:
                return value
            elif holder is None:
                pass
            elif holder.is_alive(now=now):
                return None
            else:
                # holder exists, renew the expired time for other threads
                holder.renewal(duration=self.MEM_CACHE_REFRESH, now=now)
            # check local storage
            value = await Storage.read_text(path=path)
            # update memory cache
            cache_pool.update(key=key, value=value, life_span=self.MEM_CACHE_EXPIRES, now=now)
        #
        #  3. OK, return cached value
        #
        return value
