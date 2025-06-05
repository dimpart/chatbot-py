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

from typing import Optional, List, Dict

from dimples import URI
from dimples import ID
from dimples.utils import md5, utf8_encode, hex_encode
from dimples.database.dos.base import template_replace
from dimples.database.dos import Storage

from ...common import Season
from ...common import VideoTree


class SeasonStorage(Storage):
    """
        Season in a TV drama
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/video_seasons/{AB}/{CD}/season-{TAG}.js'
    """
    season_path = '{PROTECTED}/{ADDRESS}/video_seasons/{AB}/{CD}/season-{TAG}.js'

    def show_info(self):
        path = self.protected_path(self.season_path)
        print('!!!         season path: %s' % path)

    def __season_path(self, identifier: ID, url: URI) -> str:
        tag = md5(data=utf8_encode(string=url))
        tag = hex_encode(data=tag)
        ab = tag[0:2]
        cd = tag[2:4]
        path = self.protected_path(self.season_path)
        path = template_replace(path, 'AB', ab)
        path = template_replace(path, 'CD', cd)
        path = template_replace(path, 'TAG', tag)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    async def load_season(self, url: URI, identifier: ID) -> Optional[Season]:
        path = self.__season_path(url=url, identifier=identifier)
        info = await self.read_json(path=path)
        if info is None:
            self.info(msg='season not exists: %s url: %s' % (path, url))
            return None
        self.info(msg='loaded season from: %s url: %s' % (path, url))
        assert isinstance(info, Dict), 'season error: %s -> %s' % (path, info)
        return Season.parse_season(season=info)

    async def save_season(self, season: Season, identifier: ID) -> bool:
        url = season.page
        path = self.__season_path(url=url, identifier=identifier)
        self.info(msg='saving season "%s" (%s) into %s' % (season.name, url, path))
        return await self.write_json(container=season.dictionary, path=path)


class VideoStorage(Storage):
    """
        Video Index
        ~~~~~~~~~~~

            results format:
                {
                    '{KEYWORD}' : {
                        'time': 1234,
                        'list': [
                            {
                                'url': '{SEASON_PAGE}',
                                'name': '{SEASON_NAME}'
                            }
                        ]
                    }
                }

            blocked format:
                [
                    "{KEYWORD}"
                ]

        file path: '.dim/protected/{ADDRESS}/video_results.js'
        file path: '.dim/protected/{ADDRESS}/video_blocked.js'
    """
    results_path = '{PROTECTED}/{ADDRESS}/video_results.js'
    blocked_path = '{PROTECTED}/{ADDRESS}/video_results.js'

    def show_info(self):
        path1 = self.protected_path(self.results_path)
        path2 = self.protected_path(self.blocked_path)
        print('!!!  video results path: %s' % path1)
        print('!!!  video blocked path: %s' % path2)

    def __results_path(self, identifier: ID) -> str:
        path = self.protected_path(self.results_path)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def __blocked_path(self, identifier: ID) -> str:
        path = self.protected_path(self.blocked_path)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    async def load_video_results(self, identifier: ID) -> Optional[VideoTree]:
        path = self.__results_path(identifier=identifier)
        info = await self.read_json(path=path)
        if info is None:
            self.warning(msg='video results not exists: %s' % path)
            return None
        self.info(msg='loaded %d video result(s) from: %s' % (len(info), path))
        return VideoTree(dictionary=info)

    async def save_video_results(self, results: VideoTree, identifier: ID) -> bool:
        info = results.dictionary
        path = self.__results_path(identifier=identifier)
        self.info(msg='saving %d video result(s) to path: %s' % (len(results), path))
        return await self.write_json(container=info, path=path)

    async def load_blocked_list(self, identifier: ID) -> Optional[List[str]]:
        path = self.__blocked_path(identifier=identifier)
        array = await self.read_json(path=path)
        if array is None:
            self.warning(msg='blocked list not exists: %s' % path)
            return None
        self.info(msg='loaded %d blocked keyword(s) from: %s' % (len(array), path))
        return array

    async def save_blocked_list(self, array: List[str], identifier: ID) -> bool:
        path = self.__blocked_path(identifier=identifier)
        self.info(msg='saving %d keyword(s) to blocked list: %s' % (len(array), path))
        return await self.write_json(container=array, path=path)
