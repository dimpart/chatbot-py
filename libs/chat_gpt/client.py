#! /usr/bin/env python3
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

import threading
import time
import weakref
from abc import ABC, abstractmethod
from typing import Optional, Set

from dimples import ID
from dimples.utils import Runner, Logging


from .http import HttpSession
from .token import SharedToken
from .gpt35 import SharedGPT


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


class ChatTask(ChatCallback):

    def __init__(self, request: ChatRequest, callback: ChatCallback):
        super().__init__()
        self.__request = request
        self.__callback = callback

    @property
    def request(self) -> ChatRequest:
        return self.__request

    # Override
    def chat_response(self, answer: str, request: ChatRequest):
        self.__callback.chat_response(answer=answer, request=request)


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


#
#   Chat Box
#


class ChatBox(Logging):

    EXPIRES = 36000  # seconds

    def __init__(self, base_url: str, session_key: str, data_token: str, http_session: HttpSession):
        super().__init__()
        gpt = SharedGPT(base_url=base_url, session_key=session_key, data_token=data_token, http_session=http_session)
        self.__gpt = gpt
        self.__expired = time.time() + self.EXPIRES

    def is_expired(self, now: float) -> bool:
        return now > self.__expired

    def __prepare(self) -> bool:
        self.__expired = time.time() + self.EXPIRES
        gpt = self.__gpt
        # check cookies
        if gpt.get_cookie(key='credential') is None:
            # 1. login and update 'credential' into cookies
            gpt.auth_login()
            # 2. fetch 'accessToken'
            gpt.auth_session()
            if gpt.get_cookie(key='credential') is None:
                self.error(msg='failed to fetch access token')
                return False
        # check account
        if gpt.account_id is None:
            # 3. fetch 'account_id'
            gpt.accounts_check()
            if gpt.account_id is None:
                self.warning(msg='failed to fetch account id')
                # return False
        # check model
        if gpt.default_model is None:
            # 4. fetch 'default_model'
            gpt.models()
            if gpt.default_model is None:
                self.error(msg='failed to fetch model name')
                return False
            # 5. fetch conversations
            gpt.conversations()
            if gpt.conversation_id is None:
                self.warning(msg='failed to fetch conversations')
                # return False
        # OK
        aid = gpt.account_id
        model = gpt.default_model
        session_key = gpt.session_key
        self.info(msg='ChatGPT is ready (%s): %s, session key: %s' % (model, aid, session_key))
        return True

    def ask(self, question: str) -> Optional[str]:
        if self.__prepare():
            return self.__gpt.ask(question=question)


class ChatBoxPool(Logging):

    BASE_URL = 'https://chat-shared.zhile.io'

    def __init__(self):
        super().__init__()
        self.__map = weakref.WeakValueDictionary()  # ID => ChatBox
        self.__boxes: Set[ChatBox] = set()          # Set[ChatBox]
        self.__lock = threading.Lock()
        self.__next_purge_time = 0

    def __new_box(self, session_key: str, token: dict, http_session: HttpSession) -> Optional[ChatBox]:
        token_id = token.get('token_id')
        if token_id is None:
            self.error(msg='failed to create GPT client without token id')
            return None
        if len(session_key) > 16:
            session_key = session_key[-16:]
        base_url = self.BASE_URL
        return ChatBox(base_url=base_url, session_key=session_key, data_token=token_id, http_session=http_session)

    def get_box(self, identifier: ID, token: dict = None, http_session: HttpSession = None) -> Optional[ChatBox]:
        with self.__lock:
            box = self.__map.get(identifier)
            if box is None and token is not None and http_session is not None:
                box = self.__new_box(session_key=str(identifier), token=token, http_session=http_session)
                if box is not None:
                    self.__map[identifier] = box
                    self.__boxes.add(box)
            return box

    def purge(self):
        now = time.time()
        if now < self.__next_purge_time:
            return False
        else:
            self.__next_purge_time = now + 60
        # remove expired box(es)
        with self.__lock:
            boxes = self.__boxes.copy()
            for box in boxes:
                if box.is_expired(now=now):
                    self.__boxes.discard(box)
        return True


class ChatClient(Runner, Logging):

    BASE_URL = 'https://chat-shared.zhile.io'
    TOKEN_URL = 'https://chat-shared.zhile.io/api/loads'

    def __init__(self):
        super().__init__()
        self.__session = HttpSession(long_connection=True)
        # tokens
        self.__loads = SharedToken(url=self.TOKEN_URL, session=self.__session)
        # pools
        self.__box_pool = ChatBoxPool()
        self.__task_pool = ChatTaskPool()

    def get_box(self, identifier: ID) -> Optional[ChatBox]:
        return self.__box_pool.get_box(identifier=identifier)

    def request(self, question: str, identifier: ID, callback: ChatCallback):
        request = ChatRequest(question=question, identifier=identifier)
        task = ChatTask(request=request, callback=callback)
        self.__task_pool.add_task(task=task)

    # Override
    def process(self) -> bool:
        task = self.__task_pool.pop_task()
        if task is None:
            # nothing to do now, pure expired boxes
            self.__box_pool.purge()
            return False
        request = task.request
        question = request.question
        identifier = request.identifier
        any_token = self.__loads.any
        http_session = self.__session
        box = self.__box_pool.get_box(identifier=identifier, token=any_token, http_session=http_session)
        if box is None:
            self.error(msg='failed to get chat box, drop request from %s: "%s"' % (identifier, question))
            return False
        answer = box.ask(question=question)
        if answer is None:
            self.error(msg='failed to get answer, drop request from %s: "%s"' % (identifier, question))
            return False
        # OK
        task.chat_response(answer=answer, request=request)
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
