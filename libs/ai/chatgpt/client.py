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

import random
from typing import Optional, List

from dimples import ID
from dimples import Content
from dimples import CommonFacebook

from ...chat import Request, Setting, ChatRequest
from ...chat import ChatBox, ChatClient
from ...chat import ChatProcessor, ChatProxy
from ...client import Emitter
from ...client import Monitor

from .queue import MessageQueue


class GPTChatBox(ChatBox):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook, proxy: ChatProxy, setting: Setting):
        super().__init__(identifier=identifier, facebook=facebook, proxy=proxy)
        self.__message_queue = MessageQueue.create(setting=setting)

    @property
    def message_queue(self) -> MessageQueue:
        return self.__message_queue

    # Override
    def report_success(self, service: str, agent: str):
        monitor = Monitor()
        monitor.report_success(service=service, agent=agent)

    # Override
    def report_failure(self, service: str, agent: str):
        monitor = Monitor()
        monitor.report_failure(service=service, agent=agent)

    # Override
    def report_crash(self, service: str):
        monitor = Monitor()
        monitor.report_crash(service=service)

    # Override
    async def process_request(self, request: Request) -> Optional[ChatProcessor]:
        cpu = await super().process_request(request=request)
        if cpu is None and isinstance(request, ChatRequest):
            await self.respond_text(text=self.NOT_FOUND, request=request)
        return cpu

    # Override
    async def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        return await emitter.send_content(content=content, receiver=receiver)


class GPTChatClient(ChatClient):

    SYSTEM_SETTING = 'Your name is "Gigi", a smart and beautiful girl.' \
                     ' You are set as a little assistant who is good at listening' \
                     ' and willing to answer any questions.'

    def __init__(self, facebook: CommonFacebook):
        super().__init__(facebook=facebook)
        self.__processors: List[ChatProcessor] = []
        self.__system_setting = Setting(definition=self.SYSTEM_SETTING)

    def add_processor(self, processor: ChatProcessor):
        self.__processors.append(processor)

    def _chat_processors(self) -> List[ChatProcessor]:
        return self.__processors.copy()

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.facebook
        setting = self.__system_setting
        # copy handlers in random order
        processors = self._chat_processors()
        count = len(processors)
        if count > 1:
            processors = random.sample(processors, count)
        proxy = ChatProxy(service='ChatGPT', processors=processors)
        return GPTChatBox(identifier=identifier, facebook=facebook, proxy=proxy, setting=setting)
