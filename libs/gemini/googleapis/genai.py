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
from typing import Optional, Union, List, Dict

from requests import Response

from ...utils import utf8_encode, json_encode, json_decode
from ...utils import Log, Logging
from ...utils import HttpClient


class MessageQueue:

    MAX_SIZE = 65536
    MAX_COUNT = 16

    def __init__(self):
        super().__init__()
        self.__messages = []
        self.__size = 0
        self.__lock = threading.Lock()

    @property
    def messages(self) -> List[dict]:
        with self.__lock:
            return self.__messages.copy()

    def push(self, msg: dict, trim: bool = False):
        with self.__lock:
            # simplify message data
            if trim:
                msg = self.__trim(msg=msg)
            msg = self.__check_conflict(msg=msg)
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
        # content = msg.get('content')
        # role = msg.get('role')
        # return {
        #     'content': content,
        #     'role': role,
        # }
        return msg

    # FIX: INVALID_ARGUMENT
    #   ensure that multiturn requests alternate between user and model;
    #   ensure that multiturn requests ends with a user role or a function response.
    def __check_conflict(self, msg: dict) -> dict:
        count = len(self.__messages)
        if count > 0:
            last = self.__messages[count - 1]
            if last.get('role') == msg.get('role'):
                self.__messages.pop(count - 1)
                self.__size -= len(json_encode(obj=last))
        return msg


class GenerativeAI(Logging):
    """
        Google - Generative AI
        ~~~~~~~~~~~~~~~~~~~~~~

        https://ai.google.dev/tutorials/python_quickstart
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
            'parts': [
                {
                    'text': system_content,
                }
            ],
            # 'role': 'system',
            'role': 'user',
        }

    def _build_messages(self, question: str) -> List[dict]:
        msg = {
            'parts': [
                {
                    'text': question,
                }
            ],
            'role': 'user',
        }
        self.__message_queue.push(msg=msg)
        messages = self.__message_queue.messages
        settings = self.__system_setting
        if settings is not None:
            # insert system settings in the front
            first = messages[0]
            # FIXME:
            if first.get('role') != settings.get('role'):
                # messages = messages.copy()
                messages.insert(0, settings)
            elif len(messages) == 1:
                # insert system setting
                text = first['parts']['text']
                first['parts']['text'] = '%s\n%s' % (settings, text)
        return messages

    def ask(self, question: str) -> Optional[str]:
        messages = self._build_messages(question=question)
        info = {
            'contents': messages,
            'safetySettings': [
                {
                    'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                    'threshold': 'BLOCK_NONE',
                },
                {
                    'category': 'HARM_CATEGORY_HATE_SPEECH',
                    'threshold': 'BLOCK_NONE',
                },
                {
                    'category': 'HARM_CATEGORY_HARASSMENT',
                    'threshold': 'BLOCK_NONE',
                },
                {
                    'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
                    'threshold': 'BLOCK_NONE',
                },
            ],
        }
        self.info(msg='sending message: %s' % info)
        data = utf8_encode(string=json_encode(obj=info))
        url = '/v1beta/models/gemini-pro:generateContent?key=%s' % self.__auth_token
        response = self.http_post(url=url, headers={
            'Content-Type': 'application/json',
            # 'Authorization': self.__auth_token,
            'Origin': self.__referer,
            'Referer': self.__referer,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/116.0.0.0 Safari/537.36',
        }, data=data)
        # show_response(response=response)
        info = parse_response(text=response.text)
        if info is None:
            self.error(msg='failed to parse response: %s' % response.text)
            return None
        msg = get_content(info=info)
        if msg is not None:
            self.__message_queue.push(msg=msg, trim=True)
            parts = msg.get('parts')
            if isinstance(parts, List):
                return get_text(parts=parts)
        Log.error(msg='failed to parse content: %s' % info)


def get_text(parts: List) -> str:
    lines = []
    for item in parts:
        if isinstance(item, Dict):
            text = item.get('text')
            if isinstance(text, str):
                lines.append(text)
    return '\n'.join(lines)


def get_content(info: Dict) -> Optional[Dict]:
    candidates = info.get('candidates')
    if isinstance(candidates, List) and len(candidates) > 0:
        first = candidates[0]
        if isinstance(first, Dict):
            content = first.get('content')
            if isinstance(content, Dict):
                return content


def parse_response(text: str) -> Optional[dict]:
    try:
        return json_decode(string=text)
    except Exception as e:
        Log.error(msg='failed to parse response: %s, error: %s' % (text, e))
