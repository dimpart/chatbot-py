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

from abc import ABC
from typing import Optional, List, Tuple

from dimples import URI, DateTime

from ..utils import md_esc, utf8_encode, base64_encode
from ..common import Season, VideoDBI

from .box import ChatBox


# noinspection PyAbstractClass
class VideoBox(ChatBox, ABC):

    @property
    def database(self) -> VideoDBI:
        archivist = self.facebook.archivist
        db = archivist.database
        assert isinstance(db, VideoDBI), 'database error: %s' % db
        return db

    async def save_season(self, season: Season, url: URI) -> bool:
        db = self.database
        return await db.save_season(season=season, url=url)

    async def load_season(self, url: URI) -> Optional[Season]:
        db = self.database
        return await db.load_season(url=url)

    async def save_search_results(self, results: List[URI], keywords: str) -> bool:
        db = self.database
        return await db.save_search_results(results=results, keywords=keywords)

    async def load_search_results(self, keywords: str) -> Tuple[Optional[List[URI]], Optional[DateTime]]:
        db = self.database
        return await db.load_search_results(keywords=keywords)


def build_season(season: Season, index: int, total: int) -> str:
    if total <= 5 or index < 3:
        return build_season_full(season=season, index=index, total=total)
    else:
        link = build_season_link(season=season, index=index, total=total)
    text = '(%d/%d) %s' % (index + 1, total, link)
    if total < 10 or index < 7:
        cover = season.cover
        if cover is not None:
            text = '![](%s "")\n\n%s' % (cover, text)
    return text


def build_season_link(season: Season, index: int, total: int) -> str:
    text = build_season_full(season=season, index=index, total=total)
    # "data:text/plain;charset=UTF-8;base64,"
    base64 = base64_encode(data=utf8_encode(string=text))
    href = 'data:text/plain;charset=UTF-8;base64,%s' % base64
    return '[%s](%s "")' % (season.name, href)


def build_season_full(season: Season, index: int, total: int) -> str:
    cover = season.cover
    name = md_esc(text=season.name)
    desc = season.details
    if desc is not None:
        desc = desc.replace('&nbsp;', ' ')
        desc = md_esc(text=desc)
    # headline
    if total == 1:
        text = '## **%s**\n' % name
    else:
        text = '## (%d/%d) **%s**\n' % (index + 1, total, name)
    # cover image
    if cover is not None:
        text += '![](%s "")\n' % cover
    # description
    if desc is not None:
        # text += '```\n%s\n```\n' % desc
        text += _build_desc(desc=desc)
    # show tubes
    name = md_esc(name)
    tubes = season.tubes
    for chapter in tubes:
        # tube name
        c_title = md_esc(text=chapter.title)
        text += '\n\n* **%s**' % c_title
        # show episodes
        episodes = chapter.episodes
        for item in episodes:
            i_title = md_esc(text=item.title)
            m3u8 = item.url
            if i_title.startswith(name):
                alt_text = i_title
            else:
                alt_text = '%s - %s' % (name, i_title)
            if cover is not None:
                alt_text += '; cover=%s' % cover
            text += ' > \\[[%s](%s "%s")\\]' % (i_title, m3u8, alt_text)
    return text


def _build_desc(desc: str) -> str:
    text = ''
    array = desc.strip().splitlines()
    for line in array:
        text += '> %s\n' % line
    return text
