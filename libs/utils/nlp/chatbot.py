# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Chat Bot
    ~~~~~~~~

    AI chat bots
"""

import random
from abc import ABC, abstractmethod
from typing import Union, List

from dimples import ID
from dimples import Content, TextContent, AudioContent


class ChatBot(ABC):

    @abstractmethod
    def ask(self, question: str, user: str = None) -> str:
        """Talking with the chat bot

            :param question - text message string
            :param user - sender ID number
            :return answer string
        """
        pass


class Dialog:
    """
        Dialog Bot
        ~~~~~~~~~~

        Dialog for chatting with station
    """

    def __init__(self):
        super().__init__()
        # chat bot candidates
        self.__bots = []

    @property
    def bots(self) -> List[ChatBot]:
        return self.__bots

    @bots.setter
    def bots(self, array: Union[list, ChatBot]):
        if isinstance(array, list):
            count = len(array)
            if count > 1:
                # set bots with random order
                self.__bots = random.sample(array, count)
            else:
                self.__bots = array
        elif isinstance(array, ChatBot):
            self.__bots = [array]
        else:
            raise ValueError('bots error: %s' % array)

    def ask(self, question: str, sender: ID) -> str:
        # try each chat bots
        user = str(sender.address)
        if len(user) > 32:
            user = user[-32:]
        index = 0
        for bot in self.__bots:
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

    def query(self, content: Content, sender: ID) -> TextContent:
        if isinstance(content, TextContent):
            # text dialog
            question = content.text
            answer = self.ask(question=question, sender=sender)
            if answer is not None:
                response = TextContent.create(text=answer)
                req_time = content.time
                res_time = response.time
                print('checking respond time: %s, %s' % (res_time, req_time))
                if res_time is None or res_time <= req_time:
                    response['time'] = req_time + 1
                group = content.group
                if group is not None:
                    response.group = group
                return response
        elif isinstance(content, AudioContent):
            # TODO: Automatic Speech Recognition
            pass
