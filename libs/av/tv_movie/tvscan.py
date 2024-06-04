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

import threading
from typing import Optional, Set

import requests

from dimples import URI, DateTime

from ...utils import Log, Logging
from ...utils import TextFile
from ...utils import md_esc
from ...utils import get_filename, get_extension

from ..tvbox import LiveSource, LiveChannel
from ..tvbox import LiveParser, LockedParser

from .engine import Task


class LiveScanner(Logging):

    def __init__(self, parser: LiveParser = None):
        super().__init__()
        self.__parser = LockedParser() if parser is None else parser
        self.__lock = threading.Lock()

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
            text = await TextFile(path=live_path).read()
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
        next_time = 0
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
                now = DateTime.current_timestamp()
                if request is not None and box is not None and now > next_time:
                    next_time = now + 2  # next respond time (at lease 2 seconds later)
                    self.info(msg='respond scanning channel "%s" (%d/%d) to %s'
                                  % (name, source_index, source_count, request.envelope.sender))
                    title = '**"%s"**' % name
                    if source_count > 1:
                        title += ' - Line %d' % source_index
                    partial = 'Scanning %s (%d/%d)...' % (title, channel_index, channel_count)
                    partial += '\n\n----\n'
                    partial += Task.CANCEL_PROMPT
                    if len(available_channels) > 0:
                        text = _build_channel_response(channels=available_channels)
                        partial = '%s\n\n%s' % (text, partial)
                    res = await box.respond_markdown(text=partial, request=request, sn=sn, muted='true')
                    sn = res['sn']
                #
                #  Check sources
                #
                self.info(msg='checking channel source: (%d/%d) "%s" => %s' % (channel_index, channel_count, name, src))
                await self._check_m3u8(source=src, timeout=timeout)
            #
            #  2. add channel if sources available
            #
            if channel.available:
                available_channels.add(channel)
        #
        #  respond results
        #
        if request is not None and box is not None:
            self.info(msg='respond %d channels to %s' % (len(available_channels), request.envelope.sender))
            text = _build_channel_response(channels=available_channels)
            if task.cancelled:
                text += '\n----\n'
                text += 'Scanning task is cancelled.'
            await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
        return available_channels

    async def _check_m3u8(self, source: LiveSource, timeout: float = None):
        # 1. check update time before lock
        if not (source.available is None or source.is_expired()):
            # last result not expired yet,
            # no need to check again now
            return source.available
        with self.__lock:
            # 2. check update time after lock
            if source.available is None or source.is_expired():
                # 3. check remote URL
                valid = await _http_check(url=source.url, timeout=timeout)
                source.set_available(valid)
        # return source valid
        return source.available


def _build_channel_response(channels: Set[LiveChannel]) -> str:
    if len(channels) == 0:
        return 'Channels not found.'
    else:
        channels = list(channels)
        channels.sort(key=lambda c: c.name)
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
            url = _md_live_link(name=name, url=line.url)
            text += '- %s\n' % url
            continue
        text += '- **%s**' % name
        for index in range(count):
            line = valid_sources[index]
            url = _md_live_link(name=name, url=line.url)
            text += ' > %d. %s' % (index + 1, url)
        text += '\n'
    return text


def _md_live_link(name: str, url: URI) -> str:
    if url is None or url.find('://') < 0:
        Log.error(msg='live url error: "%s" -> %s' % (name, url))
        return '_%s_' % name
    # check file extension
    ext = get_extension(filename=get_filename(path=url))
    if ext is None or len(ext) == 0:
        url += '#live/stream.m3u8'
    else:
        url += '#live'
    # check for title
    if url.lower().find('.m3u8') < 0:
        title = name
    else:
        title = '%s - LIVE' % name
    # build the link
    return '[%s](%s "%s")' % (name, url, title)


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
