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

from abc import ABC, abstractmethod
from typing import Optional, Set, List, Dict

from ..types import URI


class LiveTranslator(ABC):

    @abstractmethod
    def translate(self, text: str) -> Optional[str]:
        raise NotImplemented


class M3UInfo:

    def __init__(self, group: str, name: str, url: URI):
        super().__init__()
        self.__group = group
        self.__name = name
        self.__url = url

    @property
    def group(self) -> str:
        return self.__group

    @property
    def name(self) -> str:
        return self.__name

    @property
    def url(self) -> URI:
        return self.__url


class M3UTranslator(LiveTranslator):

    # noinspection PyMethodMayBeStatic
    def check(self, text: str) -> bool:
        return check_m3u(text=text)

    # noinspection PyMethodMayBeStatic
    def _split_items(self, text: str) -> List[str]:
        return split_m3u(text=text)

    # noinspection PyMethodMayBeStatic
    def _parse_info(self, lines: str) -> Optional[M3UInfo]:
        return parse_inf(lines=lines)

    def _parse_items(self, array: List[str]) -> Dict[str, Dict[str, Set[URI]]]:
        genres = {}
        for item in array:
            info = self._parse_info(item)
            if info is None:
                continue
            # get channels with group title
            channels: Dict = genres.get(info.group)
            if channels is None:
                channels = {}
                genres[info.group] = channels
            # get streams with channel name
            streams: Set = channels.get(info.name)
            if streams is None:
                streams = set()
                channels[info.name] = streams
            # add stream url
            streams.add(info.url)
        return genres

    # noinspection PyMethodMayBeStatic
    def _build_channel_line(self, name: str, streams: Set[URI]) -> str:
        text = '#'.join(streams)
        if len(text) < 2:
            return ''
        return '%s,%s' % (name, text)

    def _build_genre_block(self, title: str, channels: Dict[str, Set[URI]]) -> str:
        text = '\n'
        for name in channels:
            streams = channels[name]
            line = self._build_channel_line(name=name, streams=streams)
            text += '%s\n' % line
        if len(text) < 2:
            return ''
        return '%s,#genre#\n%s' % (title, text)

    # Override
    def translate(self, text: str) -> Optional[str]:
        if self.check(text=text):
            array = self._split_items(text=text)
            genres = self._parse_items(array=array)
            blocks: List[str] = []
            for title in genres:
                channels = genres[title]
                text = self._build_genre_block(title=title, channels=channels)
                blocks.append(text)
            if len(blocks) > 0:
                return '\n'.join(blocks)


"""
#EXTM3U x-tvg-url="https://live.x.com/e.xml"
#EXTINF:-1 tvg-name="CCTV1" tvg-logo="https://live.x.com/CCTV1.png" group-title="央视频道",CCTV-1 综合
http://1.2.3.4:81/CCTV1/index.m3u8
#EXTINF:-1 tvg-name="CCTV2" tvg-logo="https://live.x.com/CCTV2.png" group-title="央视频道",CCTV-2 财经
http://1.2.3.4:81/CCTV2/index.m3u8
...
"""


def check_m3u(text: str) -> bool:
    if text.find(r'#EXTM3U') < 0:
        return False
    elif text.find(r'#EXTINF') < 0:
        return False
    elif text.find(r' tvg-name="') < 0:
        return False
    elif text.find(r' group-title="') < 0:
        return False
    else:
        return True


def split_m3u(text: str) -> List[str]:
    array = []
    pos = text.find(r'#EXTINF')
    while pos > 0:
        text = text[pos:]
        pos = text.find(r'#EXTINF', 7)
        if pos < 0:
            array.append(text)
            break
        else:
            array.append(text[:pos])
    return array


def parse_inf(lines: str) -> Optional[M3UInfo]:
    array = lines.splitlines()
    if len(array) < 2:
        return None
    head = array[0]
    # get stream url
    url = array[1].strip()
    if url.find(r'://') < 0:
        return None
    # get channel name
    pos = head.rfind(r',')
    if pos > 0 and head.find(r'"', pos) < 0:
        pos += 2
        name = head[pos:]
    else:
        name = fetch_field(text=head, tag_start=' tvg-name="', tag_end='"')
        if name is None:
            name = fetch_field(text=head, tag_start=' tvg-id="', tag_end='"')
            if name is None:
                return None
    # get group title
    group = fetch_field(text=head, tag_start=' group-title="', tag_end='"')
    if group is None:
        group = 'Default'
    return M3UInfo(group=group, name=name, url=url)


def fetch_field(text: str, tag_start: str, tag_end: str) -> Optional[str]:
    start = text.find(tag_start)
    if start < 0:
        return None
    start += len(tag_start)
    end = text.find(tag_end, start)
    if end > start:
        return text[start:end]
