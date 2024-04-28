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

from dimples import ID
from dimples import Content, TextContent
from dimples import CommonFacebook

from ...utils import HttpClient
from ...chat import Request, Setting
from ...chat import ChatBox, ChatClient
from ...client import Emitter
from ...client import Monitor

from .genai import GenerativeAI


#
#   Chat Box
#


class GeminiChatBox(ChatBox):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook,
                 referer: str, auth_token: str, http_client: HttpClient,
                 setting: Setting):
        super().__init__(identifier=identifier, facebook=facebook)
        gemini = GenerativeAI(referer=referer, auth_token=auth_token, http_client=http_client)
        gemini.presume(system_content=setting.text)
        self.__gemini = gemini

    def _query(self, prompt: str) -> Optional[str]:
        monitor = Monitor()
        service = 'Gemini'
        # agent = 'GoogleAPI'
        agent = 'API'
        try:
            answer = self.__gemini.ask(question=prompt)
        except Exception as error:
            self.error(msg='failed to query google API, error: %s' % error)
            answer = None
        if answer is None or len(answer) == 0:
            self.error(msg='response error from google API')
            monitor.report_failure(service=service, agent=agent)
        else:
            monitor.report_success(service=service, agent=agent)
        return answer

    # Override
    def _say_hi(self, prompt: str, request: Request) -> bool:
        answer = self._query(prompt=prompt)
        if answer is not None and len(answer) > 0:
            self.respond_text(text=answer, request=request)
        self._save_response(prompt=prompt, text=answer, request=request)
        return True

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request) -> bool:
        answer = self._query(prompt=prompt)
        if answer is None:
            answer = self.NOT_FOUND
            self.respond_text(text=answer, request=request)
        elif len(answer) == 0:
            answer = self.NO_CONTENT
            self.respond_text(text=answer, request=request)
        else:
            self.respond_markdown(text=answer, request=request)
        self._save_response(prompt=prompt, text=answer, request=request)
        return True

    # Override
    def _send_content(self, content: Content, receiver: ID) -> bool:
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)
        return True


class GeminiChatClient(ChatClient):

    BASE_URL = 'https://generativelanguage.googleapis.com'
    REFERER_URL = 'https://generativelanguage.googleapis.com/'

    SYSTEM_SETTING = 'Your name is "Gege", a smart and handsome boy.' \
                     ' You are set as a little assistant who is good at listening' \
                     ' and willing to answer any questions.'

    def __init__(self, facebook: CommonFacebook, api_key: str):
        super().__init__()
        self.__facebook = facebook
        self.__api_key = api_key
        self.__http_client = HttpClient(long_connection=True, base_url=self.BASE_URL)
        self.__system_setting = Setting(definition=self.SYSTEM_SETTING)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        setting = self.__system_setting
        facebook = self.__facebook
        referer = self.REFERER_URL
        auth_token = self.__api_key
        http_client = self.__http_client
        return GeminiChatBox(identifier=identifier, setting=setting, facebook=facebook,
                             referer=referer, auth_token=auth_token, http_client=http_client)
