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

from typing import Optional, Any, List
from typing import Iterable

import requests

from dimples import URI, DateTime

from tvbox import LiveStream, LiveChannel, LiveGenre
from tvbox import LiveParser, LockedParser
from tvbox import LiveStreamScanner

from ...utils import Log, Logging
from ...utils import TextFile
from ...utils import md_esc
from ...utils import get_filename, get_extension
from ...chat import ChatRequest
from ...chat import VideoBox

from .engine import Task


class ScanContext:

    def __init__(self, genres: List[LiveGenre], timeout: Optional[float], task: Optional[Task]):
        super().__init__()
        self.__genres = genres
        self.__timeout = timeout
        self.__task = task
        self.__vars = {}

    @property
    def genres(self) -> List[LiveGenre]:
        return self.__genres

    @property
    def timeout(self) -> Optional[float]:
        return self.__timeout

    @property
    def task(self) -> Optional[Task]:
        return self.__task

    @property
    def request(self) -> Optional[ChatRequest]:
        task = self.task
        if task is not None:
            return task.request

    @property
    def box(self) -> Optional[VideoBox]:
        task = self.task
        if task is not None:
            return task.box

    @property
    def task_cancelled(self) -> box:
        task = self.task
        if task is not None:
            return task.cancelled

    def get_value(self, key: str, default: Any = None):
        return self.__vars.get(key, default)

    def set_value(self, key: str, value: Optional[Any]):
        if value is None:
            self.__vars.pop(key, None)
        else:
            self.__vars[key] = value


class LiveScanner(Logging):

    def __init__(self):
        super().__init__()
        self.__parser = LockedParser()
        self.__scanner = LiveStreamScanner()

    @property  # protected
    def live_parser(self) -> LiveParser:
        return self.__parser

    @property  # protected
    def stream_scanner(self) -> LiveStreamScanner:
        return self.__scanner

    async def scan(self, live_url: URI = None, live_path: str = None,
                   timeout: float = None, task: Task = None) -> List[LiveGenre]:
        """ Scan live stream channels from URL or local file """
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
            return []
        genres = self.live_parser.parse(text=text)
        context = ScanContext(genres=genres, timeout=timeout, task=task)
        count = _count_channels(genres=genres)
        context.set_value(key='channel_total_count', value=count)
        groups = await self._scan_genres(genres=genres, context=context)
        # respond full results
        await _respond_genres(context=context)
        return groups

    async def _scan_genres(self, genres: Iterable[LiveGenre], context: ScanContext) -> List[LiveGenre]:
        """ Get non-empty channel groups """
        groups: List[LiveGenre] = []
        group_index = 0
        for item in genres:
            if context.task_cancelled:
                break
            else:
                group_index += 1
                context.set_value(key='genres_index', value=group_index)
            # scan for valid channels
            channels = await self._scan_channels(channels=item.channels, context=context)
            if len(channels) > 0:
                item.channels = channels
                groups.append(item)
        return groups

    async def _scan_channels(self, channels: Iterable[LiveChannel], context: ScanContext) -> List[LiveChannel]:
        """ Get valid channels """
        available_channels: List[LiveChannel] = []
        channel_index = 0
        for item in channels:
            if context.task_cancelled:
                break
            else:
                channel_index += 1
                context.set_value(key='channel_index', value=channel_index)
            # increase offset
            channel_offset = context.get_value(key='channel_offset', default=0)
            channel_offset += 1
            context.set_value(key='channel_offset', value=channel_offset)
            # scan for valid streams
            streams = await self._scan_streams(streams=item.streams, context=context)
            if len(streams) > 0:
                item.streams = streams
                available_channels.append(item)
                # increase valid count
                count = context.get_value(key='channel_valid_count', default=0)
                count += 1
                context.set_value(key='channel_valid_count', value=count)
        return available_channels

    async def _scan_streams(self, streams: Iterable[LiveStream], context: ScanContext) -> List[LiveStream]:
        """ Get valid streams """
        scanner = self.stream_scanner
        available_streams: List[LiveStream] = []
        stream_index = 0
        for item in streams:
            if context.task_cancelled:
                break
            else:
                stream_index += 1
                context.set_value(key='stream_index', value=stream_index)
            # respond partially
            await _respond_partial(context=context)
            # scan for valid stream
            src = await scanner.scan_stream(stream=item)
            if src is not None:
                available_streams.append(src)
        return available_streams


def _count_channels(genres: List[LiveGenre]) -> int:
    count = 0
    for group in genres:
        count += len(group.channels)
    return count


async def _respond_partial(context: ScanContext):
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    now = DateTime.current_timestamp()
    next_time = context.get_value(key='next_time', default=0)
    if now < next_time:
        return False
    count = context.get_value(key='channel_valid_count', default=0)
    offset = context.get_value(key='channel_offset', default=0)
    total = context.get_value(key='channel_total_count', default=0)
    Log.info(msg='scanning %d/%d channels...' % (offset, total))
    if count == 0:
        text = ''
    else:
        text = '**%d** channels available:\n' % count
        text += '\n----\n'
        text += '%s\n' % _build_live_channels(context=context)
        text += '\n----\n'
    text += 'Scanning **%d/%d** channels ...\n' % (offset, total)
    text += '\n%s' % Task.CANCEL_PROMPT
    # respond with sn
    sn = context.get_value(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set_value(key='sn', value=sn)


async def _respond_genres(context: ScanContext):
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    count = context.get_value(key='channel_valid_count', default=0)
    text = '**%d** channels available:\n' % count
    text += '\n----\n'
    text += '%s\n' % _build_live_channels(context=context)
    if context.task_cancelled:
        text += '\n----\n'
        text += 'Scanning task is cancelled.'
    # respond with sn
    sn = context.get_value(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set_value(key='sn', value=sn)


def _build_live_channels(context: ScanContext) -> Optional[str]:
    genres_index = context.get_value(key='genres_index', default=0)
    channel_index = context.get_value(key='channel_index', default=0)
    stream_index = context.get_value(key='stream_index', default=0)
    if genres_index == 0 or channel_index == 0 or stream_index == 0:
        Log.error(msg='indexes error: %s, %s, %s' % (genres_index, channel_index, stream_index))
        return None
    genres = context.genres
    text = ''
    #
    #  1. scan genres
    #
    i = 0
    for group in genres:
        channels = group.channels
        i += 1
        if i > genres_index:
            break
        elif len(channels) == 0:
            continue
        else:
            title = group.title
            if title is None or len(title) == 0:
                text += '\n'
            else:
                text += '[**%s**]\n' % title
        #
        #  2. scan channels
        #
        j = 0
        for line in channels:
            streams = line.streams
            j += 1
            if j > channel_index and i == genres_index:
                break
            elif not line.available:
                continue
            else:
                name = md_esc(text=line.name)
                src_idx = 0
            #
            #  3. scan streams
            #
            k = 0
            for src in streams:
                k += 1
                if k > stream_index and j == channel_index and i == genres_index:
                    break
                elif not src.available:
                    continue
                else:
                    link = _build_live_link(name=name, url=src.url)
                    src_idx += 1
                if src_idx <= 1:
                    text += '- %s' % link
                else:
                    text += ' > %d. %s' % (src_idx, link)
            text += '\n'
    # OK
    return text.rstrip()


def _build_channel_md(channel: LiveChannel) -> Optional[str]:
    name = md_esc(text=channel.name)
    streams = channel.streams
    streams = [src for src in streams if src.available]
    count = len(streams)
    if count == 0:
        return None
    elif count == 1:
        src = streams[0]
        return _build_live_link(name=name, url=src.url)
    text = '**%s**' % name
    for index in range(count):
        src = streams[index]
        link = _build_live_link(name=name, url=src.url)
        text += ' > %d. %s' % (index + 1, link)
    return text


def _build_live_link(name: str, url: URI) -> str:
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
