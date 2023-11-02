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

import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional

from dimples import DateTime
from dimples import ID
from dimples.database import Storage

from ..utils import json_encode
from ..utils import Logging
from ..utils import Singleton


#
#   Chat Task
#

class ChatRequest:

    def __init__(self, question: str, identifier: ID):
        super().__init__()
        self.__question = question
        self.__identifier = identifier

    @property
    def question(self) -> str:
        return self.__question

    @property
    def identifier(self) -> ID:
        return self.__identifier


class ChatCallback(ABC):

    @abstractmethod
    def chat_response(self, answer: str, request: ChatRequest):
        raise NotImplemented


class ChatTask(Logging, ChatCallback):

    def __init__(self, request: ChatRequest, callback: ChatCallback):
        super().__init__()
        self.__request = request
        self.__callback = callback

    @property
    def request(self) -> ChatRequest:
        return self.__request

    # Override
    def chat_response(self, answer: str, request: ChatRequest):
        try:
            self.__callback.chat_response(answer=answer, request=request)
        except Exception as error:
            self.error(msg='failed to response: %s' % error)


class ChatTaskPool:

    def __init__(self):
        super().__init__()
        self.__tasks = []
        self.__lock = threading.Lock()

    def add_task(self, task: ChatTask):
        with self.__lock:
            self.__tasks.append(task)

    def pop_task(self) -> Optional[ChatTask]:
        with self.__lock:
            if len(self.__tasks) > 0:
                return self.__tasks.pop(0)


@Singleton
class ChatStorage(Logging):

    def __init__(self):
        super().__init__()
        self.__root = None  # '/var/dim/protected'
        self.__user = None

    @property
    def root(self) -> Optional[str]:
        return self.__root

    @root.setter
    def root(self, path: str):
        self.__root = path

    @property
    def bot(self) -> Optional[ID]:
        return self.__user

    @bot.setter
    def bot(self, identifier: ID):
        self.__user = identifier

    def get_path(self, now: DateTime) -> Optional[str]:
        """ get current save path """
        root = self.root
        user = self.bot
        if root is None or user is None:
            self.debug(msg='chat history not config')
            return None
        filename = 'chat-%s.txt' % time.strftime('%Y-%m-%d', now.localtime)
        return os.path.join(root, str(user), filename)

    def save_response(self, question: str, answer: str, identifier: ID, name: str) -> bool:
        now = DateTime.now()
        path = self.get_path(now=now)
        if path is None:
            self.info(msg='cannot get storage path for chat response')
            return False
        info = {
            'ID': str(identifier),
            'name': name,
            'time': str(now),
            'prompt': question,
            'result': answer,
        }
        text = '%s,\n' % json_encode(info)
        return Storage.append_text(text=text, path=path)
