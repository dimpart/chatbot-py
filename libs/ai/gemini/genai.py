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

from typing import Optional, Union, List, Dict

from requests import Response

from ...utils import utf8_encode, json_encode, json_decode
from ...utils import Log, Logging
from ...utils import HttpClient
from ...chat import Request
from ...chat import ChatContext, ChatProcessor

from .queue import MessageQueue
from .client import GeminiChatBox


class GeminiHandler(ChatProcessor):

    def __init__(self, agent: str, auth_token: str):
        super().__init__(agent=agent)
        self.__api = GenerativeAI(auth_token=auth_token)

    # Override
    async def _query(self, prompt: str, request: Request, context: ChatContext) -> Optional[str]:
        assert isinstance(context, GeminiChatBox), 'chat context error: %s' % context
        message_queue = context.message_queue
        try:
            return await self.__api.ask(question=prompt, message_queue=message_queue)
        except Exception as error:
            self.error(msg='API error: %s, "%s"' % (error, prompt))


class GenerativeAI(Logging):
    """
        Google - Generative AI
        ~~~~~~~~~~~~~~~~~~~~~~

        https://ai.google.dev/tutorials/python_quickstart
    """

    BASE_URL = 'https://generativelanguage.googleapis.com'
    REFERER_URL = 'https://generativelanguage.googleapis.com/'

    def __init__(self, auth_token: str):
        super().__init__()
        self.__auth_token = auth_token
        self.__http_client = HttpClient(long_connection=True, base_url=self.BASE_URL)

    def http_post(self, url: str, data: Union[dict, bytes], headers: dict = None) -> Response:
        return self.__http_client.http_post(url=url, data=data, headers=headers)

    def build_message_info(self, question: str, message_queue: MessageQueue) -> Optional[Dict]:
        messages = message_queue.build_messages(prompt=question)
        count = len(messages)
        if count <= 0:
            self.error(msg='failed to build message')
            return None
        return {
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

    async def ask(self, question: str, message_queue: MessageQueue) -> Optional[str]:
        info = self.build_message_info(question=question, message_queue=message_queue)
        self.info(msg='sending message: %s' % info)
        if info is None:
            return None
        data = utf8_encode(string=json_encode(obj=info))
        # url = '/v1beta/models/gemini-pro:generateContent?key=%s' % self.__auth_token
        url = '/v1beta/models/gemini-1.5-flash:generateContent?key=%s' % self.__auth_token
        response = self.http_post(url=url, headers={
            'Content-Type': 'application/json',
            # 'Authorization': self.__auth_token,
            'Origin': self.REFERER_URL,
            'Referer': self.REFERER_URL,
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
            message_queue.push(msg=msg, trim=True)
            parts = msg.get('parts')
            if isinstance(parts, List):
                return get_text(parts=parts)
        self.error(msg='failed to parse content: %s' % info)


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
