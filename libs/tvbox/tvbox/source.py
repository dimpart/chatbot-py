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

import asyncio
from typing import Optional, Union, Set, List, Dict

from .types import URI
from .utils import Logging, DateTime
from .utils import http_get_text
from .utils import text_file_read, text_file_write, json_file_write

from .lives import LiveStream, LiveChannel, LiveGenre

from .config import LiveConfig
from .scanner import ScanContext, ScanEventHandler


class SourceLoader:

    def __init__(self):
        super().__init__()
        self.__resources: Dict[str, str] = {}

    def clear_caches(self):
        self.__resources.clear()

    async def load_text(self, src: Union[str, URI]) -> Optional[str]:
        # 1. check caches
        res = self.__resources.get(src)
        if res is None:
            # 2. cache not found, try to load
            res = await _load(src=src)
            if res is None:
                res = ''  # place holder
            # 3. cache the result
            self.__resources[src] = res
        # OK
        if len(res) > 0:
            return res


async def _load(src: Union[str, URI]) -> Optional[str]:
    if src.find(r'://') > 0:
        return await http_get_text(url=src, timeout=64)
    else:
        return await text_file_read(path=src)


class PreScanner(Logging):

    BATCH = 50

    async def scan_genres(self, context: ScanContext, genres: List[LiveGenre]):
        """ scan all streams in these genres batch by batch """
        all_streams: Set[LiveStream] = set()
        for group in genres:
            channels = group.channels
            for item in channels:
                streams = item.streams
                for src in streams:
                    all_streams.add(src)
        count = len(all_streams)
        index = 0
        sources: Set[LiveStream] = set()
        self.info(msg='pre-scanning %d stream(s) in %d genre(s) ...' % (count, len(genres)))
        for src in all_streams:
            index += 1
            self.info(msg='pre-scanning stream (%d/%d) %s' % (index, count, src.url))
            sources.add(src)
            if len(sources) >= self.BATCH:
                await self.scan_streams(context=context, streams=sources)
                sources.clear()
        if len(sources) > 0:
            await self.scan_streams(context=context, streams=sources)

    # protected
    async def scan_streams(self, context: ScanContext, streams: Set[LiveStream]):
        timeout = context.timeout
        now = DateTime.current_timestamp()
        tasks = [src.check(now=now, timeout=timeout) for src in streams]
        done, _ = await asyncio.wait(tasks)
        results = [item.result() for item in done if item.result()]
        self.info(msg='pre-scanned %d stream(s) => %d result(s)' % (len(tasks), len(results)))


class LiveHandler(ScanEventHandler, Logging):
    """ Live Storage """

    def __init__(self, config: LiveConfig):
        super().__init__()
        self.__config = config
        self.__scanner = PreScanner()

    @property
    def config(self) -> LiveConfig:
        return self.__config

    @property
    def batch_scanner(self) -> PreScanner:
        return self.__scanner

    @batch_scanner.setter
    def batch_scanner(self, scanner: PreScanner):
        self.__scanner = scanner

    #
    #   Storage
    #

    async def update_index(self, lives: List[Dict]) -> bool:
        """ update 'tvbox.json' """
        path = self.config.get_output_index_path()
        if path is None or len(lives) == 0:
            self.warning(msg='ignore live index: %s => %s' % (path, lives))
            return False
        self.info(msg='saving index file: %d live urls -> %s' % (len(lives), path))
        return await json_file_write(path=path, container={
            'lives': lives,
        })

    async def update_lives(self, genres: List[LiveGenre], url: URI) -> bool:
        path = self.config.get_output_lives_path(url=url)
        if path is None or len(genres) == 0:
            self.warning(msg='ignore live urls: %s => %s' % (url, genres))
            return False
        count = 0
        text = ''
        for group in genres:
            array: List[str] = []
            channels = group.channels
            for item in channels:
                # get valid stream sources
                streams = item.streams
                sources: List[URI] = [src.url for src in streams if src.available]
                if len(sources) == 0:
                    self.warning(msg='empty channel: "%s" -> %s' % (item.name, streams))
                    continue
                line = '#'.join(sources)
                line = '%s,%s' % (item.name, line)
                array.append(line)
                count += 1
            if len(array) == 0:
                self.warning(msg='empty genre: "%s" -> %s' % (group.title, channels))
                continue
            text += '\n%s,#genre#\n' % group.title
            text += '\n%s\n' % '\n'.join(array)
        # OK
        self.info(msg='saving lives file: %d genres, %d channels, %s -> %s' % (len(genres), count, url, path))
        if len(text) > 0:
            return await text_file_write(path=path, text=text)

    async def update_source(self, text: str, url: URI) -> bool:
        path = self.config.get_output_source_path(url=url)
        if path is None:
            self.warning(msg='ignore index file: %s => %s' % (url, text))
            return False
        self.info(msg='saving source file: %d lines -> %s' % (len(text.splitlines()), path))
        if len(text) > 0:
            return await text_file_write(path=path, text=text)

    #
    #   ScanEventHandler
    #

    # Override
    async def on_scan_start(self, context: ScanContext, genres: List[LiveGenre]):
        # count all streams
        total_streams = 0
        for group in genres:
            channels = group.channels
            for item in channels:
                total_streams += len(item.streams)
        context.set(key='stream_total_count', value=total_streams)
        # pre scanning
        scanner = self.batch_scanner
        await scanner.scan_genres(context=context, genres=genres)

    # Override
    async def on_scan_finished(self, context: ScanContext, genres: List[LiveGenre]):
        self.info(msg='Mission accomplished.')

    # genre events

    # Override
    async def on_scan_genre_start(self, context: ScanContext, genre: LiveGenre):
        pass

    # Override
    async def on_scan_genre_finished(self, context: ScanContext, genre: LiveGenre):
        pass

    # channel events

    # Override
    async def on_scan_channel_start(self, context: ScanContext, genre: LiveGenre, channel: LiveChannel):
        pass

    # Override
    async def on_scan_channel_finished(self, context: ScanContext, genre: LiveGenre, channel: LiveChannel):
        pass

    # stream events

    # Override
    async def on_scan_stream_start(self, context: ScanContext, channel: LiveChannel, stream: LiveStream):
        pass

    # Override
    async def on_scan_stream_finished(self, context: ScanContext, channel: LiveChannel, stream: LiveStream):
        offset = context.get(key='stream_offset', default=0)
        total = context.get(key='stream_total_count', default=0)
        self.info(msg='Scanned (%d/%d) stream: "%s"\t-> %s' % (offset + 1, total, channel.name, stream))
