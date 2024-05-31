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
from typing import Optional, Any, Dict, List, Tuple

from dimples import DateTime
from dimples import Mapper, Dictionary
from dimples import URI


class Episode(Dictionary):

    EXPIRES = 3600 * 24  # seconds

    def __init__(self, info: Dict[str, Any] = None,
                 title: str = None, url: URI = None):
        super().__init__(dictionary=info)
        if info is None:
            self.set_datetime(key='time', value=DateTime.now())
        if title is not None:
            self['title'] = title
        if url is not None:
            self['url'] = url

    @property
    def time(self) -> Optional[DateTime]:
        """ created time """
        return self.get_datetime(key='time', default=None)

    def is_expired(self, now: DateTime = None) -> bool:
        last_time = self.time
        if last_time is None:
            return True
        elif now is None:
            now = DateTime.now()
        return now > (last_time + self.EXPIRES)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s title="%s" url="%s" />' % (cname, self.title, self.url)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s title="%s" url="%s" />' % (cname, self.title, self.url)

    @property
    def title(self) -> str:
        return self.get_str(key='title', default='')

    @property
    def url(self) -> URI:
        """ M3U8 """
        return self.get_str(key='url', default='')

    #
    #   Factory
    #
    @classmethod
    def parse_episode(cls, episode: Any):  # -> Optional[Episode]:
        if episode is None:
            return None
        elif isinstance(episode, Episode):
            return episode
        elif isinstance(episode, Mapper):
            episode = episode.dictionary
        return Episode(info=episode)

    @classmethod
    def convert_episodes(cls, array: List[Dict]):  # -> List[Episode]:
        results = []
        for item in array:
            episode = cls.parse_episode(episode=item)
            if episode is None:
                # episode info error
                continue
            results.append(episode)
        return results

    @classmethod
    def revert_episodes(cls, array: List[Mapper]) -> List[Dict]:
        results = []
        for item in array:
            results.append(item.dictionary)
        return results


class Tube(Dictionary):

    def __init__(self, info: Dict[str, Any] = None,
                 title: str = None, episodes: List[Episode] = None):
        super().__init__(dictionary=info)
        if title is not None:
            self['title'] = title
        if episodes is not None:
            self['episodes'] = Episode.revert_episodes(array=episodes)
        self.__episodes = episodes

    # Override
    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        children = '\n'
        for item in self.episodes:
            children += '    %s\n' % item
        return '  <%s title="%s">%s' \
               '  </%s module="%s">' % (cname, self.title, children, cname, mod)

    # Override
    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        children = '\n'
        for item in self.episodes:
            children += '    %s\n' % item
        return '  <%s title="%s">%s' \
               '  </%s module="%s">' % (cname, self.title, children, cname, mod)

    @property
    def title(self) -> str:
        """ Channel """
        return self.get_str(key='title', default='')

    @property
    def episodes(self) -> List[Episode]:
        array = self.__episodes
        if array is None:
            array = self.get(key='episodes', default=None)
            if array is None:
                self['episodes'] = array = []
            self.__episodes = array = Episode.convert_episodes(array=array)
        return array

    @episodes.setter
    def episodes(self, array: List[Episode]):
        if array is not None:
            self['episodes'] = Episode.revert_episodes(array=array)
        self.__episodes = array

    #
    #   Factory
    #
    @classmethod
    def parse_tube(cls, tube: Any):  # -> Optional[Tube]:
        if tube is None:
            return None
        elif isinstance(tube, Tube):
            return tube
        elif isinstance(tube, Mapper):
            tube = tube.dictionary
        return Tube(info=tube)

    @classmethod
    def convert_tubes(cls, array: List[Dict]):  # -> List[Tube]:
        results = []
        for item in array:
            tube = cls.parse_tube(tube=item)
            if tube is None:
                # tube info error
                continue
            results.append(tube)
        return results

    @classmethod
    def revert_tubes(cls, array: List[Mapper]) -> List[Dict]:
        results = []
        for item in array:
            results.append(item.dictionary)
        return results


class Season(Dictionary):

    EXPIRES = 3600 * 5  # seconds

    def __init__(self, info: Dict[str, Any] = None,
                 page: URI = None,
                 name: str = None, cover: str = None, details: Optional[str] = None,
                 tubes: List[Tube] = None):
        super().__init__(dictionary=info)
        if info is None:
            self.set_datetime(key='time', value=DateTime.now())
        if page is not None:
            self['page'] = page
        if name is not None:
            self['name'] = name
        if cover is not None:
            self['cover'] = cover
        if details is not None:
            self['details'] = details
        if tubes is not None:
            self['tubes'] = Tube.revert_tubes(array=tubes)
        self.__tubes = tubes

    @property
    def time(self) -> Optional[DateTime]:
        """ created time """
        return self.get_datetime(key='time', default=None)

    def is_expired(self, now: DateTime = None) -> bool:
        last_time = self.time
        if last_time is None:
            return True
        elif now is None:
            now = DateTime.now()
        return now > (last_time + self.EXPIRES)

    # Override
    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        children = '\n'
        for item in self.tubes:
            children += '%s\n' % item
        return '<%s name="%s" cover="%s">%s' \
               '</%s module="%s">' % (cname, self.name, self.cover, children, cname, mod)

    # Override
    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        children = '\n'
        for item in self.tubes:
            children += '%s\n' % item
        return '<%s name="%s" cover="%s">%s' \
               '</%s module="%s">' % (cname, self.name, self.cover, children, cname, mod)

    @property
    def page(self) -> URI:
        return self.get_str(key='page', default='')

    @property
    def name(self) -> str:
        return self.get_str(key='name', default='')

    @property
    def cover(self) -> Optional[str]:
        """ JPEG """
        return self.get_str(key='cover', default=None)

    @property
    def details(self) -> Optional[str]:
        return self.get_str(key='details', default=None)

    @property
    def tubes(self) -> List[Tube]:
        array = self.__tubes
        if array is None:
            array = self.get(key='tubes', default=None)
            if array is None:
                self['tubes'] = array = []
            self.__tubes = array = Tube.convert_tubes(array=array)
        return array

    @tubes.setter
    def tubes(self, array: List[Tube]):
        if array is not None:
            self['tubes'] = Tube.revert_tubes(array=array)
        self.__tubes = array

    #
    #   Factory
    #
    @classmethod
    def parse_season(cls, season: Any):  # -> Optional[Season]:
        if season is None:
            return None
        elif isinstance(season, Season):
            return season
        elif isinstance(season, Mapper):
            season = season.dictionary
        return Season(info=season)


class VideoDBI(ABC):

    @abstractmethod
    async def save_season(self, season: Season, url: URI) -> bool:
        raise NotImplemented

    @abstractmethod
    async def load_season(self, url: URI) -> Optional[Season]:
        raise NotImplemented

    @abstractmethod
    async def save_search_results(self, results: List[URI], keywords: str) -> bool:
        raise NotImplemented

    @abstractmethod
    async def load_search_results(self, keywords: str) -> Tuple[Optional[List[URI]], Optional[DateTime]]:
        raise NotImplemented
