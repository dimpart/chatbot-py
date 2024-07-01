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

from typing import Optional, Union, List, Dict

from .types import URI
from .utils import Logging, DateTime

from .config import LiveConfig
from .lives import LiveParser
from .scanner import LiveScanner, ScanContext
from .source import SourceLoader, LiveScanHandler
from .item import LiveSet


class LiveLoader(Logging):

    def __init__(self, config: LiveConfig, parser: LiveParser, scanner: LiveScanner):
        super().__init__()
        self.__config = config
        self.__parser = parser
        self.__scanner = scanner
        self.__loader = self._create_source_loader()

    @property
    def config(self) -> LiveConfig:
        return self.__config

    @property
    def parser(self) -> LiveParser:
        return self.__parser

    @property
    def scanner(self) -> LiveScanner:
        return self.__scanner

    @property
    def loader(self) -> SourceLoader:
        return self.__loader

    # noinspection PyMethodMayBeStatic
    def _create_source_loader(self) -> SourceLoader:
        # TODO: override for customized loader
        return SourceLoader()

    def clear_caches(self):
        self.loader.clear_caches()

    #
    #   Load
    #

    async def get_live_set(self) -> LiveSet:
        return await LiveSet.load(config=self.config, loader=self.loader)

    async def _load_resource(self, src: Union[str, URI]) -> Optional[str]:
        self.info(msg='loading resource from: "%s"' % src)
        res = await self.loader.load_text(src=src)
        if res is None:
            self.error(msg='failed to load resource: "%s"' % src)
        return res

    #
    #   Running
    #

    async def load(self, handler: LiveScanHandler, context: ScanContext):
        parser = self.parser
        scanner = self.scanner
        available_lives: List[Dict] = []
        # scan lives
        start_time = DateTime.current_timestamp()
        live_set = await self.get_live_set()
        lives = live_set.lives
        self.info(msg='got live set: %d, %s' % (len(lives), lives))
        for item in lives:
            url = item.get('url')
            #
            #  1. load text file
            #
            text = await self._load_resource(src=url)
            if text is None:
                self.error(msg='ignore lives: %s' % url)
                continue
            else:
                await handler.update_source(text=text, url=url)
            count = len(text.splitlines())
            self.info(msg='scanning lives: %s => %d lines' % (url, count))
            #
            #  2. parse channel groups
            #
            genres = parser.parse(text=text)
            if len(genres) == 0:
                self.warning(msg='ignore empty lives: %s => %d lines' % (url, count))
                continue
            #
            #  3. parse channel groups
            #
            available_genres = await scanner.scan(genres=genres, context=context, handler=handler)
            if len(available_genres) == 0:
                cnt = len(genres)
                self.warning(msg='ignore empty lives: %s => %d lines, %d genres' % (url, count, cnt))
                continue
            else:
                # update 'lives.txt'
                await handler.update_lives(genres=available_genres, url=url)
            # append to 'lives'
            info = item.copy()
            if 'origin' not in item:
                info['origin'] = {
                    'url': url,
                }
            _update_counts(info, context=context)
            info['url'] = self.config.get_output_lives_url(url=url)
            info['path'] = self.config.get_output_lives_path(url=url)
            info['src'] = url
            # OK
            available_lives.append(info)
        # mission accomplished
        end_time = DateTime.current_timestamp()
        return await handler.update_index(container={
            'lives': available_lives,
            'scan_time': DateTime.full_string(timestamp=start_time),
            'update_time': DateTime.full_string(timestamp=end_time),
        })


def _update_counts(info: Dict, context: ScanContext):
    origin = info.get('origin')
    if isinstance(origin, Dict):
        if 'channel_total_count' not in origin:
            origin['channel_total_count'] = context.get(key='channel_total_count')
        if 'stream_total_count' not in origin:
            origin['stream_total_count'] = context.get(key='stream_total_count')
    info['available_channel_count'] = context.get(key='available_channel_count')
    info['available_stream_count'] = context.get(key='available_stream_count')
