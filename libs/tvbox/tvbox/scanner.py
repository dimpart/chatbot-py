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
from typing import Optional, List, Dict

from .types import MapInfo

from .lives import LiveStream, LiveChannel, LiveGenre
from .lives import LiveStreamScanner
from .lives import LiveParser


class ScanContext(MapInfo):

    def __init__(self, info: Dict = None, timeout: float = None):
        super().__init__(info=info)
        if timeout is not None and timeout > 0:
            self.set(key='timeout', value=timeout)

    @property
    def timeout(self) -> Optional[float]:
        return self.get(key='timeout')

    @timeout.setter
    def timeout(self, duration: float):
        self.set(key='timeout', value=duration)

    @property
    def cancelled(self) -> bool:
        flag = self.get(key='cancelled')
        if flag is None:
            flag = self.get(key='stopped', default=False)
        return flag

    @cancelled.setter
    def cancelled(self, flag: bool):
        self.set(key='cancelled', value=flag)


class ScanEventHandler(ABC):
    """ Scan callback """

    @abstractmethod
    async def on_scan_start(self, context: ScanContext, genres: List[LiveGenre]):
        raise NotImplemented

    @abstractmethod
    async def on_scan_finished(self, context: ScanContext, genres: List[LiveGenre]):
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
        self.__parser = self._create_live_parser()
        self.__scanner = self._create_stream_scanner()

    # noinspection PyMethodMayBeStatic
    def _create_live_parser(self) -> LiveParser:
        # TODO: override for customized parser
        return LiveParser()

    # noinspection PyMethodMayBeStatic
    def _create_stream_scanner(self) -> LiveStreamScanner:
        # TODO: override for customized scanner
        return LiveStreamScanner()

    @property  # protected
    def live_parser(self) -> LiveParser:
        return self.__parser

    @property  # protected
    def stream_scanner(self) -> LiveStreamScanner:
        return self.__scanner

    async def scan(self, text: str, context: ScanContext, handler: ScanEventHandler) -> List[LiveGenre]:
        """ Get non-empty channel groups """
        all_genres = self.live_parser.parse(text=text)
        # reset pointers
        context.set(key='genre_offset', value=0)
        context.set(key='channel_offset', value=0)
        context.set(key='stream_offset', value=0)
        # start mission
        await handler.on_scan_start(context=context, genres=all_genres)
        groups = await self._scan_genres(genres=all_genres, context=context, handler=handler)
        # mission accomplished
        await handler.on_scan_finished(context=context, genres=all_genres)
        return groups

    async def _scan_genres(self, genres: List[LiveGenre],
                           context: ScanContext, handler: ScanEventHandler) -> List[LiveGenre]:
        """ Get non-empty genres """
        groups: List[LiveGenre] = []
        context.set(key='genre_count', value=len(genres))
        # positions
        offset = context.get(key='genre_offset', default=0)
        index = 0
        for item in genres:
            if context.cancelled:
                break
            else:
                context.set(key='genre_index', value=index)
            # scan genre start
            await handler.on_scan_genre_start(context=context, genre=item)
            channels = await self._scan_channels(channels=item.channels, genre=item, context=context, handler=handler)
            item.channels = channels
            if len(channels) > 0:
                groups.append(item)
            # scan genre finished
            await handler.on_scan_genre_finished(context=context, genre=item)
            index += 1
            offset += 1
            context.set(key='genre_offset', value=offset)
        return groups

    async def _scan_channels(self, channels: List[LiveChannel], genre: LiveGenre,
                             context: ScanContext, handler: ScanEventHandler) -> List[LiveChannel]:
        """ Get available channels in this genre """
        available_channels: List[LiveChannel] = []
        context.set(key='channel_count', value=len(channels))
        # positions
        offset = context.get(key='channel_offset', default=0)
        index = 0
        for item in channels:
            if context.cancelled:
                break
            else:
                context.set(key='channel_index', value=index)
            # scan channel start
            await handler.on_scan_channel_start(context=context, genre=genre, channel=item)
            streams = await self._scan_streams(streams=item.streams, channel=item, context=context, handler=handler)
            item.streams = streams
            if len(streams) > 0:
                available_channels.append(item)
            # scan channel finished
            await handler.on_scan_channel_finished(context=context, genre=genre, channel=item)
            index += 1
            offset += 1
            context.set(key='channel_offset', value=offset)
        return available_channels

    async def _scan_streams(self, streams: List[LiveStream], channel: LiveChannel,
                            context: ScanContext, handler: ScanEventHandler) -> List[LiveStream]:
        """ Get available streams in this channel """
        available_streams: List[LiveStream] = []
        context.set(key='stream_count', value=len(streams))
        # positions
        offset = context.get(key='stream_offset', default=0)
        index = 0
        for item in streams:
            if context.cancelled:
                break
            else:
                context.set(key='stream_index', value=index)
            # scan stream start
            await handler.on_scan_stream_start(context=context, channel=channel, stream=item)
            src = await self.stream_scanner.scan_stream(stream=item, timeout=context.timeout)
            if src is not None:  # and src.available:
                available_streams.append(src)
            # scan stream finished
            await handler.on_scan_stream_finished(context=context, channel=channel, stream=item)
            index += 1
            offset += 1
            context.set(key='stream_offset', value=offset)
        return available_streams
