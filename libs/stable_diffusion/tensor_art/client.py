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

import random
import threading
import time
import weakref
from typing import Optional, Union, Set, List, Dict

from dimples import ID
from dimples.utils import Singleton
from dimples.utils import Runner, Logging


from ...utils import HttpSession
from ..chat import ChatRequest, ChatCallback, ChatTask, ChatTaskPool

from .model import TensorArt


#
#   Chat Box
#


class ChatBox(Logging):

    EXPIRES = 36000  # seconds

    def __init__(self, base_url: str, referer: str, http_session: HttpSession):
        super().__init__()
        sd = TensorArt(base_url=base_url, referer=referer, http_session=http_session)
        self.__sd = sd
        self.__expired = time.time() + self.EXPIRES

    def is_expired(self, now: float) -> bool:
        return now > self.__expired

    def __prepare(self) -> bool:
        self.__expired = time.time() + self.EXPIRES
        return True

    # noinspection PyMethodMayBeStatic
    def __build_text(self, projects: List[Dict]) -> str:
        names = []
        for item in projects:
            text = item.get('name')
            if text is not None and len(text) > 0:
                names.append(text)
        return 'You can also input:\n    %s' % '\n    '.join(names)

    def request(self, prompt: str) -> Optional[List[Union[Dict, str]]]:
        try:
            if self.__prepare():
                projects = self.__sd.search(keywords=prompt)
                if len(projects) > 0:
                    # pick any project
                    item = random.choice(projects)
                    # build text message
                    text = self.__build_text(projects=projects)
                    return [item, text]
                else:
                    return [ChatCallback.NO_CONTENT]
        except Exception as error:
            self.error(msg='failed to search: %s, %s' % (prompt, error))


class ChatBoxPool(Logging):

    def __init__(self):
        super().__init__()
        self.__map = weakref.WeakValueDictionary()  # ID => ChatBox
        self.__boxes: Set[ChatBox] = set()          # Set[ChatBox]
        self.__lock = threading.Lock()
        self.__next_purge_time = 0

    @classmethod
    def __new_box(cls, base_url: str, referer: str, http_session: HttpSession) -> Optional[ChatBox]:
        return ChatBox(base_url=base_url, referer=referer, http_session=http_session)

    def get_box(self, identifier: ID, base_url: str, referer: str, http_session: HttpSession) -> Optional[ChatBox]:
        with self.__lock:
            box = self.__map.get(identifier)
            if box is None:
                box = self.__new_box(base_url=base_url, referer=referer, http_session=http_session)
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


@Singleton
class DrawClient(Runner, Logging):

    BASE_URL = 'https://api.tensor.art'
    REFERER_URL = 'https://tensor.art/'

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__client_ref: Optional[weakref.ReferenceType] = None
        self.__client_expired = 0
        # pools
        self.__box_pool = ChatBoxPool()
        self.__task_pool = ChatTaskPool()

    @property
    def http_session(self) -> HttpSession:
        client = None if self.__client_ref is None else self.__client_ref()
        now = time.time()
        if client is None or now > self.__client_expired:
            self.warning(msg='create http session: %s' % self.BASE_URL)
            client = HttpSession(long_connection=True, verify=False)
            self.__client_ref = weakref.ref(client)
            self.__client_expired = now + ChatBox.EXPIRES
        return client

    def request(self, prompt: str, identifier: ID, callback: ChatCallback):
        request = ChatRequest(prompt=prompt, identifier=identifier)
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
        prompt = request.prompt
        identifier = request.identifier
        http_session = self.http_session
        base = self.BASE_URL
        referer = self.REFERER_URL
        box = self.__box_pool.get_box(identifier=identifier, base_url=base, referer=referer, http_session=http_session)
        if box is None:
            self.error(msg='failed to get chat box, drop request from %s: "%s"' % (identifier, prompt))
            return False
        results = box.request(prompt=prompt)
        if results is None:
            self.error(msg='failed to get results, drop request from %s: "%s"' % (identifier, prompt))
            results = [ChatCallback.NOT_FOUND]
        # OK
        task.chat_response(results=results, request=request)
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
