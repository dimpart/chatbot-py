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

from .types import URI
from .utils import Logging
from .utils import json_decode
from .utils import path_parent, path_join

from .config import LiveConfig
from .scanner import LiveScanner, ScanContext
from .source import SourceLoader, LiveHandler


class LiveLoader(Logging):

    def __init__(self, config: LiveConfig):
        super().__init__()
        self.__config = config
        self.__scanner = self._create_live_scanner()
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
    def _create_live_scanner(self) -> LiveScanner:
        # TODO: override for customized scanner
        return LiveScanner()

    # noinspection PyMethodMayBeStatic
    def _create_source_loader(self) -> SourceLoader:
        # TODO: override for customized loader
        return SourceLoader()

    def clear_caches(self):
        self.loader.clear_caches()

    #
    #   Load
    #

    async def _get_live_urls(self) -> Set[URI]:
        live_urls = set()
        # 1. get from "sources"
        sources = self.config.sources
        for src in sources:
            # 1.1. load
            text = await self._load_resource(src=src)
            if text is None:
                self.error(msg='ignore index: %s' % src)
                continue
            # 1.2. parse
            info = json_decode(text=text)
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
                    base = path_parent(src)
                    url = path_join(base, url)
                live_urls.add(url)
        # 2. get from "lives"
        lives = self.config.lives
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
        live_urls = await self._get_live_urls()
        self.info(msg='got live urls: %d, %s' % (len(live_urls), live_urls))
        for url in live_urls:
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
            available_lives.append({
                'url': self.config.get_output_lives_url(url=url),
                'path': self.config.get_output_lives_path(url=url),
                'src': url,
            })
        # mission accomplished
        return await handler.update_index(lives=available_lives)


def _get_live_url(item: Any) -> str:
    if isinstance(item, Dict):
        item = item.get('url')
    if isinstance(item, str):
        return item
    else:
        return ''
