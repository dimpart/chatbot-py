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

from typing import Optional, Union, List

from requests import Response

from ....utils import utf8_encode, json_encode, json_decode
from ....utils import Log, Logging
from ....utils import HttpClient


class MessageQueue:

    MAX_SIZE = 10240
    MAX_COUNT = 8

    def __init__(self):
        super().__init__()
        self.__messages = []
        self.__size = 0

    @property
    def messages(self) -> List[dict]:
        return self.__messages

    def push(self, msg: dict, trim: bool = False):
        # simplify message data
        if trim:
            msg = self.__trim(msg=msg)
        # append to tail
        self.__messages.append(msg)
        self.__size += len(json_encode(obj=msg))
        # check data size of the queue
        while self.__size > self.MAX_SIZE:
            if len(self.__messages) < self.MAX_COUNT:
                break
            first = self.__messages.pop(0)
            self.__size -= len(json_encode(obj=first))

    # noinspection PyMethodMayBeStatic
    def __trim(self, msg: dict) -> dict:
        content = msg.get('content')
        role = msg.get('role')
        return {
            'content': content,
            'role': role,
        }


class GPTHandler(Logging):
    """
        CAI Free
        ~~~~~~~~

        https://chat.caifree.com/api/openai/v1/chat/completions

    """

    def __init__(self, referer: str, auth_token: str, http_client: HttpClient):
        super().__init__()
        self.__http_client = http_client
        self.__referer = referer
        self.__auth_token = auth_token
        # messages
        self.__message_queue = MessageQueue()
        self.__system_setting: Optional[dict] = None

    def http_post(self, url: str, data: Union[dict, bytes], headers: dict = None) -> Response:
        return self.__http_client.http_post(url=url, data=data, headers=headers)

    def presume(self, system_content: str):
        assert system_content is not None and len(system_content) > 0, 'presume error'
        self.__system_setting = {
            'content': system_content,
            'role': 'system',
        }

    def _build_messages(self, question: str) -> List[dict]:
        msg = {
            'content': question,
            'role': 'user',
        }
        self.__message_queue.push(msg=msg)
        messages = self.__message_queue.messages
        settings = self.__system_setting
        if settings is not None:
            # insert system settings in the front
            messages = messages.copy()
            messages.insert(0, settings)
        return messages

    def ask(self, question: str) -> Optional[str]:
        messages = self._build_messages(question=question)
        info = {
            "messages": messages,
            # "model": "gpt-4",
            # "temperature": 1,
            "model": "gpt-3.5-turbo",
            "temperature": 0.5,
            "presence_penalty": 0,
            "top_p": 1,
            "frequency_penalty": 0,
            "stream": False,
        }
        self.info(msg='sending message: %s' % info)
        data = utf8_encode(string=json_encode(obj=info))
        response = self.http_post(url='/api/openai/v1/chat/completions', headers={
            # 'Accept': 'application/json, text/event-stream',
            'Content-Type': 'application/json',
            # 'Authorization': self.__auth_token,
            'Origin': self.__referer,
            'Referer': self.__referer,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/116.0.0.0 Safari/537.36',
        }, data=data)
        # show_response(response=response)
        msg = parse_response(text=response.text)
        if msg is None:
            self.error(msg='failed to parse response: %s' % response.text)
        else:
            self.__message_queue.push(msg=msg, trim=True)
            content = msg.get('content')
            if isinstance(content, str):
                return content


def parse_response(text: str) -> Optional[dict]:
    try:
        info = json_decode(string=text)
        choices = info.get('choices')
        if isinstance(choices, List) and len(choices) > 0:
            return choices[0].get('message')
        error = info.get('error')
        if error is not None:
            return {
                'content': error['message'],
                'role': 'assistant',
            }
    except Exception as e:
        Log.error(msg='failed to parse response: %s, error: %s' % (text, e))
        return None
