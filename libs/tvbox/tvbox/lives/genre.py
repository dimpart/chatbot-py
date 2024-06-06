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
from .channel import LiveChannel


class LiveGenre(MapInfo):
    """ Channel Group """

    def __init__(self, info: Dict = None, title: str = None):
        """
        Create Channel Group

        :param info:  group info
        :param title: group name
        """
        super().__init__(info=info)
        if title is not None:
            self.set(key='title', value=title)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        channels = self.get(key='channels', default=[])
        count = len(channels)
        return '<%s title="%s" count=%d />' % (cname, self.title, count)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        channels = self.get(key='channels', default=[])
        count = len(channels)
        return '<%s title="%s" count=%d />' % (cname, self.title, count)

    @property
    def title(self) -> str:
        """ group name """
        return self.get(key='title', default='')

    @property
    def channels(self) -> List[LiveChannel]:
        """ live channels """
        array = self.get(key='channels', default=[])
        return LiveChannel.convert(array=array)

    @channels.setter
    def channels(self, array: Iterable[LiveChannel]):
        value = LiveChannel.revert(channels=array)
        self.set(key='channels', value=value)

    def add_channel(self, channel: LiveChannel):
        """ add the channel in this genre """
        all_channels = self.channels
        for old in all_channels:
            if old.name == channel.name:
                # same channel, merge streams
                old.add_streams(streams=channel.streams)
                return True
        all_channels.append(channel)
        self.channels = all_channels
        return True

    def add_channels(self, channels: Iterable[LiveChannel]):
        """ all channels in this genre """
        all_channels = self.channels
        count = 0
        for item in channels:
            found = False
            for old in all_channels:
                if old.name == item.name:
                    # same channel, merge streams
                    old.add_streams(streams=item.streams)
                    found = True
                    break
            if not found:
                all_channels.append(item)
                count += 1
        if count > 0:
            self.channels = all_channels
            return True

    #
    #   Factories
    #

    @classmethod
    def parse(cls, info: Any):  # -> Optional[LiveGenre]:
        if info is None:
            return None
        elif isinstance(info, LiveGenre):
            return info
        elif isinstance(info, MapInfo):
            info = info.dictionary
        if 'title' in info:
            return cls(info=info)

    @classmethod
    def convert(cls, array: Iterable[Dict]):  # -> List[LiveGenre]:
        groups: List[LiveGenre] = []
        for item in array:
            info = cls.parse(info=item)
            if info is not None:
                groups.append(info)
        return groups

    @classmethod
    def revert(cls, genres: Iterable) -> List[Dict]:
        array: List[Dict] = []
        for item in genres:
            if isinstance(item, MapInfo):
                array.append(item.dictionary)
            elif isinstance(item, Dict):
                array.append(item)
        return array
