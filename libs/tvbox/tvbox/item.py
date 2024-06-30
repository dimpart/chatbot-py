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
from .utils import Log
from .utils import base64_decode
from .utils import json_decode
from .utils import path_parent
from .utils import path_join

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

    #
    #   Factory
    #

    @classmethod
    async def load(cls, config: LiveConfig, loader: SourceLoader):
        return await _get_live_set(config=config, loader=loader)


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
    # check channels
    for item in channels:
        if not isinstance(item, Dict):
            Log.warning(msg='cannot decode url from channel: %s' % item)
            continue
        urls = item.get('urls')
        if not isinstance(urls, List):
            Log.warning(msg='cannot decode url from channel: %s' % item)
            continue
        # check urls
        for proxy in urls:
            if not isinstance(proxy, str):
                Log.warning(msg='cannot decode url: %s, %s' % (proxy, item))
                continue
            if not proxy.startswith(r'proxy://'):
                Log.warning(msg='cannot decode url: %s, %s' % (proxy, item))
                continue
            # try to decode url from ext
            ext = _get_query_value(url=proxy, key='ext')
            try:
                return base64_decode(string=ext)
            except Exception as error:
                Log.error(msg='failed to decode url: %s, %s, %s' % (proxy, item, error))


def _get_query_value(url: URI, key: str) -> Optional[str]:
    array = url.split(r'&')
    for item in array:
        pos = item.find(r'=')
        if pos > 0 and item[:pos] == key:
            pos += 1
            return item[pos:]


#
#   Load live set
#

async def _get_live_set(config: LiveConfig, loader: SourceLoader) -> LiveSet:
    live_set = LiveSet()
    # 1. get from "sources"
    sources = config.sources
    Log.info(msg='getting live urls from: %s' % sources)
    for idx in sources:
        src = LiveSet.get_source_url(item=idx)
        if src is None or len(src) == 0:
            Log.error(msg='source error: %s' % idx)
            continue
        # elif src.find(r'://') < 0:
        #     self.error(msg='source error: %s -> %s' % (idx, src))
        #     continue
        # 1.1. load
        text = await _load_resource(src=src, loader=loader)
        if text is None:
            Log.error(msg='ignore index: %s' % src)
            continue
        # 1.2. parse
        info = json_decode(string=text)
        if not isinstance(info, Dict):
            Log.error(msg='json error: %s -> %s' % (src, text))
            continue
        # 1.3. get 'lives' from this source
        lives = info.get('lives')
        if not isinstance(lives, List):
            Log.error(msg='json error: %s -> %s' % (src, text))
            continue
        # 1.4. add lives url
        base = path_parent(src)
        for item in lives:
            # check url
            url = LiveSet.get_live_url(item=item, base=base)
            if url is None or len(url) == 0:
                Log.error(msg='lives item error: %s' % item)
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
    lives = config.lives
    Log.info(msg='got live urls from config: %s' % lives)
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
            Log.error(msg='lives item error: %s' % item)
        else:
            live_set.add_item(item=item)
    # OK
    return live_set


async def _load_resource(src: Union[str, URI], loader: SourceLoader) -> Optional[str]:
    Log.info(msg='loading resource from: "%s"' % src)
    res = await loader.load_text(src=src)
    if res is None:
        Log.error(msg='failed to load resource: "%s"' % src)
    return res
