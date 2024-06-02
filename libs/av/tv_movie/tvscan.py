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

from typing import Optional, Set

import requests

from dimples import URI

from ...utils import Log, Logging
from ...utils import TextFile
from ...utils import md_esc

from ..tvbox import LiveChannel
from ..tvbox import LiveParser, LockedParser

from .engine import Task


class LiveScanner(Logging):

    def __init__(self, parser: LiveParser = None):
        super().__init__()
        self.__parser = LockedParser() if parser is None else parser

    @property  # protected
    def parser(self) -> LiveParser:
        return self.__parser

    async def scan_channels(self, live_url: URI = None, live_path: str = None,
                            timeout: float = None, task: Task = None) -> Set[LiveChannel]:
        """ Get valid channels from live URL/local file """
        if live_url is not None:
            self.info(msg='loading channels from "%s"...' % live_url)
            text = await _http_get(url=live_url)
        elif live_path is not None:
            self.info(msg='loading channels from "%s"...' % live_path)
            text = TextFile(path=live_path).read()
        else:
            assert False, 'live url/path empty'
        if text is None:
            self.warning(msg='failed to load channels: %s, %s' % (live_url, live_path))
            text = ''
        return await self.parse_channels(text=text, timeout=timeout, task=task)

    async def parse_channels(self, text: str, timeout: float = None, task: Task = None) -> Set[LiveChannel]:
        if task is None:
            request = None
            box = None
        else:
            request = task.request
            box = task.box
        available_channels = set()
        all_channels = self.parser.parse_channels(text=text)
        channel_count = len(all_channels)
        channel_index = 0
        sn = 0
        for channel in all_channels:
            channel_index += 1
            if task is not None and task.cancelled:
                break
            name = channel.name
            sources = channel.sources
            assert name is not None and len(sources) > 0, 'channel error: %s' % str(sources)
            #
            #  1. check channel sources
            #
            source_count = len(sources)
            source_index = 0
            for src in sources:
                source_index += 1
                if task is not None and task.cancelled:
                    break
                #
                #  respond results partially
                #
                if request is not None and box is not None:
                    title = '**"%s"**' % name
                    if source_count > 1:
                        title += ' - Line %d' % source_index
                    partial = 'Scanning %s (%d/%d)...' % (title, channel_index, channel_count)
                    if len(available_channels) > 0:
                        text = _build_channel_response(channels=available_channels)
                        partial = '%s\n\n----\n%s' % (text, partial)
                    res = await box.respond_markdown(text=partial, request=request, sn=sn, muted='true')
                    sn = res['sn']
                #
                #  Check sources
                #
                self.info(msg='checking channel source: (%d/%d) "%s" => %s' % (channel_index, channel_count, name, src))
                if src.available is None or src.is_expired():
                    src.set_available(await _http_check(url=src.url, timeout=timeout))
            #
            #  2. add channel if sources available
            #
            if channel.available:
                available_channels.add(channel)
        #
        #  respond results
        #
        if request is not None and box is not None:
            text = _build_channel_response(channels=available_channels)
            if task.cancelled:
                text += '\n----\n'
                text += 'Scanning task is cancelled.'
            await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
        return available_channels


def _build_channel_response(channels: Set[LiveChannel]) -> str:
    if len(channels) == 0:
        return 'Channels not found'
    text = 'Channels:\n'
    text += '\n----\n'
    for item in channels:
        name = md_esc(text=item.name)
        all_sources = item.sources
        # get valid sources
        valid_sources = []
        for src in all_sources:
            if src.available:
                valid_sources.append(src)
        count = len(valid_sources)
        if count == 0:
            continue
        elif count == 1:
            line = valid_sources[0]
            text += '- [%s](%s "%s - Live")\n' % (name, line.url, name)
            continue
        text += '- **%s**' % name
        for index in range(count):
            line = valid_sources[index]
            text += ' > %d. [%s](%s "%s - Live")' % (index + 1, name, line.url, name)
        text += '\n'
    return text


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


async def _http_check(url: URI, timeout: float = None, is_m3u8: bool = None) -> bool:
    if is_m3u8 is None and url.lower().find('m3u8') > 0:
        is_m3u8 = True
    try:
        response = requests.head(url, timeout=timeout)
        status_code = response.status_code
        Log.info(msg='http status: %d, %s' % (status_code, url))
        if status_code == 302:
            redirected_url = response.headers.get('Location')
            return await _http_check(url=redirected_url, is_m3u8=is_m3u8, timeout=timeout)
        elif status_code != 200:
            # HTTP error
            return False
        elif is_m3u8:
            return True
        # check content type
        content_type = response.headers.get('Content-Type')
        content_type = '' if content_type is None else str(content_type).lower()
        if content_type.find('application/vnd.apple.mpegurl') >= 0:
            return True
        elif content_type.find('application/x-mpegurl') >= 0:
            return True
        else:
            Log.warning(msg='Content-Type not matched: %s -> "%s"' % (url, content_type))
    except Exception as error:
        Log.error(msg='failed to query URL: %s, error: %s' % (url, error))
    return False
