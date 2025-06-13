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

from abc import ABC, abstractmethod
from typing import Optional, List

from dimples import URI


class EpisodeInfo:

    def __init__(self, page: URI, title: str):
        super().__init__()
        self.__page = page
        self.__title = title

    @property
    def page(self) -> URI:
        return self.__page

    @property
    def title(self) -> str:
        return self.__title


class TubeInfo:

    def __init__(self, title: str, episodes: List[EpisodeInfo]):
        super().__init__()
        self.__title = title
        self.__episodes = episodes

    @property
    def title(self) -> str:
        return self.__title

    @property
    def episodes(self) -> List[EpisodeInfo]:
        return self.__episodes


class SeasonInfo:

    def __init__(self, page: URI, name: str, cover: Optional[URI], tags: Optional[str]):
        super().__init__()
        self.__page = page
        self.__name = name
        self.__cover = cover
        self.__tags = tags

    @property
    def page(self) -> URI:
        return self.__page

    @property
    def name(self) -> str:
        return self.__name

    @property
    def cover(self) -> Optional[URI]:
        return self.__cover

    @property
    def tags(self) -> Optional[str]:
        return self.__tags

    def copy(self):
        return SeasonInfo(page=self.page, name=self.name, cover=self.cover, tags=self.tags)


class Parser(ABC):

    @abstractmethod
    def full_url(self, path: Optional[str]) -> Optional[str]:
        raise NotImplemented

    #
    #   Search Result Page
    #

    @abstractmethod
    def fetch_total_seasons(self, html: str) -> int:
        """ parse for total count """
        raise NotImplemented

    @abstractmethod
    def parse_seasons(self, html: str) -> List[SeasonInfo]:
        """ parse season for page URL, name and cover URL """
        raise NotImplemented

    #
    #   Season Detail Page
    #

    @abstractmethod
    def fetch_season_name(self, html: str) -> Optional[str]:
        """ parse for season name """
        raise NotImplemented

    @abstractmethod
    def fetch_season_cover(self, html: str) -> Optional[URI]:
        """ parse for season cover """
        raise NotImplemented

    @abstractmethod
    def fetch_season_description(self, html: str) -> Optional[str]:
        """ parse for season details """
        raise NotImplemented

    @abstractmethod
    def parse_tubes(self, html: str) -> List[TubeInfo]:
        """ parse tube for title and episodes """
        raise NotImplemented

    @abstractmethod
    def parse_episodes(self, tube_html: str) -> List[EpisodeInfo]:
        """ parse episodes for page URL and title """
        raise NotImplemented

    #
    #   Episode Play Page
    #

    @abstractmethod
    def fetch_episode_title(self, html: str) -> Optional[str]:
        """ parse for episode title """
        raise NotImplemented

    @abstractmethod
    def fetch_m3u8(self, html: str) -> Optional[URI]:
        """ parse for m3u8 URL """
        raise NotImplemented
