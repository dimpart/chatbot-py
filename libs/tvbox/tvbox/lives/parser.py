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

    def get_stream(self, url: URI) -> Optional[LiveStream]:
        return self.stream_factory.get_stream(url=url)

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
            title = fetch_genre(text=text)
            if title is not None:
                # add current group
                if len(current.channels) > 0:
                    all_groups.append(current)
                # create next group
                current = LiveGenre(title=title)
                continue
            # 2. parse channel
            name, sources = fetch_channel(text=text)
            if name is None:
                # empty line?
                continue
            else:
                channel = LiveChannel(name=name)
            # 3. create streams
            streams: Set[LiveStream] = set()
            for src in sources:
                m3u8 = self.get_stream(url=src)
                if m3u8 is not None:
                    streams.add(m3u8)
            channel.add_streams(streams=streams)
            current.add_channel(channel=channel)
        # add last group
        if len(current.channels) > 0:
            all_groups.append(current)
        return all_groups


def fetch_genre(text: str) -> Optional[str]:
    """ get group title """
    pos = text.find(',#genre#')
    if pos >= 0:
        return text[:pos].strip()


def fetch_channel(text: str) -> Tuple[Optional[str], List[URI]]:
    """ get channel name & stream sources """
    pos = text.find(',http')
    if pos < 0:
        # not a channel line
        return None, []
    else:
        # fetch channel name
        name = text[:pos].strip()
        pos += 1  # skip ','
        text = text[pos:]
    # fetch sources
    return name, fetch_streams(text=text)


def fetch_streams(text: str) -> List[URI]:
    """ split steam sources with '#' """
    sources = []
    while True:
        pos = text.find('#http')
        if pos > 0:
            sources.append(text[:pos])
            pos += 1  # skip '#'
            text = text[pos:]
            continue
        # remove the tail
        pos = text.find('$')
        if pos > 0:
            text = text[:pos]
        else:
            text = text.rstrip()
        # last url
        sources.append(text)
        break
    return sources
