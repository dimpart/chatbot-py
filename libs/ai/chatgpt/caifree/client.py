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

from typing import Optional

from dimples import ID
from dimples import Content
from dimples import TextContent
from dimples import CommonFacebook

from ....utils import HttpClient
from ....database import ChatStorage

from ....client import Emitter

from ....chat import Request, Setting
from ....chat import ChatBox, ChatClient
from ....chat.base import get_nickname

from .gpt import GPTHandler


#
#   Chat Box
#


class GPTChatBox(ChatBox):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, setting: Setting, facebook: CommonFacebook,
                 referer: str, auth_token: str, http_client: HttpClient):
        super().__init__(identifier=identifier, setting=setting)
        self.__facebook = facebook
        gpt = GPTHandler(referer=referer, auth_token=auth_token, http_client=http_client)
        gpt.presume(system_content=setting.text)
        self.__gpt = gpt
        self.__talks_count = 0

    # Override
    def _say_hi(self, prompt: str, request: Request):
        if self.__talks_count > 0:
            return
        answer = self.__gpt.ask(question=prompt)
        if answer is not None and len(answer) > 0:
            self.respond_text(text=answer, request=request)
        self._save_response(question=prompt, answer=answer, identifier=request.sender)
        self.__talks_count += 1

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request):
        answer = self.__gpt.ask(question=prompt)
        if answer is None:
            answer = self.NOT_FOUND
        elif len(answer) == 0:
            answer = self.NO_CONTENT
        self.respond_text(text=answer, request=request)
        self._save_response(question=prompt, answer=answer, identifier=request.sender)
        self.__talks_count += 1

    # Override
    def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)

    def _save_response(self, question: str, answer: str, identifier: ID) -> bool:
        name = get_nickname(identifier=identifier, facebook=self.__facebook)
        storage = ChatStorage()
        return storage.save_response(question=question, answer=answer, identifier=identifier, name=name)


class GPTChatClient(ChatClient):

    BASE_URL = 'https://chat.caifree.com'
    REFERER_URL = 'https://chat.caifree.com/'

    SYSTEM_SETTING = 'Your name is "Gigi", a smart and beautiful girl.' \
                     ' You are set as a little assistant who is good at listening' \
                     ' and willing to answer any questions.'

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook
        self.__http_client = HttpClient(long_connection=True, base_url=self.BASE_URL)
        self.__system_setting = Setting(definition=self.SYSTEM_SETTING)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        setting = self.__system_setting
        facebook = self.__facebook
        referer = self.REFERER_URL
        auth_token = 'Bearer pk-this-is-a-real-free-pool-token-for-everyone'
        http_client = self.__http_client
        return GPTChatBox(identifier=identifier, setting=setting, facebook=facebook,
                          referer=referer, auth_token=auth_token, http_client=http_client)
