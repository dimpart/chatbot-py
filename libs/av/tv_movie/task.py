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

from typing import Optional

from dimples import URI

from ...chat import ChatRequest

from .video import VideoBox


class Task:
    """ Search Task """

    CANCEL_PROMPT = '_If this task takes too long, you can input the commands below to stop it:_\n' \
                    '- **cancel**\n' \
                    '- **stop**\n' \
                    '\n' \
                    '### NOTICE:\n' \
                    '_Another new task will interrupt the previous task too._'

    def __init__(self, keywords: str, request: Optional[ChatRequest], box: VideoBox):
        super().__init__()
        self.__keywords = keywords
        self.__request = request
        self.__box = box
        self.__cancelled = False

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s id="%s" keywords="%s" />' % (cname, self.box.identifier, self.keywords)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s id="%s" keywords="%s" />' % (cname, self.box.identifier, self.keywords)

    @property
    def keywords(self) -> str:
        return self.__keywords

    @property
    def request(self) -> Optional[ChatRequest]:
        return self.__request

    @property
    def box(self) -> VideoBox:
        return self.__box

    @property
    def cancelled(self) -> bool:
        return self.__cancelled

    def cancel(self):
        """ stop the task """
        self.__cancelled = True

    def copy(self):
        return Task(keywords=self.keywords, request=self.request, box=self.box)


#
#   Update
#


class UpdateTask:

    def __init__(self, task: Task):
        super().__init__()
        self.__task = Task(keywords=task.keywords, request=None, box=task.box)

    @property
    def task(self) -> Task:
        return self.__task


class UpdateSeasonTask(UpdateTask):

    def __init__(self, url: URI, name: Optional[str], cover: Optional[URI], task: Task):
        super().__init__(task=task)
        self.__url = url
        self.__name = name
        self.__cover = cover

    @property
    def url(self) -> URI:
        return self.__url

    @property
    def name(self) -> str:
        return self.__name

    @property
    def cover(self) -> Optional[URI]:
        return self.__cover
