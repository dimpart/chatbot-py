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

from typing import Any, List, Dict
from typing import Iterable

from ..types import MapInfo
from .stream import LiveStream


class LiveChannel(MapInfo):
    """ TV Channel """

    def __init__(self, info: Dict = None, name: str = None):
        """
        Create Live Channel

        :param info: channel info
        :param name: channel name
        """
        super().__init__(info=info)
        if name is not None:
            self.set(key='name', value=name)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        streams = self.get(key='streams', default=[])
        count = len(streams)
        return '<%s name="%s" count=%d />' % (cname, self.name, count)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        streams = self.get(key='streams', default=[])
        count = len(streams)
        return '<%s name="%s" count=%d />' % (cname, self.name, count)

    @property
    def name(self) -> str:
        """ channel name """
        return self.get(key='name', default='')

    @property
    def available(self) -> bool:
        """ source stream(s) available """
        sources = self.streams
        for src in sources:
            if src.available:
                return True
        # channel not available
        return False

    @property
    def streams(self) -> List[LiveStream]:
        """ channel sources """
        array = self.get(key='streams', default=[])
        return LiveStream.convert(array=array)

    @streams.setter
    def streams(self, array: Iterable[LiveStream]):
        value = LiveStream.revert(streams=array)
        self.set(key='streams', value=value)

    def add_stream(self, stream: LiveStream):
        """ add the stream in this channel """
        all_streams = self.streams
        for old in all_streams:
            if old.url == stream.url:
                # same source,
                # update info?
                return False
        all_streams.append(stream)
        self.streams = all_streams
        return True

    def add_streams(self, streams: Iterable[LiveStream]):
        """ add streams in this channel """
        all_streams = self.streams
        count = 0
        for item in streams:
            found = False
            for old in all_streams:
                if old.url == item.url:
                    # same source,
                    # update info?
                    found = True
                    break
            if not found:
                all_streams.append(item)
                count += 1
        if count > 0:
            self.streams = all_streams
            return True

    #
    #   Factories
    #

    @classmethod
    def parse(cls, info: Any):  # -> Optional[LiveChannel]:
        if info is None:
            return None
        elif isinstance(info, LiveChannel):
            return info
        elif isinstance(info, MapInfo):
            info = info.dictionary
        if 'name' in info:
            return cls(info=info)

    @classmethod
    def convert(cls, array: Iterable[Dict]):  # -> List[LiveChannel]:
        channels: List[LiveChannel] = []
        for item in array:
            info = cls.parse(info=item)
            if info is not None:
                channels.append(info)
        return channels

    @classmethod
    def revert(cls, channels: Iterable) -> List[Dict]:
        array: List[Dict] = []
        for item in channels:
            if isinstance(item, MapInfo):
                array.append(item.dictionary)
            elif isinstance(item, Dict):
                array.append(item)
        return array
