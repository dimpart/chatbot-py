# -*- coding: utf-8 -*-
#
#   TV-Box: Live Stream
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
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

from typing import Optional, Set, Tuple, List

from ..types import URI
from .stream import LiveStream
from .factory import LiveFactory
from .channel import LiveChannel
from .genre import LiveGenre


class LiveParser:

    def __init__(self):
        super().__init__()
        self.__factory = LiveFactory()

    @property
    def factory(self) -> LiveFactory:
        return self.__factory

    def parse(self, text: str) -> List[LiveGenre]:
        """ parse 'lives.txt' file content """
        lines = text.splitlines()
        return self.parse_lines(lines=lines)

    # protected
    def parse_lines(self, lines: List[str]) -> List[LiveGenre]:
        all_groups: List[LiveGenre] = []
        current = self.factory.new_genre(title='Default')
        for item in lines:
            text = item.strip()
            if len(text) == 0:
                continue
            elif text.startswith(r'#'):
                continue
            elif text.startswith(r'//'):
                continue
            # 1. check group name
            genre = self._fetch_genre(text=text)
            if genre is not None:
                # alternate current group
                if not current.empty:
                    all_groups.append(current)
                current = genre
                continue
            # 2. check channel name
            channel, text = self._fetch_channel(text=text)
            if channel is None:
                # empty line?
                continue
            else:
                # split streams
                sources = text.split(r'#')
            # 3. create streams
            streams: Set[LiveStream] = set()
            for src in sources:
                m3u8 = self._fetch_stream(text=src)
                if m3u8 is not None:
                    streams.add(m3u8)
            channel.add_streams(streams=streams)
            current.add_channel(channel=channel)
        # add last group
        if not current.empty:
            all_groups.append(current)
        return all_groups

    def _fetch_genre(self, text: str) -> Optional[LiveGenre]:
        title = split_genre(text=text)
        if title is None:
            return None
        return self.factory.new_genre(title=title)

    def _fetch_channel(self, text: str) -> Tuple[Optional[LiveChannel], str]:
        name, body = split_channel(text=text)
        if name is None:
            return None, text
        channel = self.factory.new_channel(name=name)
        return channel, body

    def _fetch_stream(self, text: str) -> Optional[LiveStream]:
        url, label = split_stream(text=text)
        if url is None:
            return None
        return self.factory.new_stream(url=url, label=label)


def split_genre(text: str) -> Optional[str]:
    pos = text.find(',#genre#')
    if pos > 0:
        return text[:pos].strip()


def split_channel(text: str) -> Tuple[Optional[str], str]:
    pos = text.find(',http')
    if pos < 0:
        # not a channel line
        return None, text
    # fetch channel name
    name = text[:pos].strip()
    pos += 1  # skip ','
    return name, text[pos:]


def split_stream(text: str) -> Tuple[Optional[URI], Optional[str]]:
    url = None
    label = None
    pair = text.split(r'$')
    if len(pair) == 1:
        url = text.strip()
        url = LiveStream.parse_url(url=url)
    else:
        # assert len(pair) == 2
        first = pair[0].strip()
        second = pair[1].strip()
        # check for url
        if first.find(r'://') > 0:
            url = first
            label = second
        elif second.find(r'://') > 0:
            url = second
            label = first
    # done
    return url, label
