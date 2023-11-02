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
from typing import Optional, Set

from dimples import ID

from ...utils import hex_decode, base58_decode
from ...utils import Singleton
from ...utils import Runner, Logging
from ...utils import HttpClient
from ..chat import ChatRequest, ChatCallback, ChatTask, ChatTaskPool

from .gpt35 import AIChatOS


def check_code(identifier: ID) -> int:
    address = str(identifier.address)
    if address.startswith('0x'):
        # ETH address
        data = hex_decode(string=address[2:])
    else:
        # BTC address
        data = base58_decode(string=address)
    # convert last 4 bytes to int
    if len(data) > 4:
        data = data[-4:]
    return int.from_bytes(data, byteorder='big', signed=False)


#
#   Chat Box
#


class ChatBox(Logging):

    EXPIRES = 36000  # seconds

    def __init__(self, user_id: int, referer: str, http_client: HttpClient):
        super().__init__()
        self.__gpt = AIChatOS(user_id=user_id, referer=referer, http_client=http_client)
        self.__expired = time.time() + self.EXPIRES

    def is_expired(self, now: float) -> bool:
        return now > self.__expired

    def __prepare(self) -> bool:
        self.__expired = time.time() + self.EXPIRES
        gpt = self.__gpt
        # check cookies
        acw_tc = gpt.get_cookie(key='acw_tc')
        cdn_sec_tc = gpt.get_cookie(key='cdn_sec_tc')
        if acw_tc is None or cdn_sec_tc is None:
            # get cookies
            gpt.auth_session()
            acw_tc = gpt.get_cookie(key='acw_tc')
            cdn_sec_tc = gpt.get_cookie(key='cdn_sec_tc')
            if acw_tc is None or cdn_sec_tc is None:
                self.error(msg='failed to get cookies')
                return False
        # OK
        self.info(msg='ChatGPT is ready: %s, %s' % (acw_tc, cdn_sec_tc))
        return True

    def ask(self, question: str) -> Optional[str]:
        try:
            if self.__prepare():
                return self.__gpt.ask(question=question)
        except Exception as error:
            self.error(msg='failed to ask question: %s, %s' % (question, error))


class ChatBoxPool(Logging):

    def __init__(self):
        super().__init__()
        self.__map = weakref.WeakValueDictionary()  # ID => ChatBox
        self.__boxes: Set[ChatBox] = set()          # Set[ChatBox]
        self.__lock = threading.Lock()
        self.__next_purge_time = 0

    @classmethod
    def __new_box(cls, identifier: ID, referer: str, http_client: HttpClient) -> Optional[ChatBox]:
        user_id = check_code(identifier=identifier)
        return ChatBox(user_id=user_id, referer=referer, http_client=http_client)

    def get_box(self, identifier: ID, http_client: HttpClient, referer: str) -> Optional[ChatBox]:
        with self.__lock:
            box = self.__map.get(identifier)
            if box is None:
                box = self.__new_box(identifier=identifier, referer=referer, http_client=http_client)
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
class ChatClient(Runner, Logging):

    BASE_URL = 'https://api.binjie.fun'
    REFERER_URL = 'https://chat.aichatos.top'

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__client_ref: Optional[weakref.ReferenceType] = None
        self.__client_expired = 0
        # pools
        self.__box_pool = ChatBoxPool()
        self.__task_pool = ChatTaskPool()

    @property
    def http_client(self) -> HttpClient:
        client = None if self.__client_ref is None else self.__client_ref()
        now = time.time()
        if client is None or now > self.__client_expired:
            self.warning(msg='create http client: %s' % self.BASE_URL)
            client = HttpClient(long_connection=True, verify=False, base_url=self.BASE_URL)
            self.__client_ref = weakref.ref(client)
            self.__client_expired = now + ChatBox.EXPIRES
        return client

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
        http_client = self.http_client
        referer = self.REFERER_URL
        box = self.__box_pool.get_box(identifier=identifier, http_client=http_client, referer=referer)
        if box is None:
            self.error(msg='failed to get chat box, drop request from %s: "%s"' % (identifier, question))
            return False
        answer = box.ask(question=question)
        if answer is None:
            self.error(msg='failed to get answer, drop request from %s: "%s"' % (identifier, question))
            answer = '{\n\t"code": 404,\n\t"error": "No response, please try again later."\n}'
        elif answer.startswith('sorry') and answer.find('(vpn)') > 0:
            answer = '{\n\t"code": 403,\n\t"error": "Request forbidden, please contact the web-master."\n}'
        elif answer.find('binjie') >= 0:
            answer = answer.replace('binjie', ' Gigi ')
        # OK
        task.chat_response(answer=answer, request=request)
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
