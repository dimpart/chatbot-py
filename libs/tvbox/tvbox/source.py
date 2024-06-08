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

import requests
from aiou import TextFile, JSONFile

from .types import URI
from .utils import Log, Logging

from .lives import LiveStream, LiveChannel, LiveGenre

from .config import LiveConfig
from .scanner import ScanContext, ScanEventHandler


class SourceLoader:

    def __init__(self):
        super().__init__()
        self.__resources: Dict[str, str] = {}

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
        return await _http_get(url=src)
    else:
        return await _file_read(path=src)


async def _file_read(path: str) -> Optional[str]:
    try:
        return await TextFile(path=path).read()
    except Exception as error:
        Log.error(msg='failed to read file: %s, error: %s' % (path, error))


async def _http_get(url: URI) -> Optional[str]:
    try:
        response = requests.get(url)
        encoding = response.encoding
        if encoding is None or len(encoding) == 0:
            response.encoding = 'utf-8'
        elif encoding.upper() == 'ISO-8859-1':
            response.encoding = 'utf-8'
        return response.text
    except Exception as error:
        Log.error(msg='failed to get URL: %s, error: %s' % (url, error))


class LiveHandler(ScanEventHandler, Logging):
    """ Live Storage """

    def __init__(self, config: LiveConfig):
        super().__init__()
        self.__config = config

    @property
    def config(self) -> LiveConfig:
        return self.__config

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
        return await JSONFile(path=path).write(container={
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
        self.info(msg='saving lives file: %d genres, %d channels -> %s' % (len(genres), count, path))
        if len(text) > 0:
            return await TextFile(path=path).write(text=text)

    async def update_source(self, text: str, url: URI) -> bool:
        path = self.config.get_output_source_path(url=url)
        if path is None:
            self.warning(msg='ignore index file: %s => %s' % (url, text))
            return False
        self.info(msg='saving source file: %d lines -> %s' % (len(text.splitlines()), path))
        if len(text) > 0:
            return await TextFile(path=path).write(text=text)

    #
    #   ScanEventHandler
    #

    # Override
    async def on_scan_start(self, context: ScanContext):
        pass

    # Override
    async def on_scan_finished(self, context: ScanContext):
        pass

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
        offset = context.get_value(key='stream_offset', default=0)
        total = context.get_value(key='total_streams', default=0)
        self.info(msg='scanned (%d/%d) stream: "%s"\t-> %s' % (offset, total, channel.name, stream))
