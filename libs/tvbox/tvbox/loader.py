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
from .utils import Log, Logging, DateTime
from .utils import json_decode, base64_decode
from .utils import path_parent, path_join

from .config import LiveConfig
from .scanner import LiveScanner, ScanContext
from .source import SourceLoader, LiveHandler


class LiveSet:

    def __init__(self):
        super().__init__()
        self.__lives: List[Dict] = []

    # Override
    def __len__(self) -> int:
        """ Return len(self). """
        return self.__lives.__len__()

    @property
    def lives(self) -> List[Dict]:
        return self.__lives

    def add_item(self, item: Dict):
        url = item.get('url')
        assert url is not None, 'lives item error: %s' % item
        for live in self.__lives:
            old = live.get('url')
            if old == url:
                # duplicated
                return False
        self.__lives.append(item)

    @classmethod
    def get_live_url(cls, item: Union[URI, Dict], base: URI = None) -> Optional[URI]:
        if isinstance(item, Dict):
            if 'url' in item:
                item = item.get('url')
            else:
                item = _decode_proxy_url(item=item)
        if not isinstance(item, str):
            return None
        elif len(item) == 0:
            return None
        elif item.find(r'://') > 0:
            return item
        elif base is not None:
            return path_join(base, item)

    @classmethod
    def get_source_url(cls, item: Union[str, Dict]) -> Optional[URI]:
        if isinstance(item, Dict):
            item = item.get('url')
        if isinstance(item, str):
            return item


def _decode_proxy_url(item: Dict) -> Optional[URI]:
    """ {
            "group": "redirect",
            "channels": [{
                "name": "live",
                "urls": [
                    "proxy://do=live&type=txt&ext={BASE64_ENCODED_URL}"
                ]
            }]
        }
    """
    channels = item.get('channels')
    if not isinstance(channels, List):
        return None
    for item in channels:
        try:
            urls = item.get('urls')
            for proxy in urls:
                ext = _get_query_value(url=proxy, key='ext')
                return base64_decode(string=ext)
        except Exception as error:
            Log.error(msg='failed to decode channel: %s, %s' % (item, error))


def _get_query_value(url: URI, key: str) -> Optional[str]:
    array = url.split(r'&')
    for item in array:
        pos = item.find(r'=')
        if pos > 0 and item[:pos] == key:
            pos += 1
            return item[pos:]


class LiveLoader(Logging):

    def __init__(self, config: LiveConfig, scanner: LiveScanner):
        super().__init__()
        self.__config = config
        self.__scanner = scanner
        self.__loader = self._create_source_loader()

    @property
    def config(self) -> LiveConfig:
        return self.__config

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
        live_set = LiveSet()
        # 1. get from "sources"
        sources = self.config.sources
        self.info(msg='getting live urls from: %s' % sources)
        for idx in sources:
            src = LiveSet.get_source_url(item=idx)
            if src is None or len(src) == 0:
                self.error(msg='source error: %s' % idx)
                continue
            # elif src.find(r'://') < 0:
            #     self.error(msg='source error: %s -> %s' % (idx, src))
            #     continue
            # 1.1. load
            text = await self._load_resource(src=src)
            if text is None:
                self.error(msg='ignore index: %s' % src)
                continue
            # 1.2. parse
            info = json_decode(string=text)
            if not isinstance(info, Dict):
                self.error(msg='json error: %s -> %s' % (src, text))
                continue
            # 1.3. get 'lives' from this source
            lives = info.get('lives')
            if not isinstance(lives, List):
                self.error(msg='json error: %s -> %s' % (src, text))
                continue
            # 1.4. add lives url
            base = path_parent(src)
            for item in lives:
                # check url
                url = LiveSet.get_live_url(item=item, base=base)
                if url is None or len(url) == 0:
                    self.error(msg='lives item error: %s' % item)
                    continue
                # check for origin info
                if isinstance(item, str):
                    item = {
                        'url': url,
                        'origin': {
                            'url': url,
                            'source': src,
                        },
                    }
                elif 'origin' not in item:
                    item['origin'] = {
                        'url': url,
                        'source': src,
                    }
                # OK
                live_set.add_item(item=item)
        # 2. get from "lives"
        lives = self.config.lives
        self.info(msg='got live urls from config: %s' % lives)
        for item in lives:
            if isinstance(item, str):
                url = item
                item = {
                    'url': url,
                    'origin': {
                        'url': url,
                    },
                }
            else:
                url = item.get('url')
                if 'origin' not in item:
                    item['origin'] = {
                        'url': url,
                    }
            if url is None or url.find(r'://') < 0:
                self.error(msg='lives item error: %s' % item)
            else:
                live_set.add_item(item=item)
        # OK
        return live_set

    async def _load_resource(self, src: Union[str, URI]) -> Optional[str]:
        self.info(msg='loading resource from: "%s"' % src)
        res = await self.loader.load_text(src=src)
        if res is None:
            self.error(msg='failed to load resource: "%s"' % src)
        return res

    #
    #   Running
    #

    async def load(self, handler: LiveHandler, context: ScanContext):
        scanner = self.scanner
        available_lives: List[Dict] = []
        # scan lives
        start_time = DateTime.current_timestamp()
        live_set = await self.get_live_set()
        lives = live_set.lives
        self.info(msg='got live set: %d, %s' % (len(lives), lives))
        for item in lives:
            url = item.get('url')
            text = await self._load_resource(src=url)
            if text is None:
                self.error(msg='ignore lives: %s' % url)
                continue
            else:
                await handler.update_source(text=text, url=url)
            count = len(text.splitlines())
            self.info(msg='scanning lives: %s => %d lines' % (url, count))
            genres = await scanner.scan(text=text, context=context, handler=handler)
            if len(genres) == 0:
                self.warning(msg='ignore empty lives: %s => %d lines' % (url, count))
                continue
            else:
                # update 'lives.txt'
                await handler.update_lives(genres=genres, url=url)
            # append to 'lives'
            info = item.copy()
            if 'origin' not in item:
                info['origin'] = {
                    'url': url,
                }
            info['origin']['channel_total_count'] = context.get(key='channel_total_count')
            info['origin']['stream_total_count'] = context.get(key='stream_total_count')
            info['available_channel_count'] = context.get(key='available_channel_count')
            info['available_stream_count'] = context.get(key='available_stream_count')
            info['url'] = self.config.get_output_lives_url(url=url)
            info['path'] = self.config.get_output_lives_path(url=url)
            info['src'] = url
            available_lives.append(info)
        # mission accomplished
        end_time = DateTime.current_timestamp()
        return await handler.update_index(container={
            'lives': available_lives,
            'scan_time': DateTime.full_string(timestamp=start_time),
            'update_time': DateTime.full_string(timestamp=end_time),
        })
