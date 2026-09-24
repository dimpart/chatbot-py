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

from abc import ABC, abstractmethod
from typing import Optional, List

from dimples import DateTime
from dimples import Converter
from dimples import Dictionary
from dimples import URI
from dimples import ID

from ...utils import Logging

from .episode import Episode, Season


class VideoTree(Dictionary, Logging):
    """
        Video Results Tree
        ~~~~~~~~~~~~~~~~~~

        data format:
            {
                '{KEYWORD}' : {
                    'time': 12345,
                    'page_list': [
                        '{SEASON_PAGE}'
                    ]
                }
            }
    """

    @property
    def keywords(self) -> List[str]:
        """ Sorted keywords by last update time """
        keys = self.keys()
        array = []
        # List[Tuple[str, float]]
        for kw in keys:
            pages = self.page_list(keyword=kw)
            if pages is None or len(pages) == 0:
                self.warning('skip empty keyword: %s', kw)
                continue
            last = self.last_time(keyword=kw)
            if last is None:
                self.error('last update time lost: %s, %d', kw, len(pages))
                continue
            array.append((kw, last.timestamp))
        # sort with last update time
        array.sort(key=lambda item: item[1], reverse=True)
        # take keywords
        return [item[0] for item in array]

    def page_list(self, keyword: str) -> Optional[List[URI]]:
        """ Get season page list for this keyword """
        results = self.get(keyword)
        if results is not None:
            return results.get('page_list')

    def last_time(self, keyword: str) -> Optional[DateTime]:
        """ Get last update time for this keyword """
        results = self.get(keyword)
        if results is not None:
            timestamp = results.get('time')
            return Converter.get_datetime(value=timestamp, default=None)

    def touch(self, keyword: str) -> bool:
        """ Refresh last update time """
        results = self.get(keyword)
        if results is not None:
            results['time'] = DateTime.current_timestamp()
            return True

    def update_results(self, keyword: str, page_list: List[URI]):
        """ Set results for keyword """
        self[keyword] = {
            'time': DateTime.current_timestamp(),
            'page_list': page_list,
        }


class VideoDBI(ABC):

    @abstractmethod
    async def save_episode(self, episode: Episode, url: URI, identifier: ID) -> bool:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.save_episode()'
        )

    @abstractmethod
    async def load_episode(self, url: URI, identifier: ID) -> Optional[Episode]:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.load_episode()'
        )

    @abstractmethod
    async def save_season(self, season: Season, identifier: ID) -> bool:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.save_season()'
        )

    @abstractmethod
    async def load_season(self, url: URI, identifier: ID) -> Optional[Season]:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.load_season()'
        )

    #
    #   Video List
    #

    @abstractmethod
    async def save_video_results(self, results: VideoTree, identifier: ID) -> bool:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.save_video_results()'
        )

    @abstractmethod
    async def load_video_results(self, identifier: ID) -> Optional[VideoTree]:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.load_video_results()'
        )

    @abstractmethod
    async def save_blocked_list(self, array: List[str], identifier: ID) -> bool:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.save_blocked_list()'
        )

    @abstractmethod
    async def load_blocked_list(self, identifier: ID) -> Optional[List[str]]:
        raise NotImplementedError(
            f'Not implemented: {type(self).__module__}.{type(self).__name__}.load_blocked_list()'
        )
