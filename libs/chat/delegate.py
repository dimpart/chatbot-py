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
from typing import Optional, List, Dict

from dimples import TextContent

from ..utils import Log, Logging
from ..utils import json_decode

from .base import Request, Greeting, ChatRequest, TranslateRequest
from .context import ChatContext
from .translation import TranslateResult, TranslateContent, Translator


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
        if isinstance(request, TranslateRequest):
            # translate
            prompt = request.text
            prompt = prompt.strip()
            if prompt is None or len(prompt) == 0:
                self.error(msg='translate content error: %s, envelope: %s' % (request.content, request.envelope))
                return False
            return await self._handle_translate(prompt=prompt, request=request, context=context)
        elif isinstance(request, Greeting):
            # say hello
            prompt = request.text
            prompt = prompt.strip()
            if prompt is None or len(prompt) == 0:
                self.error(msg='greeting content error: %s, envelope: %s' % (request.content, request.envelope))
                return False
            return await self._handle_text(prompt=prompt, request=request, context=context)
        elif isinstance(request, ChatRequest):
            content = request.content
            if isinstance(content, TextContent):
                # text conversation
                prompt = request.text
                if prompt is None or len(prompt) == 0:
                    prompt = content.text
                prompt = prompt.strip()
                if prompt is None or len(prompt) == 0:
                    self.error(msg='text content error: %s, envelope: %s' % (content, request.envelope))
                    return False
                return await self._handle_text(prompt=prompt, request=request, context=context)
        # error
        self.error(msg='unsupported request: %s' % request)

    async def _handle_translate(self, prompt: str, request: TranslateRequest, context: ChatContext) -> bool:
        content = request.content
        #
        #  1. query
        #
        translator = Translator()
        text = content.get('text')
        answer = translator.fetch(text=text, code=request.code)
        if answer is not None:
            # response from cache
            record = '[%s] cached: %s' % (self.agent, answer)
            await context.save_response(text=record, prompt=prompt, request=request)
            info = _fetch_json_result(text=answer)
            # assert isinstance(info, Dict), 'response error: %s' % answer
            result = TranslateResult(dictionary=info)
        else:
            # query AI server
            answer = await self._query(prompt=prompt, request=request, context=context)
            record = '[%s] %s' % (self.agent, answer)
            await context.save_response(text=record, prompt=prompt, request=request)
            if answer is None:
                self.error(msg='response error: "%s" => "%s"' % (prompt, record))
                return False
            else:
                answer = answer.strip()
                if len(answer) == 0:
                    self.warning(msg='respond nothing: "%s" => "%s"' % (prompt, record))
                    return False
            info = _fetch_json_result(text=answer)
            if info is None:
                info = {}
            # else:
            #     assert isinstance(info, Dict), 'response error: %s' % answer
            result = TranslateResult(dictionary=info)
            if result.valid:
                translator.cache(text=text, code=request.code, response=answer)
        #
        #  2. respond
        #
        res = TranslateContent.respond(result=result, query=request.content)
        if 'text' not in res:
            res['text'] = answer
        await context.respond_content(content=res, request=request)
        return True

    async def _handle_text(self, prompt: str, request: Request, context: ChatContext) -> bool:
        # query AI server
        answer = await self._query(prompt=prompt, request=request, context=context)
        record = '[%s] %s' % (self.agent, answer)
        await context.save_response(text=record, prompt=prompt, request=request)
        if answer is None:
            self.error(msg='response error: "%s" => "%s"' % (prompt, record))
            return False
        else:
            answer = answer.strip()
            if len(answer) == 0:
                self.info(msg='respond nothing: "%s" => "%s"' % (prompt, record))
                return False
        # OK
        await context.respond_markdown(text=answer, request=request)
        return True

    @abstractmethod
    async def _query(self, prompt: str, request: Request, context: ChatContext) -> Optional[str]:
        """ Build message(s) & query the server """
        raise NotImplemented


def _fetch_json_result(text: str) -> Optional[Dict]:
    # fetch code block
    start = text.find('```')
    if start < 0:
        return None
    end = text.rfind('```')
    if end <= start:
        return None
    else:
        block = text[start:end+3]
    # fetch json code
    start = block.find('{')
    if start < 0:
        return None
    end = block.rfind('}')
    if end <= start:
        return None
    else:
        code = block[start:end+1]
    # decode result
    try:
        return json_decode(string=code)
    except Exception as error:
        Log.error(msg='translate result error: %s, %s' % (error, text))


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
