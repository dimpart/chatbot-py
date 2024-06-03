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

import threading
from typing import Optional, Tuple, Set, Dict

from dimples import URI, DateTime


class LiveSource:
    """ M3U8 """

    EXPIRES = 3600 * 6

    def __init__(self, url: URI, available: bool = None, now: DateTime = None):
        super().__init__()
        self.__url = url
        self.__valid = available
        self.__time = DateTime.now() if now is None else now

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s time="%s" available=%s url="%s" />' % (cname, self.time, self.available, self.url)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s time="%s" available=%s url="%s" />' % (cname, self.time, self.available, self.url)

    @property
    def url(self) -> URI:
        """ m3u8 """
        return self.__url

    @property
    def available(self) -> Optional[bool]:
        return self.__valid

    @property
    def time(self) -> DateTime:
        return self.__time

    def set_available(self, valid: bool, now: DateTime = None):
        self.__valid = valid
        self.__time = DateTime.now() if now is None else now

    def is_expired(self, now: DateTime = None) -> bool:
        if now is None:
            now = DateTime.now()
        return now > (self.__time + self.EXPIRES)


class LiveChannel:
    """ TV Channel """

    def __init__(self, name: str):
        super().__init__()
        self.__name = name
        self.__sources: Dict[URI, LiveSource] = {}

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        count = len(self.__sources)
        return '<%s title="%s" count=%d />' % (cname, self.name, count)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        count = len(self.__sources)
        return '<%s title="%s" count=%d />' % (cname, self.name, count)

    @property
    def name(self) -> str:
        """ channel name """
        return self.__name

    @property
    def sources(self) -> Set[LiveSource]:
        """ channel sources """
        return set(self.__sources.values())

    @property
    def available(self) -> bool:
        """ source(s) available """
        sources = self.sources
        for src in sources:
            if src.available:
                return True
        # channel not available
        return False

    def add_source(self, source: LiveSource):
        self.__sources[source.url] = source


class LiveParser:

    def __init__(self):
        super().__init__()
        # caches
        self.__sources: Dict[URI, LiveSource] = {}
        self.__channels: Dict[str, LiveChannel] = {}

    def get_source(self, url: URI) -> LiveSource:
        source = self.__sources.get(url)
        if source is None:
            source = LiveSource(url=url)
            self.__sources[url] = source
        return source

    def get_channel(self, name: str) -> LiveChannel:
        channel = self.__channels.get(name)
        if channel is None:
            channel = LiveChannel(name=name)
            self.__channels[name] = channel
        return channel

    def parse_channels(self, text: str) -> Set[LiveChannel]:
        all_channels = set()
        array = text.splitlines()
        for line in array:
            # parse line
            name, sources = self._parse_sources(line=line)
            if name is None or len(sources) == 0:
                continue
            # create channel with name
            channel = self.get_channel(name=name)
            # add sources to the channel
            for src in sources:
                channel.add_source(source=src)
            # OK
            all_channels.add(channel)
        # done!
        return all_channels

    def _parse_sources(self, line: str) -> Tuple[Optional[str], Set[LiveSource]]:
        if line is None or len(line) == 0:
            return None, set()
        else:
            line = line.strip()
        # check channel line
        pos = line.find(',http')
        if pos < 1:
            return None, set()
        else:
            name = line[:pos].strip()
            pos += 1  # skip ','
            text = line[pos:]
        # check sources
        sources: Set[LiveSource] = set()
        while True:
            pos = text.find('#http')
            if pos > 0:
                # split for next url
                sources.add(self.get_source(url=text[:pos]))
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
            sources.add(self.get_source(url=text))
            break
        # OK
        return name, sources


class LockedParser(LiveParser):

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()

    # Override
    def get_source(self, url: URI) -> LiveSource:
        with self.__lock:
            return super().get_source(url=url)

    # Override
    def get_channel(self, name: str) -> LiveChannel:
        with self.__lock:
            return super().get_channel(name=name)
