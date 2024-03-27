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

from typing import Optional, Union
from urllib.error import URLError

from dimples import ID
from dimples import Content
from dimples import TextContent
from dimples import CommonFacebook

from ...utils import Logging
from ...database import ChatStorage

from ...client import Emitter

from ...chat import Request
from ...chat import ChatBox, ChatClient
from ...chat.base import get_nickname

from .chatbot import ChatBot, Dialog


#
#   Chat Box
#


class NLPChatBox(ChatBox, Logging):

    def __init__(self, identifier: ID, facebook: CommonFacebook, bots: Union[list, ChatBot]):
        super().__init__(identifier=identifier)
        self.__facebook = facebook
        self.__bots = bots
        self.__dialog: Optional[Dialog] = None

    @property
    def dialog(self) -> Dialog:
        if self.__dialog is None and len(self.__bots) > 0:
            d = Dialog()
            d.bots = self.__bots
            self.__dialog = d
        return self.__dialog

    # Override
    def _say_hi(self, prompt: str, request: Request):
        pass

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request):
        if self.__bots is None:
            self.error('chat bots not set')
            return None
        dialog = self.dialog
        if dialog is None:
            # chat bots empty
            return None
        try:
            res = dialog.query(content=content, sender=request.identifier)
        except URLError as error:
            self.error('%s' % error)
            return None
        self.respond(responses=[res], request=request)
        answer = res.get_str(key='text', default='')
        self._save_response(question=prompt, answer=answer, identifier=request.identifier)

    # Override
    def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)

    def _save_response(self, question: str, answer: str, identifier: ID) -> bool:
        name = get_nickname(identifier=identifier, facebook=self.__facebook)
        storage = ChatStorage()
        return storage.save_response(question=question, answer=answer, identifier=identifier, name=name)


class NLPChatClient(ChatClient):

    def __init__(self, facebook: CommonFacebook, bots: Union[list, ChatBot]):
        super().__init__()
        self.__facebook = facebook
        self.__bots = bots

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        bots = self.__bots
        return NLPChatBox(identifier=identifier, facebook=facebook, bots=bots)
