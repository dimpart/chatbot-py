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

from typing import Optional, Union, Dict

from dimples import json_encode, json_decode, utf8_encode, utf8_decode
from dimples import URI
from dimples import Mapper
from dimples.database.redis import RedisCache

from ...common import Episode, Season


class SeasonCache(RedisCache):

    # season cached in Redis will be removed after 24 hours.
    EXPIRES = 3600 * 24  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'video'

    @property  # Override
    def tbl_name(self) -> str:
        return 'season'

    """
        Season
        ~~~~~~

        redis key: 'video.season.{URL}'
    """
    def __key(self, url: URI) -> str:
        return '%s.%s.%s' % (self.db_name, self.tbl_name, url)

    async def save_season(self, season: Season) -> bool:
        """ Save season with page URL """
        url = season.page
        key = self.__key(url=url)
        value = encode_map(info=season)
        return await self.set(name=key, value=value, expires=self.EXPIRES)

    async def load_season(self, url: URI) -> Optional[Season]:
        """ Load season with page URL """
        key = self.__key(url=url)
        value = await self.get(name=key)
        dictionary = decode_map(data=value)
        return Season.parse_season(season=dictionary)


class EpisodeCache(RedisCache):

    # episode cached in Redis will be removed after 3 days.
    EXPIRES = 3600 * 24 * 3  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'video'

    @property  # Override
    def tbl_name(self) -> str:
        return 'episode'

    """
        Episode
        ~~~~~~~

        redis key: 'video.episode.{URL}'
    """
    def __key(self, url: URI) -> str:
        return '%s.%s.%s' % (self.db_name, self.tbl_name, url)

    async def save_episode(self, episode: Episode) -> bool:
        """ Save episode with URL """
        url = episode.url
        key = self.__key(url=url)
        value = encode_map(info=episode)
        return await self.set(name=key, value=value, expires=self.EXPIRES)

    async def load_episode(self, url: URI) -> Optional[Episode]:
        """ Load episode with URL """
        key = self.__key(url=url)
        value = await self.get(name=key)
        dictionary = decode_map(data=value)
        return Episode.parse_episode(episode=dictionary)


def encode_map(info: Union[Dict, Mapper]) -> bytes:
    if isinstance(info, Mapper):
        info = info.dictionary
    js = json_encode(obj=info)
    return utf8_encode(string=js)


def decode_map(data: Optional[bytes]) -> Optional[Dict]:
    if data is None:
        return None
    js = utf8_decode(data=data)
    assert js is not None, 'failed to decode string: %s' % data
    info = json_decode(string=js)
    assert info is not None, 'failed to decode map: %s' % js
    return info
