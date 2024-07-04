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

from abc import ABC, abstractmethod
from typing import Optional, List

from dimples import Content, TextContent, FileContent

from ..utils import Logging

from .base import Request, Greeting, ChatRequest
from .context import ChatContext


class ChatProcessor(Logging, ABC):
    """ Chat Processing Unit """

    def __init__(self, agent: str):
        super().__init__()
        self.__agent = agent

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s agent="%s" />' % (cname, self.agent)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s agent="%s" />' % (cname, self.agent)

    @property
    def agent(self) -> str:
        return self.__agent  # 'OpenAI'

    async def process_request(self, request: Request, context: ChatContext) -> bool:
        if isinstance(request, ChatRequest):
            content = request.content
            return await self._process_content(content=content, request=request, context=context)
        elif isinstance(request, Greeting):
            text = request.text
            if text is not None and len(text) > 0:
                return await self._say_hi(prompt=text, request=request, context=context)

    async def _process_content(self, content: Content, request: ChatRequest, context: ChatContext) -> bool:
        if isinstance(content, TextContent):
            return await self._process_text_content(content=content, request=request, context=context)
        elif isinstance(content, FileContent):
            return await self._process_file_content(content=content, request=request, context=context)
        else:
            self.error(msg='unsupported content: %s, envelope: %s' % (content, request.envelope))

    async def _process_text_content(self, content: TextContent, request: ChatRequest, context: ChatContext) -> bool:
        text = request.text
        if text is not None and len(text) > 0:
            return await self._query(prompt=text, content=content, request=request, context=context)

    async def _process_file_content(self, content: FileContent, request: ChatRequest, context: ChatContext) -> bool:
        pass

    async def _say_hi(self, prompt: str, request: Greeting, context: ChatContext) -> bool:
        """ Build greeting message & query the server """
        pass

    @abstractmethod
    async def _query(self, prompt: str, content: TextContent, request: ChatRequest, context: ChatContext) -> bool:
        """ Build message(s) & query the server """
        raise NotImplemented


class ChatProxy(Logging):
    """ Chat Processors Manager """

    def __init__(self, service: str, processors: List[ChatProcessor]):
        super().__init__()
        self.__service = service
        self.__processors = processors

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        count = len(self.__processors)
        return '<%s service="%s" count=%d />' % (cname, self.service, count)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        count = len(self.__processors)
        return '<%s service="%s" count=%d />' % (cname, self.service, count)

    @property
    def service(self) -> str:
        return self.__service  # 'ChatGPT'

    @property  # protected
    def processors(self) -> List[ChatProcessor]:
        return self.__processors

    # protected
    def _move_processor(self, index: int, processor: ChatProcessor):
        if index > 0:
            self.warning(msg='move processor position: %d, %s' % (index, processor))
            self.__processors.pop(index)
            self.__processors.insert(0, processor)

    async def process_request(self, request: Request, context: ChatContext) -> Optional[ChatProcessor]:
        all_handlers = self.processors
        if len(all_handlers) == 0:
            self.error(msg='gpt handlers not set')
            return None
        index = -1
        for handler in all_handlers:
            index += 1
            # try to query by each handler
            try:
                ok = await handler.process_request(request=request, context=context)
            except Exception as error:
                self.error(msg='handler error: %s, %s' % (error, handler))
                ok = False
            if ok:
                # move this handler to the front
                self._move_processor(index=index, processor=handler)
                context.report_success(service=self.service, agent=handler.agent)
                return handler
            else:
                context.report_failure(service=self.service, agent=handler.agent)
                self.warning(msg='failed to query handler: %s' % handler)
        # failed to get answer
        context.report_crash(service=self.service)
