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

from ...client import Emitter

from ...chat import Greeting, ChatRequest
from ...chat import ChatBox, ChatClient

from .chatbot import NLPBot


class NLPChatBox(ChatBox):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook, bots: List[NLPBot]):
        super().__init__(identifier=identifier, facebook=facebook)
        self.__bots = bots

    def _ask_bots(self, question: str, identifier: ID) -> Optional[str]:
        all_bots = self.__bots
        if len(all_bots) == 0:
            self.error(msg='chat bots not set')
            return 'Chat bot not found'
        user = str(identifier.address)
        if len(user) > 32:
            user = user[-32:]
        # try each chat bots
        index = 0
        for bot in all_bots:
            answer = bot.ask(question=question, user=user)
            if answer is None or len(answer) == 0:
                self.error(msg='failed to ask bot: %s' % bot)
                index += 1
                continue
            # got the answer
            if index > 0:
                # move this bot to front
                self.warning(msg='move bot position: %d, %s' % (index, bot))
                self.__bots.remove(bot)
                self.__bots.insert(0, bot)
            # OK
            return answer

    # Override
    async def _say_hi(self, prompt: str, request: Greeting):
        return True

    # Override
    async def _ask_question(self, prompt: str, content: TextContent, request: ChatRequest) -> bool:
        try:
            answer = self._ask_bots(question=prompt, identifier=request.identifier)
            if answer is None:
                answer = self.NOT_FOUND
            elif len(answer) == 0:
                answer = self.NO_CONTENT
        except URLError as error:
            self.error('%s' % error)
            return False
        await self.respond_text(text=answer, request=request)
        await self._save_response(prompt=prompt, text=answer, request=request)
        return True

    # Override
    async def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        await emitter.send_content(content=content, receiver=receiver)


class NLPChatClient(ChatClient):

    def __init__(self, facebook: CommonFacebook, bots: Union[List, NLPBot]):
        super().__init__()
        self.__facebook = facebook
        if isinstance(bots, List):
            self.__bots = bots
        else:
            assert isinstance(bots, NLPBot), 'NLP bots error: %s' % bots
            self.__bots = [bots]

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        # copy bots in random order
        bots = self.__bots.copy()
        count = len(bots)
        if count > 1:
            bots = random.sample(bots, count)
        return NLPChatBox(identifier=identifier, facebook=facebook, bots=bots)
