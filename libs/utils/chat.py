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

import random
import threading
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set, Dict

from dimples import DateTime
from dimples import ID
from dimples import CommonFacebook

from dimples.utils import Logging, Runner, Singleton
from dimples.utils import template_replace

from .http import HttpClient


def greeting_prompt(identifier: ID, facebook: CommonFacebook) -> str:
    visa = facebook.document(identifier=identifier)
    if visa is None:
        language = 'en'
    else:
        language = visa.get_property(key='language')
        if language is None or len(language) == 0:
            language = visa.get_property(key='locale')
            if language is None or len(language) == 0:
                language = 'en'
    template = ChatRequest.GREETING_PROMPT
    return template_replace(template=template, key='language', value=language)


#
#   Chat Task
#

class ChatRequest:

    def __init__(self, prompt: str, time: DateTime, identifier: ID):
        super().__init__()
        self.__prompt = prompt
        self.__time = time
        self.__identifier = identifier

    @property
    def prompt(self) -> str:
        """ request question """
        return self.__prompt

    @property
    def time(self) -> DateTime:
        """ request time """
        return self.__time

    @property
    def identifier(self) -> ID:
        """ request user/group """
        return self.__identifier

    #
    #   Say Hi
    #
    GREETING_PROMPT = 'greeting:{language}'

    __greetings = {
        'en': ['Hello!', 'Hi!'],
        'fr': ['Bonjour!'],
        'zh': ['你好！', '您好！'],
    }

    @classmethod
    def is_greeting(cls, text: str) -> bool:
        return text.startswith('greeting:')

    @classmethod
    def get_language(cls, text: str) -> Optional[str]:
        pair = text.split(':')
        assert len(pair) == 2, 'greeting error: %s' % text
        assert not pair[1].startswith('{'), 'language error: %s' % text
        return pair[1]

    @classmethod
    def greeting(cls, language: Optional[str]) -> str:
        # get language name
        if language is None:
            language = 'en'
        else:
            array = language.split('_')
            language = array[0]
        # get greetings
        greetings = cls.__greetings.get(language)
        if greetings is None:
            greetings = cls.__greetings.get('en')
            assert greetings is not None, 'failed to get greeting for language: %s' % language
        if isinstance(greetings, str):
            return greetings
        assert isinstance(greetings, List), 'greetings error: %s' % greetings
        if len(greetings) == 1:
            return greetings[0]
        else:
            return random.choice(greetings)


class ChatCallback(ABC):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    @classmethod
    def replace_at(cls, text: str, name: str) -> str:
        at = '@%s' % name
        if text.endswith(at):
            text = text[:-len(at)]
        at = '@%s ' % name
        return text.replace(at, '')

    @abstractmethod
    def chat_response(self, results: List, request: ChatRequest):
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
    def chat_response(self, results: List, request: ChatRequest):
        try:
            self.__callback.chat_response(results, request=request)
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


#
#   Chat Box
#
class ChatBox(Logging, ABC):

    EXPIRES = 36000  # seconds

    def __init__(self):
        super().__init__()
        self.__expired = DateTime.current_timestamp() + self.EXPIRES

    def is_expired(self, now: DateTime) -> bool:
        return now > self.__expired

    def request(self, prompt: str) -> Optional[List]:
        try:
            if self._prepare():
                return self._ask(prompt)
        except Exception as error:
            self.error(msg='failed to ask: %s, %s' % (prompt, error))

    def _prepare(self) -> bool:
        """ prepare box """
        self.__expired = DateTime.current_timestamp() + self.EXPIRES
        return True

    def _ask(self, question: str) -> Optional[List]:
        """ ask question """
        raise NotImplemented


class ChatBoxPool(Logging, ABC):

    def __init__(self):
        super().__init__()
        self.__map = weakref.WeakValueDictionary()  # ID => ChatBox
        self.__boxes: Set[ChatBox] = set()          # Set[ChatBox]
        self.__lock = threading.Lock()
        self.__next_purge_time = 0

    def purge(self):
        now = DateTime.now()
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

    def get_box(self, identifier: ID, params: Dict) -> Optional[ChatBox]:
        with self.__lock:
            box = self.__map.get(identifier)
            if box is None:
                box = self._new_box(params=params)
                if box is not None:
                    self.__map[identifier] = box
                    self.__boxes.add(box)
            return box

    def _new_box(self, params: Dict) -> Optional[ChatBox]:
        """ create chat box """
        raise NotImplemented


class ChatClient(Runner, Logging, ABC):

    def __init__(self, interval: float = None):
        if interval is None:
            interval = Runner.INTERVAL_SLOW
        super().__init__(interval=interval)
        self.__http_ref: Optional[weakref.ReferenceType] = None
        self.__http_expired = 0
        self.__task_pool = ChatTaskPool()

    @property
    def http(self) -> HttpClient:
        client = None if self.__http_ref is None else self.__http_ref()
        now = DateTime.current_timestamp()
        if client is None or now > self.__http_expired:
            client = self._create_http()
            self.__http_ref = weakref.ref(client)
            self.__http_expired = now + ChatBox.EXPIRES
        return client

    def _create_http(self) -> HttpClient:
        """ create http client """
        raise NotImplemented

    def _get_box(self, identifier: ID) -> Optional[ChatBox]:
        """ get chat box with user/group ID """
        raise NotImplemented

    def _purge(self):
        """ pure expired boxes """
        raise NotImplemented

    def request(self, prompt: str, time: DateTime, identifier: ID, callback: ChatCallback):
        request = ChatRequest(prompt=prompt, time=time, identifier=identifier)
        task = ChatTask(request=request, callback=callback)
        self.__task_pool.add_task(task=task)

    # Override
    def process(self) -> bool:
        task = self.__task_pool.pop_task()
        if task is None:
            # nothing to do now
            self._purge()
            return False
        request = task.request
        prompt = request.prompt
        if ChatRequest.is_greeting(text=prompt):
            # get greeting text with language
            language = ChatRequest.get_language(text=prompt)
            prompt = ChatRequest.greeting(language=language)
        identifier = request.identifier
        box = self._get_box(identifier=identifier)
        if box is None:
            self.error(msg='failed to get chat box, drop request from %s: "%s"' % (identifier, prompt))
            return False
        answers = box.request(prompt=prompt)
        if answers is None:
            self.error(msg='failed to get answer, drop request from %s: "%s"' % (identifier, prompt))
            answers = [ChatCallback.NOT_FOUND]
        # OK
        task.chat_response(answers, request=request)
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()


@Singleton
class Footprint:

    EXPIRES = 36000  # vanished after 10 hours

    def __init__(self):
        super().__init__()
        self.__active_times = {}  # ID => DateTime

    def __get_time(self, identifier: ID, when: Optional[DateTime]) -> Optional[DateTime]:
        now = DateTime.now()
        if when is None or when <= 0 or when >= now:
            return now
        elif when > self.__active_times.get(identifier, 0):
            return when
        # else:
        #     # time expired, drop it
        #     return None

    def touch(self, identifier: ID, when: DateTime = None):
        when = self.__get_time(identifier=identifier, when=when)
        if when is not None:
            self.__active_times[identifier] = when
            return True

    def is_vanished(self, identifier: ID, now: DateTime = None) -> bool:
        last_time = self.__active_times.get(identifier)
        if last_time is None:
            return True
        if now is None:
            now = DateTime.current_timestamp()
        return now > (last_time + self.EXPIRES)
