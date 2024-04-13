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
from typing import Optional, Union, List
from urllib.error import URLError

from dimples import ID
from dimples import Content
from dimples import TextContent
from dimples import CommonFacebook

from ...utils import Logging

from ...client import Emitter

from ...chat import Request
from ...chat import ChatBox, ChatClient

from .chatbot import NLPBot


class NLPChatBox(ChatBox, Logging):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook, bots: Union[list, NLPBot]):
        super().__init__(identifier=identifier, facebook=facebook)
        if isinstance(bots, List):
            count = len(bots)
            if count > 1:
                # set bots with random order
                bots = random.sample(bots, count)
        else:
            assert isinstance(bots, NLPBot), 'chat bot error: %s' % bots
            bots = [bots]
        self.__bots = bots

    def _ask_bots(self, question: str, identifier: ID) -> Optional[str]:
        all_bots = self.__bots
        if all_bots is None:
            self.error('chat bots not set')
            return 'Chat bot not found'
        user = str(identifier.address)
        if len(user) > 32:
            user = user[-32:]
        # try each chat bots
        index = 0
        for bot in all_bots:
            answer = bot.ask(question=question, user=user)
            if answer is None:
                index += 1
                continue
            # got the answer
            if index > 0:
                # move this bot to front
                self.__bots.remove(bot)
                self.__bots.insert(0, bot)
            return answer

    # Override
    def _say_hi(self, prompt: str, request: Request):
        return True

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request) -> bool:
        try:
            answer = self._ask_bots(question=prompt, identifier=request.identifier)
            if answer is None:
                answer = self.NOT_FOUND
            elif len(answer) == 0:
                answer = self.NO_CONTENT
        except URLError as error:
            self.error('%s' % error)
            return False
        self.respond_text(text=answer, request=request)
        self._save_response(prompt=prompt, text=answer, request=request)
        return True

    # Override
    def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)


class NLPChatClient(ChatClient):

    def __init__(self, facebook: CommonFacebook, bots: Union[list, NLPBot]):
        super().__init__()
        self.__facebook = facebook
        self.__bots = bots

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        bots = self.__bots
        return NLPChatBox(identifier=identifier, facebook=facebook, bots=bots)
