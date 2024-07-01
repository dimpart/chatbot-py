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
from .utils import Logging
from .utils import base64_decode, utf8_decode, json_decode
from .utils import path_parent, path_join

from .config import LiveConfig
from .source import SourceLoader


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

    #
    #   Factory
    #

    @classmethod
    async def load(cls, config: LiveConfig, loader: SourceLoader):
        return await _live_set_helper.get_live_set(config=config, loader=loader)


#
#   Load live set
#


class _LiveSetHelper(Logging):

    async def get_live_set(self, config: LiveConfig, loader: SourceLoader) -> LiveSet:
        live_set = LiveSet()
        #
        #  1. get 'sources'
        #
        sources = self._get_source_urls(config=config)
        for src in sources:
            #
            #  2. get 'lives' from source
            #
            lives = await self._load_lives(src=src, loader=loader)
            if not isinstance(lives, List):
                self.error(msg='lives error: %s -> %s' % (src, lives))
                continue
            else:
                base = path_parent(src)
            #
            #  3. get live items
            #
            for info in lives:
                live_items = self._get_live_items(info=info, base=base)
                for item in live_items:
                    if 'origin' not in item:
                        item['origin'] = {
                            'url': item.get('url'),
                            'source': src,
                        }
                    # OK
                    live_set.add_item(item=item)
        #
        #  4. get from 'lives'
        #
        lives = config.lives
        for info in lives:
            url = None
            item = None
            if isinstance(info, str):
                url = info
                item = {
                    'url': url,
                    'origin': {
                        'url': url,
                    },
                }
            elif isinstance(info, Dict):
                url = info.get('url')
                item = info.copy()
                if 'origin' not in item:
                    item['origin'] = {
                        'url': url,
                    }
            if url is None or url.find(r'://') < 0:
                self.error(msg='lives item error: %s' % info)
            else:
                live_set.add_item(item=item)
        return live_set

    def _get_source_urls(self, config: LiveConfig) -> List[URI]:
        sources = []
        array = config.sources
        for item in array:
            url = item.get('url') if isinstance(item, Dict) else item
            if isinstance(url, str):
                sources.append(url)
            else:
                self.error(msg='source error: %s' % item)
        self.info(msg='got live urls: %s -> %s' % (array, sources))
        return sources

    async def _load_lives(self, src: str, loader: SourceLoader) -> Optional[List]:
        try:
            text = await self._load_resource(src=src, loader=loader)
            if text is not None:
                info = json_decode(string=text)
                if isinstance(info, Dict):
                    return info.get('lives')
        except Exception as error:
            self.error(msg='failed to load resource: "%s", %s' % (src, error))

    async def _load_resource(self, src: Union[str, URI], loader: SourceLoader) -> Optional[str]:
        self.info(msg='loading resource from: "%s"' % src)
        res = await loader.load_text(src=src)
        if res is None:
            self.error(msg='failed to load resource: "%s"' % src)
        return res

    def _get_live_items(self, info: Union[URI, Dict], base: URI) -> List[Dict]:
        if isinstance(info, str):
            url = _full_url(url=info, base=base)
            return [{
                'url': url,
            }]
        elif not isinstance(info, Dict):
            self.error(msg='live info error: %s' % info)
            return []
        # check url
        url = info.get('url')
        if isinstance(url, str):
            info['url'] = _full_url(url=url, base=base)
            return [info]
        # check channels
        channels = info.get('channels')
        if not isinstance(channels, List):
            self.error(msg='live info error: %s' % info)
            return []
        array = []
        for item in channels:
            if not isinstance(item, Dict):
                self.warning(msg='cannot decode url from channel: %s' % item)
                continue
            proxies = self._decode_channel_proxies(item=item, base=base)
            for proxy in proxies:
                array.append(proxy)
        if len(array) == 0:
            self.warning(msg='channels empty: %s' % channels)
        return array

    def _decode_channel_proxies(self, item: Dict, base: URI) -> List[Dict]:
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
        proxy_urls = item.get('urls')
        if not isinstance(proxy_urls, List):
            self.warning(msg='cannot decode url from channel: %s' % item)
            return []
        array = []
        for proxy in proxy_urls:
            if not isinstance(proxy, str):
                self.warning(msg='cannot decode url: %s, %s' % (proxy, item))
                continue
            if not proxy.startswith(r'proxy://'):
                self.warning(msg='cannot decode url: %s, %s' % (proxy, item))
                continue
            # try to decode url from ext
            ext = _get_query_value(url=proxy, key='ext')
            if ext is None:
                self.warning(msg='proxy url error: %s, %s' % (proxy, item))
                continue
            try:
                data = base64_decode(string=ext)
                assert data is not None, 'failed to decode proxy url: %s' % ext
                url = utf8_decode(data=data)
                assert url is not None, 'failed to decode proxy url: %s' % ext
                # clone and replace with url
                info = item.copy()
                info.pop('urls', None)
                info['url'] = _full_url(url=url, base=base)
                array.append(info)
            except Exception as error:
                self.error(msg='failed to decode url: %s, %s, %s' % (proxy, item, error))
        if len(array) == 0:
            self.warning(msg='channel empty: %s' % item)
        return array


# shared helper
_live_set_helper = _LiveSetHelper()


#
#   URL Utils
#

def _get_query_value(url: URI, key: str) -> Optional[str]:
    array = url.split(r'&')
    for item in array:
        pos = item.find(r'=')
        if pos > 0 and item[:pos] == key:
            pos += 1
            return item[pos:]


def _full_url(url: str, base: URI) -> URI:
    if url.find(r'://') > 0:
        return url
    elif url.startswith(r'/'):
        return url
    else:
        return path_join(base, url)
