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

from .model import TensorArt


#
#   Chat Box
#


class ChatBox(SuperBox):

    def __init__(self, referer: str, http_client: HttpClient):
        super().__init__()
        sd = TensorArt(referer=referer, http_client=http_client)
        self.__sd = sd

    # noinspection PyMethodMayBeStatic
    def __build_text(self, projects: List[Dict]) -> str:
        names = []
        for item in projects:
            text = item.get('name')
            if text is not None and len(text) > 0:
                names.append(text)
        return 'You can also input:\n    %s' % '\n    '.join(names)

    # Override
    def _ask(self, question: str) -> Optional[List]:
        projects = self.__sd.search(keywords=question)
        count = 0 if projects is None else len(projects)
        if count == 0:
            return [ChatCallback.NO_CONTENT]
        # build text message
        text = self.__build_text(projects=projects)
        if count > 3:
            projects = projects[:3]
        responses = []
        for item in projects:
            responses.append(item)
        responses.append(text)
        return responses


class ChatBoxPool(SuperPool):

    # Override
    def _new_box(self, params: Dict) -> Optional[ChatBox]:
        referer = params.get('referer')
        http_client = params.get('http_client')
        return ChatBox(referer=referer, http_client=http_client)


@Singleton
class DrawClient(SuperClient):

    BASE_URL = 'https://api.tensor.art'
    REFERER_URL = 'https://tensor.art/'

    def __init__(self):
        super().__init__()
        self.__box_pool = ChatBoxPool()

    # Override
    def _create_http(self) -> HttpClient:
        base = self.BASE_URL
        return HttpClient(long_connection=True, verify=False, base_url=base)

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
