# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

import time
from typing import Optional, List, Dict

from dimples import ID

from dimples.utils import CacheManager
from dimples.common import GroupDBI

from .dos import GroupStorage
from .redis import GroupCache


class GroupTable(GroupDBI):
    """ Implementations of GroupDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupStorage(root=root, public=public, private=private)
        self.__redis = GroupCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='members')  # ID => List[ID]
        self.__cache_keys = man.get_pool(name='group_keys')  # (sender, group) => Dict[str, str]  # member => key

    def show_info(self):
        self.__dos.show_info()

    #
    #   Group DBI
    #

    # Override
    def founder(self, group: ID) -> Optional[ID]:
        # TODO: get founder
        pass

    # Override
    def owner(self, group: ID) -> Optional[ID]:
        # TODO: get owner
        pass

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__cache.update(key=group, value=members, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_members(members=members, group=group)
        # 3. store into local storage
        return self.__dos.save_members(members=members, group=group)

    # Override
    def members(self, group: ID) -> List[ID]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # meta not load yet, wait to load
                self.__cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # meta not exists
                    return []
                # meta expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.members(group=group)
            if len(value) == 0:
                # 3. check local storage
                value = self.__dos.members(group=group)
                if len(value) > 0:
                    # update redis server
                    self.__redis.save_members(members=value, group=group)
            # update memory cache
            self.__cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def add_member(self, member: ID, group: ID) -> bool:
        array = self.members(group=group)
        if member in array:
            # self.warning(msg='member exists: %s, group: %s' % (member, group))
            return True
        array.append(member)
        return self.save_members(members=array, group=group)

    # Override
    def remove_member(self, member: ID, group: ID) -> bool:
        array = self.members(group=group)
        if member not in array:
            # self.warning(msg='member not exists: %s, group: %s' % (member, group))
            return True
        array.remove(member)
        return self.save_members(members=array, group=group)

    # Override
    def remove_group(self, group: ID) -> bool:
        # TODO: remove group
        # self.warning(msg='TODO: remove group: %s' % group)
        return False

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        # TODO: save assistants
        pass

    # Override
    def assistants(self, group: ID) -> List[ID]:
        # TODO: get assistants
        pass

    """
        Encrypted keys
        ~~~~~~~~~~~~~~

        redis key: 'mkm.group.{GID}.encrypted-keys'
    """

    def load_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        now = time.time()
        cache_key = (sender, group)
        # 1. check memory cache
        value, holder = self.__cache_keys.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # keys not load yet, wait to load
                self.__cache_keys.update(key=cache_key, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # keys not exists
                    return {}
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.load_keys(sender=sender, group=group)
            if len(value) == 0:
                # 3. check local storage
                value = self.__dos.load_keys(sender=sender, group=group)
                if value is None:
                    value = {}  # placeholder
                # update redis server
                self.__redis.save_keys(keys=value, sender=sender, group=group)
            # update memory cache
            self.__cache_keys.update(key=cache_key, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def save_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        # old = self.load_keys(sender=sender, group=group)
        # if old is not None:
        #     # update old keys
        #     for member in keys:
        #         old[member] = keys.get(member)
        #     keys = old
        #     # FIXME: what about members that has been expelled?
        cache_key = (sender, group)
        # 1. store into memory cache
        self.__cache.update(key=cache_key, value=keys, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_keys(keys=keys, sender=sender, group=group)
        # 3. store into local storage
        return self.__dos.save_keys(keys=keys, sender=sender, group=group)
