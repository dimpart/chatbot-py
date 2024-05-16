# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from abc import abstractmethod
from typing import List

from dimples import EntityType, ID
from dimples import ReliableMessage
from dimples import Envelope
from dimples import Content, TextContent, FileContent, CustomizedContent
from dimples import CommonFacebook, CommonMessenger

from dimples.client import ClientMessageProcessor

from ..chat import Greeting, ChatRequest, ChatClient


class ClientProcessor(ClientMessageProcessor):

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__chat_client = self._create_chat_client()

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @abstractmethod
    def _create_chat_client(self) -> ChatClient:
        """ Create Chat Client """
        raise NotImplemented

    def _process_text_content(self, content: TextContent, envelope: Envelope):
        request = ChatRequest(content=content, envelope=envelope, facebook=self.facebook)
        self.__chat_client.append(request=request)

    def _process_file_content(self, content: FileContent, envelope: Envelope):
        request = ChatRequest(content=content, envelope=envelope, facebook=self.facebook)
        self.__chat_client.append(request=request)

    def _process_users_content(self, content: CustomizedContent, envelope: Envelope):
        users = content.get('users')
        if isinstance(users, List):
            self.info(msg='received users: %s' % users)
        else:
            self.error(msg='users content error: %s, %s' % (content, envelope))
            return
        for item in users:
            identifier = ID.parse(identifier=item.get('U'))
            if identifier is None or identifier.type != EntityType.USER:
                self.warning(msg='ignore user: %s' % item)
                continue
            self.info(msg='say hi for %s' % identifier)
            greeting = Greeting(identifier=identifier, content=content, envelope=envelope, facebook=self.facebook)
            self.__chat_client.append(request=greeting)

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        if isinstance(content, TextContent):
            self._process_text_content(content=content, envelope=r_msg.envelope)
            return []
        elif isinstance(content, FileContent):
            self._process_file_content(content=content, envelope=r_msg.envelope)
            return []
        elif isinstance(content, CustomizedContent):
            mod = content.module
            if mod == 'users':
                self._process_users_content(content=content, envelope=r_msg.envelope)
            return []
        # system contents
        return await super().process_content(content=content, r_msg=r_msg)
