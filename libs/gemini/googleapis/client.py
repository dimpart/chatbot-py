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

from typing import Optional, List, Dict

from dimples import ID

from ...utils import Singleton
from ...utils import HttpClient
from ...utils import ChatCallback
from ...utils import ChatBox as SuperBox
from ...utils import ChatBoxPool as SuperPool
from ...utils import ChatClient as SuperClient

from .genai import GenerativeAI


#
#   Chat Box
#


class ChatBox(SuperBox):

    def __init__(self, referer: str, auth_token: str, http_client: HttpClient):
        super().__init__()
        gemini = GenerativeAI(referer=referer, auth_token=auth_token, http_client=http_client)
        self.__gemini = gemini

    # Override
    def presume(self, system_content: str):
        self.__gemini.presume(system_content=system_content)

    # Override
    def _ask(self, question: str) -> Optional[List]:
        answer = self.__gemini.ask(question=question)
        if answer is None:
            return None
        elif len(answer) == 0:
            return [ChatCallback.NO_CONTENT]
        else:
            return [answer]


class ChatBoxPool(SuperPool):

    # Override
    def _new_box(self, params: Dict) -> Optional[ChatBox]:
        auth_token = 'GOOGLE_API_KEY'
        referer = params.get('referer')
        http_client = params.get('http_client')
        return ChatBox(referer=referer, auth_token=auth_token, http_client=http_client)


@Singleton
class ChatClient(SuperClient):

    BASE_URL = 'https://generativelanguage.googleapis.com'
    REFERER_URL = 'https://generativelanguage.googleapis.com/'

    def __init__(self):
        super().__init__()
        self.__box_pool = ChatBoxPool()

    # Override
    def _create_http(self) -> HttpClient:
        base = self.BASE_URL
        return HttpClient(long_connection=True, base_url=base)

    # Override
    def _get_box(self, identifier: ID) -> Optional[ChatBox]:
        params = {
            'referer': self.REFERER_URL,
            'http_client': self.http,
        }
        return self.__box_pool.get_box(identifier=identifier, params=params)

    # Override
    def _purge(self):
        self.__box_pool.purge()
