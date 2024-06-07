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

from typing import Optional, Union, Any, Set, List, Dict

import requests

from aiou import Path
from aiou import TextFile, JSONFile

from .types import URI
from .utils import Log, Logging
from .utils import Config
from .utils import hex_md5, parse_json

from .lives import LiveStream, LiveChannel, LiveGenre
from .lives import LiveStreamScanner
from .lives import LiveParser


class ScanContext:

    def __init__(self):
        super().__init__()
        self.__vars: Dict[str, Any] = {}

    def get_value(self, key: str, default: Any = None) -> Optional[Any]:
        return self.__vars.get(key, default)

    def set_value(self, key: str, value: Optional[Any]):
        if value is None:
            self.__vars.pop(key, None)
        else:
            self.__vars[key] = value


class LiveScanner(Logging):

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

    async def scan(self, text: str, timeout: float) -> List[LiveGenre]:
        """ Get non-empty channel groups """
        groups: List[LiveGenre] = []
        genres = self.live_parser.parse(text=text)
        # prepare context
        total = _count_streams(genres=genres)
        context = ScanContext()
        context.set_value(key='stream_count', value=total)
        context.set_value(key='timeout', value=timeout)
        for item in genres:
            # scan for valid channels
            channels = await self._scan_genre(genre=item, context=context)
            if len(channels) > 0:
                item.channels = channels
                groups.append(item)
        return groups

    async def _scan_genre(self, genre: LiveGenre, context: ScanContext) -> List[LiveChannel]:
        """ Get available channels in this genre """
        available_channels: List[LiveChannel] = []
        channels = genre.channels
        for item in channels:
            # scan for valid streams
            streams = await self._scan_channel(channel=item, context=context)
            if len(streams) > 0:
                item.streams = streams
                available_channels.append(item)
        return available_channels

    async def _scan_channel(self, channel: LiveChannel, context: ScanContext) -> List[LiveStream]:
        """ Get available streams in this channel """
        scanner = self.stream_scanner
        available_streams: List[LiveStream] = []
        streams = channel.streams
        timeout = context.get_value(key='timeout', default=None)
        total = context.get_value(key='stream_count', default=0)
        for item in streams:
            offset = context.get_value(key='stream_offset', default=0) + 1
            context.set_value(key='stream_offset', value=offset)
            # scan stream source
            src = await scanner.scan_stream(stream=item, timeout=timeout)
            self.info(msg='scanned (%d/%d) stream: "%s"\t-> %s' % (offset, total, channel.name, item))
            if src is not None:  # and src.available:
                available_streams.append(src)
        return available_streams


class LiveLoader(Logging):

    def __init__(self, config: Config):
        super().__init__()
        self.__config = config
        self.__scanner = LiveScanner()
        # caches
        self.__resources: Dict[str, str] = {}

    @property
    def scanner(self) -> LiveScanner:
        return self.__scanner

    @property
    def config(self) -> Config:
        return self.__config

    @property
    def sources(self) -> List[URI]:
        array = self.config.get_option(section='tvbox', option='sources')
        return [] if array is None else array

    @property
    def lives(self) -> List[URI]:
        array = self.config.get_option(section='tvbox', option='lives')
        return [] if array is None else array

    @property
    def base_url(self) -> Optional[URI]:
        """ base url """
        return self.config.get_option(section='tvbox', option='base-url')

    @property
    def output_dir(self) -> Optional[str]:
        """ output directory """
        return self.config.get_option(section='tvbox', option='output-dir')

    def get_index_file(self) -> Optional[str]:
        return self.config.get_option(section='tvbox', option='index-file')

    def get_lives_file(self, url: URI) -> Optional[str]:
        file = self.config.get_option(section='tvbox', option='lives-file')
        if file is not None:
            digest = hex_md5(data=url)
            return file.replace(r'{HASH}', digest)

    def get_source_file(self, url: URI) -> Optional[str]:
        file = self.config.get_option(section='tvbox', option='source-file')
        if file is not None:
            digest = hex_md5(data=url)
            return file.replace(r'{HASH}', digest)

    #
    #   Output file path
    #

    def get_output_index_path(self) -> str:
        """ output index """
        file = self.get_index_file()
        return _join_path(base=self.output_dir, file=file)

    def get_output_lives_path(self, url: URI) -> str:
        """ output lives """
        file = self.get_lives_file(url=url)
        return _join_path(base=self.output_dir, file=file)

    def get_output_source_path(self, url: URI) -> str:
        file = self.get_source_file(url=url)
        return _join_path(base=self.output_dir, file=file)

    #
    #   Output URL
    #

    def get_output_index_url(self) -> Optional[URI]:
        file = self.get_index_file()
        return _join_path(base=self.base_url, file=file)

    def get_output_lives_url(self, url: URI):
        file = self.get_lives_file(url=url)
        return _join_path(base=self.base_url, file=file)

    #
    #   Running
    #

    async def run(self):
        scanner = self.scanner
        available_lives: List[Dict] = []
        # scan lives
        live_urls = await self._get_live_urls()
        self.info(msg='got live urls: %d, %s' % (len(live_urls), live_urls))
        for url in live_urls:
            text = await self._load_resource(src=url)
            if text is None:
                self.error(msg='ignore lives: %s' % url)
                continue
            else:
                path = self.get_output_source_path(url=url)
                if path is not None:
                    await _save_source(text=text, path=path)
            count = len(text.splitlines())
            self.info(msg='scanning lives: %s => %d lines' % (url, count))
            genres = await scanner.scan(text=text, timeout=64)
            path = self.get_output_lives_path(url=url)
            if path is None or len(genres) == 0:
                self.warning(msg='ignore empty lives: %s => %d lines' % (url, count))
                continue
            # update 'lives.txt'
            await _save_channels(genres=genres, path=path)
            available_lives.append({
                'url': self.get_output_lives_url(url=url),
                'src': url,
                'path': path,
            })
        # mission accomplished
        path = self.get_output_index_path()
        if path is None or len(available_lives) == 0:
            self.warning(msg='ignore empty live index: %s => %s' % (path, available_lives))
            return False
        # update 'tvbox.json'
        return await _save_index(lives=available_lives, path=path)

    async def _get_live_urls(self) -> Set[URI]:
        live_urls = set()
        # 1. get from "sources"
        sources = self.sources
        for src in sources:
            # 1.1. load
            text = await self._load_resource(src=src)
            if text is None:
                self.error(msg='failed to load resources: %s' % src)
                continue
            # 1.2. parse
            info = parse_json(text=text)
            if not isinstance(info, Dict):
                self.error(msg='json error: %s -> %s' % (src, text))
                continue
            # 1.3. get 'lives' from this source
            lives = info.get('lives')
            if not isinstance(lives, List):
                self.error(msg='json error: %s -> %s' % (src, text))
                continue
            # 1.4. add lives url
            for item in lives:
                url = _get_live_url(item=item)
                if len(url) == 0:
                    self.error(msg='lives item error: %s' % item)
                    continue
                elif url.find(r'://') < 0:
                    url = _join_path(base=src, file=url)
                live_urls.add(url)
        # 2. get from "lives"
        lives = self.lives
        for item in lives:
            url = _get_live_url(item=item)
            if url.find(r'://') < 0:
                self.error(msg='lives item error: %s' % item)
                continue
            live_urls.add(url)
        # OK
        return live_urls

    async def _load_resource(self, src: Union[str, URI]) -> Optional[str]:
        self.info(msg='loading resource from: "%s"' % src)
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
        else:
            self.error(msg='failed to load resource: "%s" % src')


def _get_live_url(item: Any) -> str:
    if isinstance(item, Dict):
        item = item.get('url')
    if isinstance(item, str):
        return item
    else:
        return ''


def _join_path(base: str, file: str) -> str:
    assert base is not None and len(base) > 0, 'base path empty, file: %s' % file
    assert file is not None and len(file) > 0, 'file name empty, path: %s' % base
    # standard base path
    if base.endswith(r'/'):
        base = base.rstrip(r'/')
    else:
        base = Path.dir(path=base)
    # standard file name
    if file.startswith(r'./'):
        file = file[2:]
    return '%s/%s' % (base, file)


async def _save_index(lives: List[Dict], path: str) -> bool:
    Log.info(msg='saving index file: %d live urls -> %s' % (len(lives), path))
    return await JSONFile(path=path).write({
        'lives': lives,
    })


async def _save_channels(genres: List[LiveGenre], path: str) -> bool:
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
                Log.warning(msg='empty channel: "%s" -> %s' % (item.name, streams))
                continue
            line = '#'.join(sources)
            line = '%s,%s' % (item.name, line)
            array.append(line)
            count += 1
        if len(array) == 0:
            Log.warning(msg='empty genre: "%s" -> %s' % (group.title, channels))
            continue
        text += '\n%s,#genre#\n' % group.title
        text += '\n%s\n' % '\n'.join(array)
    # OK
    Log.info(msg='saving lives file: %d genres, %d channels -> %s' % (len(genres), count, path))
    if len(text) > 0:
        return await TextFile(path=path).write(text=text)


async def _save_source(text: str, path: str) -> bool:
    Log.info(msg='saving source file: %d lines -> %s' % (len(text.splitlines()), path))
    if len(text) > 0:
        return await TextFile(path=path).write(text=text)


def _count_streams(genres: List[LiveGenre]) -> int:
    count = 0
    for group in genres:
        channels = group.channels
        for item in channels:
            count += len(item.streams)
    return count


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
