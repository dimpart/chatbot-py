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
from typing import List

from dimples import DateTime
from dimples import ID
from dimples import Content, TextContent
from dimples import FileContent, ImageContent, AudioContent, VideoContent
from dimples import CommonFacebook

from ..utils import Logging

from .base import get_nickname
from .base import Request
from .base import Greeting, ChatRequest
from .storage import ChatStorage


class ChatBox(Logging, ABC):

    EXPIRES = 3600 * 36  # seconds

    def __init__(self, identifier: ID, facebook: CommonFacebook):
        super().__init__()
        self.__identifier = identifier
        self.__facebook = facebook
        self.__greeted = False
        self.__last_time = DateTime.now()

    @property
    def identifier(self) -> ID:
        """ Conversation ID """
        return self.__identifier

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    async def get_name(self, identifier: ID) -> str:
        # return self.__facebook.get_name(identifier=identifier)
        name = await get_nickname(identifier=identifier, facebook=self.__facebook)
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

    # Override
    def __hash__(self) -> int:
        """ Return hash(self). """
        return self.__identifier.__hash__()

    # Override
    def __eq__(self, x: str) -> bool:
        """ Return self==value. """
        if isinstance(x, ChatBox):
            if self is x:
                # same object
                return True
            x = x.identifier
        # check inner string
        return self.__identifier.__eq__(x)

    # Override
    def __ne__(self, x: str) -> bool:
        """ Return self!=value. """
        if isinstance(x, ChatBox):
            if self is x:
                # same object
                return False
            x = x.identifier
        # check inner string
        return self.__identifier.__ne__(x)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" time="%s" />' % (cname, self.__identifier, self.__last_time)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" time="%s" />' % (cname, self.__identifier, self.__last_time)

    #
    #   Request
    #

    async def process_request(self, request: Request) -> bool:
        # refresh last active time
        self._refresh_time(when=request.time)
        # chatting
        if isinstance(request, ChatRequest):
            # question from user
            await request.build()
            self.__greeted = True
        elif self.__greeted:
            assert isinstance(request, Greeting), 'request error: %s' % request
            # no need to greet again
            return True
        else:
            assert isinstance(request, Greeting), 'request error: %s' % request
            await request.build()
            # say hi
            text = request.text
            if text is not None and len(text) > 0:
                self.__greeted = await self._say_hi(prompt=text, request=request)
            return self.__greeted
        # process request content
        content = request.content
        if isinstance(content, TextContent):
            return await self._process_text_content(content=content, request=request)
        elif isinstance(content, FileContent):
            return await self._process_file_content(content=content, request=request)
        else:
            self.error(msg='unsupported content: %s, envelope: %s' % (content, request.envelope))

    async def _process_text_content(self, content: TextContent, request: ChatRequest) -> bool:
        # text message
        text = request.text
        if text is None:
            self.error(msg='text content error: %s from %s' % (content, request.identifier))
            return False
        text = text.strip()
        if len(text) == 0:
            self.warning(msg='ignore empty text content: %s from %s' % (content, request.identifier))
            return False
        return await self._ask_question(prompt=text, content=content, request=request)

    async def _process_file_content(self, content: FileContent, request: ChatRequest) -> bool:
        # file message
        if isinstance(content, ImageContent):
            # image message
            return await self._process_image_content(content=content, request=request)
        elif isinstance(content, AudioContent):
            # audio message
            return await self._process_audio_content(content=content, request=request)
        elif isinstance(content, VideoContent):
            # video message
            return await self._process_video_content(content=content, request=request)
        else:
            self.error(msg='unsupported file content: %s, envelope: %s' % (content, request.envelope))

    async def _process_image_content(self, content: ImageContent, request: ChatRequest) -> bool:
        """ Process image message """
        pass

    async def _process_audio_content(self, content: AudioContent, request: ChatRequest) -> bool:
        """ Process audio message """
        pass

    async def _process_video_content(self, content: VideoContent, request: ChatRequest) -> bool:
        """ Process video message """
        pass

    async def _say_hi(self, prompt: str, request: Greeting) -> bool:
        """ Build greeting message & query the server """
        pass

    @abstractmethod
    async def _ask_question(self, prompt: str, content: TextContent, request: ChatRequest) -> bool:
        """ Build message(s) & query the server """
        raise NotImplemented

    async def _save_response(self, text: str, prompt: str, request: Request) -> bool:
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

    #
    #   Respond
    #

    async def respond_text(self, text: str, request: Request) -> int:
        content = TextContent.create(text=text)
        calibrate_time(content=content, request=request)
        return await self.respond(responses=[content], request=request)

    async def respond_markdown(self, text: str, request: Request) -> int:
        content = TextContent.create(text=text)
        content['format'] = 'markdown'
        calibrate_time(content=content, request=request)
        return await self.respond(responses=[content], request=request)

    async def respond(self, responses: List[Content], request: Request) -> int:
        # all content time in responses must be calibrated with the request time
        receiver = request.identifier
        for res in responses:
            await self._send_content(content=res, receiver=receiver)
        return len(responses)

    @abstractmethod
    async def _send_content(self, content: Content, receiver: ID) -> bool:
        """ Send message to DIM station """
        raise NotImplemented


def calibrate_time(content: Content, request: Request, period: float = 1.0):
    res_time = content.time
    req_time = request.time
    if req_time is None:
        assert False, 'request error: %s' % req_time
    elif res_time is None or res_time <= req_time:
        content['time'] = req_time + period
