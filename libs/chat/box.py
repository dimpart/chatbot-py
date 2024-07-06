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

from abc import ABC
from typing import Optional

from dimples import DateTime
from dimples import ID
from dimples import CommonFacebook

from ..utils import Logging

from .base import get_nickname
from .base import Request
from .base import Greeting, ChatRequest
from .context import ChatContext
from .delegate import ChatProxy, ChatProcessor
from .storage import ChatStorage


# noinspection PyAbstractClass
class ChatBox(ChatContext, Logging, ABC):

    EXPIRES = 3600 * 36  # seconds

    def __init__(self, identifier: ID, facebook: CommonFacebook, proxy: ChatProxy):
        super().__init__(identifier=identifier)
        self.__facebook = facebook
        self.__proxy = proxy
        self.__greeted = False
        self.__last_time = DateTime.now()

    @property  # protected
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property  # protected
    def proxy(self) -> ChatProxy:
        return self.__proxy

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" time="%s" />' % (cname, self.identifier, self.__last_time)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" time="%s" />' % (cname, self.identifier, self.__last_time)

    async def get_name(self, identifier: ID) -> str:
        # return self.facebook.get_name(identifier=identifier)
        name = await get_nickname(identifier=identifier, facebook=self.facebook)
        if name is None or len(name) == 0:
            name = identifier.name
            if name is None or len(name) == 0:
                name = str(identifier.address)
        return name

    def is_expired(self, now: DateTime) -> bool:
        expired = self.__last_time + self.EXPIRES
        return now > expired

    def _refresh_time(self, when: DateTime):
        if when is None:
            # error
            return
        else:
            # calibrate time
            current = DateTime.now()
            if when > current:
                when = current
        if when > self.__last_time:
            self.__last_time = when

    #
    #   Request
    #

    async def process_request(self, request: Request) -> Optional[ChatProcessor]:
        # refresh last active time
        self._refresh_time(when=request.time)
        # chatting
        if isinstance(request, ChatRequest):
            # question from user
            self.__greeted = True
        elif self.__greeted:
            assert isinstance(request, Greeting), 'request error: %s' % request
            # no need to greet again
            return None
        else:
            assert isinstance(request, Greeting), 'request error: %s' % request
            self.__greeted = True
        # process request content
        return await self.proxy.process_request(request=request, context=self)

    # Override
    async def save_response(self, text: str, prompt: str, request: Request) -> bool:
        """ Save response text with prompt """
        # check request type
        if isinstance(request, ChatRequest):
            # sender
            sender = request.envelope.sender
            sender_name = await self.get_name(identifier=sender)
            # check group
            group = request.content.group
            if group is not None:
                # group message: "sender_name (group_name)"
                identifier = group
                group_name = await self.get_name(identifier=group)
                name = '%s (%s)' % (sender_name, group_name)
            else:
                # personal message: "sender_name"
                identifier = sender
                name = sender_name
        else:
            # greeting: "sender_name"
            identifier = request.identifier
            name = await self.get_name(identifier=identifier)
        # OK
        storage = ChatStorage()
        return await storage.save_response(question=prompt, answer=text, identifier=identifier, name=name)
