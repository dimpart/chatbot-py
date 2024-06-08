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

from typing import Optional, List, Dict

from dimples import URI, DateTime

from tvbox import LiveStream, LiveChannel, LiveGenre
from tvbox import LiveLoader, LiveHandler
from tvbox import LiveConfig
from tvbox import ScanContext

from ...utils import Log
from ...utils import md_esc
from ...utils import get_filename, get_extension

from ...chat import ChatRequest
from ...chat import VideoBox

from .engine import Task


class SearchContext(ScanContext):

    def __init__(self, timeout: Optional[float], task: Optional[Task]):
        super().__init__(params={'timeout': timeout})
        self.__task = task

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


class TVScan(LiveHandler):

    INDEX_URI = 'http://tfs.dim.chat/tvbox/index.json'

    def __init__(self, config: LiveConfig):
        super().__init__(config=config)
        self.__loader = LiveLoader(config=config)
        self.__respond_time = 0

    @property
    def loader(self) -> LiveLoader:
        return self.__loader

    async def search(self, task: Task):
        request = task.request
        box = task.box
        # check task
        if request is None or box is None:
            self.error(msg='task error')
            return False
        else:
            context = SearchContext(timeout=32, task=task)
        # load 'lives'
        await self.loader.load(handler=self, context=context)

    # Override
    async def update_index(self, lives: List[Dict]) -> bool:
        self.info(msg='scanned from %d lives: %s' % (len(lives), lives))
        return True

    # Override
    async def update_lives(self, genres: List[LiveGenre], url: URI) -> bool:
        return True

    # Override
    async def update_source(self, text: str, url: URI) -> bool:
        lines = 0 if text is None else len(text.splitlines())
        self.info(msg='scanning %d lines in lives: %s' % (lines, url))
        return True

    #
    #   ScanEventHandler
    #

    # Override
    async def on_scan_start(self, context: ScanContext):
        context.set_value(key='sn', value=0)
        context.set_value(key='available_channel_count', value=0)

    # Override
    async def on_scan_finished(self, context: SearchContext):
        # respond full results
        await _respond_genres(context=context)

    # Override
    async def on_scan_stream_start(self, context: SearchContext, channel: LiveChannel, stream: LiveStream):
        # respond partially
        expired = self.__respond_time + 2
        now = DateTime.now()
        if now > expired:
            self.__respond_time = now
            await _respond_partial(context=context)


async def _respond_partial(context: SearchContext):
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    now = DateTime.current_timestamp()
    next_time = context.get_value(key='next_time', default=0)
    if now < next_time:
        return False
    count = context.get_value(key='available_channel_count', default=0)
    offset = context.get_value(key='channel_offset', default=0)
    total = context.get_value(key='total_channels', default=0)
    Log.info(msg='scanning %d/%d channels...' % (offset + 1, total))
    if count == 0:
        text = ''
    else:
        text = _build_live_channels(context=context)
        text += '\n----\n'
    text += 'Scanning **%d/%d** channels ...\n' % (offset + 1, total)
    text += '\n%s' % Task.CANCEL_PROMPT
    # respond with sn
    sn = context.get_value(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set_value(key='sn', value=sn)


async def _respond_genres(context: SearchContext):
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    count = context.get_value(key='available_channel_count', default=0)
    text = _build_live_channels(context=context)
    text += '\n----\n'
    if context.task_cancelled:
        text += 'Scanning task is cancelled.'
    else:
        text += '**%d** channels available.' % count
    # respond with sn
    sn = context.get_value(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set_value(key='sn', value=sn)


def _build_live_channels(context: SearchContext) -> Optional[str]:
    genres_index = context.get_value(key='genre_index', default=0)
    channel_index = context.get_value(key='channel_index', default=0)
    stream_index = context.get_value(key='stream_index', default=0)
    genres: List[LiveGenre] = context.get_value(key='all_genres', default=[])
    text = ''
    #
    #  1. scan genres
    #
    i = -1
    for group in genres:
        channels = group.channels
        i += 1
        if i > genres_index:
            break
        elif len(channels) == 0:
            continue
        else:
            array: List[str] = []
        #
        #  2. scan channels
        #
        j = -1
        for item in channels:
            streams = item.streams
            j += 1
            if j > channel_index and i == genres_index:
                break
            elif not item.available:
                continue
            else:
                name = md_esc(text=item.name)
                src_idx = 0
                line = ''
            #
            #  3. scan streams
            #
            k = -1
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
                    line += '- %s' % link
                else:
                    line += ' > %d. %s' % (src_idx, link)
            array.append(line)
        # build group
        text += '\n### %s\n' % group.title
        text += '\n%s\n' % '\n'.join(array)
    # done
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
