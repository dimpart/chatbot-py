# -*- coding: utf-8 -*-
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

from typing import Optional, Iterable, List, Dict

from dimples import URI, DateTime

from tvbox import LiveGenre

from ...utils import Runner
from ...utils import Singleton, Logging
from ...utils import Path, TextFile, JSONFile

from .tvscan import LiveScanner
from .engine import Task


@Singleton
class LiveLoader(Runner, Logging):

    SCAN_INTERVAL = 3600 * 2

    def __init__(self):
        super().__init__(interval=60)
        self.__scanner = LiveScanner()
        self.__entrance = None    # 'tvbox.json'
        self.__local_path = None  # 'lives.txt'
        self.__next_time = 0      # next scan time
        Runner.thread_run(runner=self)

    @property  # protected
    def scanner(self) -> LiveScanner:
        return self.__scanner

    @property
    def entrance(self) -> Optional[str]:
        return self.__entrance

    @entrance.setter
    def entrance(self, path: str):
        self.__entrance = path

    @property
    def local_path(self) -> str:
        return self.__local_path

    @local_path.setter
    def local_path(self, path: str):
        self.__local_path = path

    # Override
    async def process(self) -> bool:
        if DateTime.now() < self.__next_time:
            return False
        else:
            self.info(msg='start scanning ...')
        try:
            # get live urls from "tvbox.json"
            lives_urls = await self._get_live_urls()
            if lives_urls is None or len(lives_urls) == 0:
                self.warning(msg='lives url not found')
                return False
            # scan live urls
            await self._scan_live_urls(live_urls=lives_urls)
            self.__next_time = DateTime.now() + self.SCAN_INTERVAL
        except Exception as error:
            self.error(msg='lives loader error: %s' % error)

    async def _get_live_urls(self) -> Optional[List[URI]]:
        entrance = self.entrance
        if entrance is None:
            self.warning(msg='path for "tvbox.json" not found')
            return None
        # load 'tvbox.json'
        container = await JSONFile(path=entrance).read()
        if isinstance(container, Dict):
            container = container.get('lives')
        if not isinstance(container, List):
            self.error(msg='lives error: %s' % entrance)
            return None
        live_urls = []
        for item in container:
            if isinstance(item, Dict):
                url = item.get('url')
                assert isinstance(url, str), 'lives item error: %s' % item
            elif isinstance(item, str):
                url = item
            else:
                self.error(msg='lives url error: %s' % item)
                continue
            live_urls.append(url)
        return live_urls

    async def _scan_live_urls(self, live_urls: Iterable[URI]):
        # 1. check local path for "lives.txt"
        local_path = self.local_path
        if local_path is None:
            self.warning(msg='path for "lives.txt" not found')
            return False
        else:
            self.info(msg='scanning live channels: %s -> %s' % (live_urls, local_path))
            is_first = not await Path.exists(path=local_path)
        # 2. scan each url
        all_groups: List[LiveGenre] = []
        channel_count = 0
        for url in live_urls:
            genres = await self.scanner.scan(live_url=url, timeout=64)
            for group in genres:
                count = len(group.channels)
                if count > 0:
                    channel_count += count
                    all_groups.append(group)
                else:
                    self.warning(msg='no available channel found: %s' % url)
            # 3. save available channels
            if is_first:
                self.info(msg='saving channels: %d -> %s' % (channel_count, local_path))
                await _save_channels(genres=all_groups, path=local_path)
        if not is_first:
            self.info(msg='saving all channels: %d -> %s' % (channel_count, local_path))
            await _save_channels(genres=all_groups, path=local_path)

    async def search(self, task: Task):
        request = task.request
        box = task.box
        # check task
        if request is None or box is None:
            self.error(msg='task error')
            return False
        # check path for "lives.txt"
        local_path = self.local_path
        if local_path is None:
            text = 'Lives not found'
            await box.respond_text(text=text, request=request)
            return False
        # scan live channels from local path
        await self.scanner.scan(live_path=local_path, timeout=32, task=task)


async def _save_channels(genres: Iterable[LiveGenre], path: str):
    text = ''
    for group in genres:
        text += '%s,#genre#\n'
        channels = group.channels
        for item in channels:
            urls = ''
            sources = item.streams
            for src in sources:
                if src.available:
                    urls += '#%s' % src.url
            if len(urls) > 0:
                urls = urls[1:]  # skip first '#'
                text += '%s,%s\n' % (item.name, urls)
    if len(text) == 0:
        return False
    return await TextFile(path=path).write(text=text)
