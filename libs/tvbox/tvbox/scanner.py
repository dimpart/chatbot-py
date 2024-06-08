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
from typing import Optional, Any, Tuple, List, Dict

from .lives import LiveStream, LiveChannel, LiveGenre
from .lives import LiveStreamScanner
from .lives import LiveParser


class ScanContext:

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__()
        self.__vars: Dict[str, Any] = {} if params is None else params

    def get_value(self, key: str, default: Any = None) -> Optional[Any]:
        return self.__vars.get(key, default)

    def set_value(self, key: str, value: Optional[Any]):
        if value is None:
            self.__vars.pop(key, None)
        else:
            self.__vars[key] = value


class ScanEventHandler(ABC):
    """ Scan callback """

    @abstractmethod
    async def on_scan_start(self, context: ScanContext):
        raise NotImplemented

    @abstractmethod
    async def on_scan_finished(self, context: ScanContext):
        raise NotImplemented

    # genre events

    @abstractmethod
    async def on_scan_genre_start(self, context: ScanContext, genre: LiveGenre):
        raise NotImplemented

    @abstractmethod
    async def on_scan_genre_finished(self, context: ScanContext, genre: LiveGenre):
        raise NotImplemented

    # channel events

    @abstractmethod
    async def on_scan_channel_start(self, context: ScanContext, genre: LiveGenre, channel: LiveChannel):
        raise NotImplemented

    @abstractmethod
    async def on_scan_channel_finished(self, context: ScanContext, genre: LiveGenre, channel: LiveChannel):
        raise NotImplemented

    # stream events

    @abstractmethod
    async def on_scan_stream_start(self, context: ScanContext, channel: LiveChannel, stream: LiveStream):
        raise NotImplemented

    @abstractmethod
    async def on_scan_stream_finished(self, context: ScanContext, channel: LiveChannel, stream: LiveStream):
        raise NotImplemented


class LiveScanner:

    def __init__(self):
        super().__init__()
        self.__parser = LiveParser()
        self.__scanner = LiveStreamScanner()

    @property  # protected
    def live_parser(self) -> LiveParser:
        return self.__parser

    @property  # protected
    def stream_scanner(self) -> LiveStreamScanner:
        return self.__scanner

    async def scan(self, text: str, context: ScanContext, handler: ScanEventHandler) -> List[LiveGenre]:
        """ Get non-empty channel groups """
        groups: List[LiveGenre] = []
        genres = self.live_parser.parse(text=text)
        total_genres = len(genres)
        total_channels, total_streams = _count_channel_streams(genres=genres)
        # prepare scan context
        context.set_value(key='all_genres', value=genres)
        context.set_value(key='available_genres', value=groups)
        context.set_value(key='total_genres', value=total_genres)
        context.set_value(key='total_channels', value=total_channels)
        context.set_value(key='total_streams', value=total_streams)
        context.set_value(key='genre_offset', value=0)
        context.set_value(key='channel_offset', value=0)
        context.set_value(key='stream_offset', value=0)
        # start mission
        await handler.on_scan_start(context=context)
        context.set_value(key='genre_count', value=total_genres)
        # positions
        offset = 0  # context.get_value(key='genre_offset', default=0)
        index = 0
        for item in genres:
            context.set_value(key='genre_index', value=index)
            await handler.on_scan_genre_start(context=context, genre=item)
            # scan genre start
            channels = await self._scan_genre(genre=item, context=context, handler=handler)
            item.channels = channels
            if len(channels) > 0:
                groups.append(item)
            # scan genre finished
            await handler.on_scan_genre_finished(context=context, genre=item)
            # increase positions
            index += 1
            offset += 1
            context.set_value(key='genre_offset', value=offset)
        # mission accomplished
        await handler.on_scan_finished(context=context)
        return groups

    async def _scan_genre(self, genre: LiveGenre,
                          context: ScanContext, handler: ScanEventHandler) -> List[LiveChannel]:
        """ Get available channels in this genre """
        available_channels: List[LiveChannel] = []
        channels = genre.channels
        context.set_value(key='channel_count', value=len(channels))
        # positions
        offset = context.get_value(key='channel_offset', default=0)
        index = 0
        for item in channels:
            context.set_value(key='channel_index', value=index)
            await handler.on_scan_channel_start(context=context, genre=genre, channel=item)
            # scan channel start
            streams = await self._scan_channel(channel=item, context=context, handler=handler)
            item.streams = streams
            if len(streams) > 0:
                available_channels.append(item)
                cnt = context.get_value(key='available_channel_count', default=0)
                context.set_value(key='available_channel_count', value=(cnt + 1))
            # scan channel finished
            await handler.on_scan_channel_finished(context=context, genre=genre, channel=item)
            # increase positions
            index += 1
            offset += 1
            context.set_value(key='channel_offset', value=offset)
        return available_channels

    async def _scan_channel(self, channel: LiveChannel,
                            context: ScanContext, handler: ScanEventHandler) -> List[LiveStream]:
        """ Get available streams in this channel """
        available_streams: List[LiveStream] = []
        streams = channel.streams
        context.set_value(key='stream_count', value=len(streams))
        # positions
        offset = context.get_value(key='stream_offset', default=0)
        index = 0
        for item in streams:
            context.set_value(key='stream_index', value=index)
            await handler.on_scan_stream_start(context=context, channel=channel, stream=item)
            # scan stream start
            timeout = context.get_value(key='timeout', default=None)
            src = await self.stream_scanner.scan_stream(stream=item, timeout=timeout)
            if src is not None:  # and src.available:
                available_streams.append(src)
            # scan stream finished
            await handler.on_scan_stream_finished(context=context, channel=channel, stream=item)
            # increase positions
            index += 1
            offset += 1
            context.set_value(key='stream_offset', value=offset)
        return available_streams


def _count_channel_streams(genres: List[LiveGenre]) -> Tuple[int, int]:
    total_channels = 0
    total_streams = 0
    for group in genres:
        channels = group.channels
        for item in channels:
            total_channels += 1
            total_streams += len(item.streams)
    return total_channels, total_streams
