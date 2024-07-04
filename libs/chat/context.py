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
from typing import Optional, Any, Dict

from dimples import Dictionary
from dimples import ID
from dimples import Content, TextContent

from .base import Request


class ChatContext(Dictionary, ABC):

    def __init__(self, identifier: ID):
        super().__init__()
        self.__identifier = identifier

    @property
    def identifier(self) -> ID:
        """ Conversation ID """
        return self.__identifier

    # Override
    def __hash__(self) -> int:
        """ Return hash(self). """
        return self.__identifier.__hash__()

    # Override
    def __eq__(self, x: str) -> bool:
        """ Return self==value. """
        if isinstance(x, ChatContext):
            if self is x:
                # same object
                return True
            x = x.identifier
        # check inner string
        return self.__identifier.__eq__(x)

    # Override
    def __ne__(self, x: str) -> bool:
        """ Return self!=value. """
        if isinstance(x, ChatContext):
            if self is x:
                # same object
                return False
            x = x.identifier
        # check inner string
        return self.__identifier.__ne__(x)

    #
    #   Variables
    #

    # Override
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        return super().get(key=key, default=default)

    def set(self, key: str, value: Optional[Any]):
        if value is None:
            self.pop(key=key, default=None)
        else:
            self[key] = value

    #
    #   Monitor
    #

    def report_success(self, service: str, agent: str):
        pass

    def report_failure(self, service: str, agent: str):
        pass

    def report_crash(self, service: str):
        pass

    #
    #   Responses
    #

    async def respond_markdown(self, text: str, request: Request, extra: Dict = None,
                               sn: int = 0, muted: str = None) -> TextContent:
        if extra is None:
            extra = {}
        else:
            extra = extra.copy()
        # extra info
        extra['format'] = 'markdown'
        if sn > 0:
            extra['sn'] = sn
        if muted is not None:
            extra['muted'] = muted
        return await self.respond_text(text=text, request=request, extra=extra)

    async def respond_text(self, text: str, request: Request, extra: Dict = None) -> TextContent:
        content = TextContent.create(text=text)
        if extra is not None:
            for key in extra:
                content[key] = extra[key]
        calibrate_time(content=content, request=request)
        await self._send_content(content=content, receiver=self.identifier)
        return content

    @abstractmethod
    async def _send_content(self, content: Content, receiver: ID) -> bool:
        """ Send message to DIM station """
        raise NotImplemented

    @abstractmethod
    async def save_response(self, text: str, prompt: str, request: Request) -> bool:
        """ Save response text with prompt """
        raise NotImplemented


def calibrate_time(content: Content, request: Request, period: float = 1.0):
    res_time = content.time
    req_time = request.time
    if req_time is None:
        assert False, 'request error: %s' % req_time
    elif res_time is None or res_time <= req_time:
        content['time'] = req_time + period
