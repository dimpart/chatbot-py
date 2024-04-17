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

from typing import Optional, List

from dimples import URI


class Episode:

    def __init__(self, title: str, url: URI):
        super().__init__()
        self.__title = title
        self.__url = url

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
        return self.__title

    @property
    def url(self) -> URI:
        return self.__url


class Tube:

    def __init__(self, title: str, episodes: List[Episode]):
        super().__init__()
        self.__title = title
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
        return self.__title

    @property
    def episodes(self) -> List[Episode]:
        return self.__episodes


class Season:

    def __init__(self, name: str, cover: str, details: Optional[str], tubes: List[Tube]):
        super().__init__()
        self.__name = name
        self.__cover = cover
        self.__desc = details
        self.__tubes = tubes

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
    def name(self) -> str:
        return self.__name

    @property
    def cover(self) -> str:
        return self.__cover

    @property
    def details(self) -> Optional[str]:
        return self.__desc

    @property
    def tubes(self) -> List[Tube]:
        return self.__tubes
