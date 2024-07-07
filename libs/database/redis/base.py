# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from abc import ABC, abstractmethod
from typing import Optional

from aiou import Redis
from aiou import RedisClient
from aiou import RedisConnector


class Cache(RedisClient, ABC):

    @property
    @abstractmethod
    def db_name(self) -> Optional[str]:
        """ database name for redis """
        raise NotImplemented

    @property
    @abstractmethod
    def tbl_name(self) -> str:
        """ table name for redis """
        raise NotImplemented

    def get_redis(self, name: str) -> Optional[Redis]:
        """ Get Redis with name

            0 - default
            1 - mkm.meta
            2 - mkm.document
            3 - mkm.user
            4 - mkm.group
            5
            6
            7 - mkm.session
            8 - dkd.msg
            9 - dkd.key
        """
        connector = self.connector
        if connector is None:
            return None
        else:
            assert isinstance(connector, RedisConnector)
        if name == 'default':
            return connector.get_redis(db=0)
        #
        #  MingKeMing
        #
        elif name == 'mkm.meta':
            return connector.get_redis(db=1)
        elif name == 'mkm.document':
            return connector.get_redis(db=2)
        elif name == 'mkm.user':
            return connector.get_redis(db=3)
        elif name == 'mkm.group':
            return connector.get_redis(db=4)
        #
        #  Session
        #
        elif name == 'mkm.session':
            return connector.get_redis(db=7)
        #
        #  DaoKeDao
        #
        elif name == 'dkd.msg':
            return connector.get_redis(db=8)
        elif name == 'dkd.key':
            return connector.get_redis(db=9)

    @property  # Override
    def redis(self) -> Optional[Redis]:
        db_name = self.db_name
        tbl_name = self.tbl_name
        db = None
        if db_name is not None:
            db = self.get_redis(name='%s.%s' % (db_name, tbl_name))
        if db is None:
            db = self.get_redis(name=tbl_name)
        if db is None:
            db = super().redis
        return db
