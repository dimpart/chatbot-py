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
from .factory import LiveStreamFactory
from .channel import LiveChannel
from .genre import LiveGenre


class LiveParser:

    def __init__(self):
        super().__init__()
        self.__factory = LiveStreamFactory()

    @property
    def stream_factory(self) -> LiveStreamFactory:
        return self.__factory

    def get_stream(self, url: URI, label: Optional[str]) -> Optional[LiveStream]:
        return self.stream_factory.get_stream(url=url, label=label)

    def parse(self, text: str) -> List[LiveGenre]:
        lines = text.splitlines()
        return self.parse_lines(lines=lines)

    # protected
    def parse_lines(self, lines: List[str]) -> List[LiveGenre]:
        all_groups: List[LiveGenre] = []
        current = LiveGenre(title='')
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
                if len(current.channels) > 0:
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
                url, label = self._split_stream(text=src)
                if url is None:
                    continue
                m3u8 = self.get_stream(url=url, label=label)
                if m3u8 is not None:
                    streams.add(m3u8)
            channel.add_streams(streams=streams)
            current.add_channel(channel=channel)
        # add last group
        if len(current.channels) > 0:
            all_groups.append(current)
        return all_groups

    # noinspection PyMethodMayBeStatic
    def _fetch_genre(self, text: str) -> Optional[LiveGenre]:
        title = split_genre(text=text)
        if title is None:
            return None
        return LiveGenre(title=title)

    # noinspection PyMethodMayBeStatic
    def _fetch_channel(self, text: str) -> Tuple[Optional[LiveChannel], str]:
        name, body = split_channel(text=text)
        if name is None:
            return None, text
        return LiveChannel(name=name), body

    # noinspection PyMethodMayBeStatic
    def _split_stream(self, text: str) -> Tuple[Optional[URI], Optional[str]]:
        url, label = split_stream(text=text)
        return url, label


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
    pair = text.split(r'$')
    if len(pair) == 1:
        url = text.strip()
        if url.find(r'://') > 0:
            return url, None
        # error
        return None, None
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
    else:
        # error
        return None, None
    # OK
    if len(label) == 0:
        return url, None
    else:
        return url, label
