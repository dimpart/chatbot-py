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

from tvbox.lives import LiveStream, LiveChannel, LiveGenre
from tvbox.lives import LiveParser
from tvbox import LiveConfig
from tvbox import LiveLoader, LiveScanHandler
from tvbox import LiveScanner, ScanContext

from ...utils import Log
from ...utils import md_esc
from ...utils import get_filename, get_extension

from ...chat import ChatRequest
from ...chat import VideoBox

from .engine import Task


class SearchContext(ScanContext):

    def __init__(self, timeout: Optional[float], task: Optional[Task]):
        super().__init__(timeout=timeout)
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

    @property  # Override
    def cancelled(self) -> bool:
        task = self.task
        stopped = False if task is None else task.cancelled
        return stopped or super().cancelled

    @cancelled.setter  # Override
    def cancelled(self, flag: bool):
        self.set(key='cancelled', value=flag)


class TVScan(LiveScanHandler):

    INDEX_URI = 'http://tfs.dim.chat/tvbox/index.json'
    # list foot
    LIST_DESC = '* Here are the live stream sources collected from the internet;\n' \
                '* All live stream sources are contributed by the netizens with a spirit of sharing;\n' \
                '* Before presenting them to you, the service bot scans all sources to verify their availability.'

    def __init__(self, config: LiveConfig):
        super().__init__(config=config)
        self.__loader = LiveLoader(config=config,
                                   parser=LiveParser(),
                                   scanner=LiveScanner())
        self.__respond_time = 0

    @property
    def loader(self) -> LiveLoader:
        return self.__loader

    def clear_caches(self):
        self.loader.clear_caches()

    async def get_lives(self) -> List[Dict]:
        live_set = await self.loader.get_live_set()
        return live_set.lives

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
    async def update_index(self, container: Dict) -> bool:
        lives = container.get('lives', [])
        count = len(lives)
        self.info(msg='finished scanning %d lives: %s' % (count, lives))
        return True

    # Override
    async def update_lives(self, genres: List[LiveGenre], url: URI) -> bool:
        count = len(genres)
        self.info(msg='got lives in %d genres from %s' % (count, url))
        return True

    # Override
    async def update_source(self, text: str, url: URI) -> bool:
        count = 0 if text is None else len(text.splitlines())
        self.info(msg='got source file (%d lines) from %s' % (count, url))
        return True

    #
    #   ScanEventHandler
    #

    # Override
    async def on_scan_start(self, context: ScanContext, genres: List[LiveGenre]):
        # await super().on_scan_start(context=context, genres=genres)
        total_channels = 0
        total_streams = 0
        for group in genres:
            channels = group.channels
            for item in channels:
                total_channels += 1
                total_streams += len(item.streams)
        context.set(key='channel_total_count', value=total_channels)
        context.set(key='stream_total_count', value=total_streams)
        context.set(key='available_channel_count', value=0)
        context.set(key='available_stream_count', value=0)
        # store other params
        context.set(key='sn', value=0)
        context.set(key='all_genres', value=genres)  # genres list

    # Override
    async def on_scan_finished(self, context: SearchContext, genres: List[LiveGenre]):
        # respond full results
        await _respond_genres(context=context)
        await super().on_scan_finished(context=context, genres=genres)

    # Override
    async def on_scan_stream_start(self, context: SearchContext, channel: LiveChannel, stream: LiveStream):
        await super().on_scan_stream_start(context=context, channel=channel, stream=stream)
        # respond partially
        expired = self.__respond_time + 2
        now = DateTime.now()
        if now > expired:
            self.__respond_time = now
            await _respond_partial(context=context)


async def _respond_partial(context: SearchContext):
    count = context.get(key='available_channel_count', default=0)
    offset = context.get(key='channel_offset', default=0)
    total = context.get(key='channel_total_count', default=0)
    Log.info(msg='scanning %d/%d channels...' % (offset + 1, total))
    # check for respond
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    now = DateTime.current_timestamp()
    next_time = context.get(key='next_time', default=0)
    if now < next_time:
        return False
    elif count == 0:
        text = ''
    else:
        text = _build_live_channels(context=context)
        text += '\n----\n'
    text += 'Scanning **%d/%d** channels ...\n' % (offset + 1, total)
    text += '\n%s' % Task.CANCEL_PROMPT
    # respond with sn
    sn = context.get(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set(key='sn', value=sn)


async def _respond_genres(context: SearchContext):
    request = context.request
    box = context.box
    if request is None or box is None:
        return False
    count = context.get(key='available_channel_count', default=0)
    total = context.get(key='channel_total_count', default=0)
    text = _build_live_channels(context=context)
    text += '\n----\n'
    if context.task_cancelled:
        text += 'Scanning task is cancelled, above shows **%d/%d** only.' % (count, total)
    else:
        text += '**%d/%d** channels available.' % (count, total)
    # respond with sn
    sn = context.get(key='sn', default=0)
    res = await box.respond_markdown(text=text, request=request, sn=sn, muted='true')
    sn = res['sn']
    context.set(key='sn', value=sn)


def _build_live_channels(context: SearchContext) -> Optional[str]:
    genres_index = context.get(key='genre_index', default=0)
    channel_index = context.get(key='channel_index', default=0)
    stream_index = context.get(key='stream_index', default=0)
    genres: List[LiveGenre] = context.get(key='all_genres', default=[])
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
