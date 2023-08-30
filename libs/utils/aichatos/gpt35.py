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

from typing import Optional

from dimples.utils import utf8_encode, utf8_decode, json_encode


from ..gpt.http import HttpClient, HttpSession, show_response


class AIChatOS(HttpClient):
    """
        AI Chat OS
        ~~~~~~~~~~

        https://chat.aichatos.top/
    """

    def __init__(self, base_url: str, referer: str, http_session: HttpSession = None):
        super().__init__(session=http_session, long_connection=True, base=base_url)
        self.__referer = referer

    def auth_session(self):
        response = self.http_get(url='/api/generateStream', headers={
            # 'Content-Type': 'application/json',
            'Origin': self.__referer,
            'Referer': self.__referer,
        })
        show_response(response=response)

    def ask(self, question: str, user_id: int) -> Optional[str]:
        info = {
            'prompt': question,
            'userId': '#/chat/%d' % user_id,
            'network': True,
            'system': '',
            'withoutContext': False,
            'stream': False,
        }
        self.info(msg='sending message: %s' % info)
        data = utf8_encode(string=json_encode(obj=info))
        response = self.http_post(url='/api/generateStream', headers={
            'Content-Type': 'application/json',
            'Origin': self.__referer,
            'Referer': self.__referer,
        }, data=data)
        # show_response(response=response)
        return utf8_decode(data=response.content)
