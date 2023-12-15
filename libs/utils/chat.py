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
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set, Dict

from dimples import DateTime
from dimples import ID
from dimples import CommonFacebook

from dimples.utils import Logging, Runner, Singleton
from dimples.utils import template_replace

from .http import HttpClient


def combine_language(language: Optional[str], locale: Optional[str], default: str) -> str:
    # if 'language' not found:
    #     return 'locale' or default code
    if language is None or len(language) == 0:
        if locale is None or len(locale) == 0:
            return default
        else:
            return locale
    # if 'locale' not found
    #     return 'language'
    if locale is None or len(locale) == 0:
        return language
    assert isinstance(language, str)
    assert isinstance(locale, str)
    # combine 'language' and 'locale'
    lang = language.lower()
    if lang == 'zh_cn':
        language = 'zh_Hans'
    elif lang == 'zh_tw':
        language = 'zh_Hant'
    else:
        pos = language.rfind('_')
        if pos > 0:
            language = language[:pos]
    pos = locale.rfind('_')
    if pos > 0:
        locale = locale[pos+1:]
    return '%s_%s' % (language, locale)


def greeting_prompt(identifier: ID, facebook: CommonFacebook) -> str:
    visa = facebook.document(identifier=identifier)
    if visa is None:
        language = 'en'
    else:
        # check 'app:language'
        app = visa.get_property(key='app')
        if isinstance(app, Dict):
            language = app.get('language')
        else:
            language = None
        # check 'sys:locale'
        sys = visa.get_property(key='sys')
        if isinstance(sys, Dict):
            locale = sys.get('locale')
        else:
            locale = None
        # combine them
        language = combine_language(language=language, locale=locale, default='en')
    # greeting with language code
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
        self.__role_bot = ''

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

    @property
    def role_bot(self) -> str:
        return self.__role_bot

    @role_bot.setter
    def role_bot(self, text):
        self.__role_bot = text

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        from bots.shared import GlobalVariable
        shared = GlobalVariable()
        return shared.facebook

    @property
    def nickname(self) -> Optional[str]:
        user = self.identifier
        facebook = self.facebook
        if facebook is not None:
            doc = facebook.document(identifier=user)
            if doc is not None:
                return doc.name

    #
    #   Say Hi
    #
    GREETING_PROMPT = 'greeting:{language}'

    @property
    def is_greeting(self) -> bool:
        return self.prompt.startswith('greeting:')

    @property
    def language_code(self) -> Optional[str]:
        assert self.is_greeting, 'not a greeting: %s' % self.prompt
        text = self.prompt
        pair = text.split(':')
        assert len(pair) == 2, 'greeting error: %s' % text
        if pair[1].startswith('{'):
            assert False, 'greeting error: %s' % text
        else:
            return pair[1]

    @property
    def system_setting(self) -> Optional[str]:
        name = self.nickname
        lang = self.language_code
        if lang is None or len(lang) == 0:
            lang = 'en'
        # content = 'You are ChatGPT, a large language model trained by OpenAI.\n' \
        #           'Carefully heed the user\'s instructions.\n' \
        #           'Respond using Markdown.'
        # 1. setting username & language
        if name is None or len(name) == 0:
            setting = 'My current language environment code is "%s".\n' \
                      'Please consider a language that suits me.' % lang
        else:
            setting = 'My name is "%s", and my current language environment code is "%s".\n' \
                      'Please consider a language that suits me.' % (name, lang)
        # 2. combine settings
        return '%s\nYou are set as a little assistant who is good at listening' \
               ' and willing to answer any questions.\n%s' % (self.role_bot, setting)

    @property
    def greeting(self) -> str:
        name = self.nickname
        if name is None or len(name) == 0:
            return 'Please greet me in a language that suits me,' \
                   ' considering my language habits and location' \
                   ' and attempting to spark a new conversation.'
        else:
            return 'Please greet me in a language that suits me,' \
                   ' considering my language habits and location' \
                   ' and attempting to spark a new conversation.' \
                   ' Please keep my fullname from being translated.'


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

    def presume(self, system_content: str):
        """ system setting """
        raise NotImplemented

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
        self.__role_bot = 'Your name is "Gigi", a smart and beautiful girl.'

    @property
    def role_bot(self) -> str:
        return self.__role_bot

    @role_bot.setter
    def role_bot(self, text):
        self.__role_bot = text

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
        request.role_bot = self.role_bot
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
        identifier = request.identifier
        box = self._get_box(identifier=identifier)
        if box is None:
            self.error(msg='failed to get chat box, drop request from %s: "%s"' % (identifier, request.prompt))
            return False
        if request.is_greeting:
            # presume language environment and get greeting text
            box.presume(system_content=request.system_setting)
            prompt = request.greeting
        else:
            prompt = request.prompt
        # send request
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
