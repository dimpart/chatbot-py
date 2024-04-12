# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from dimples import ID
from dimples import Content, TextContent
from dimples import CommonFacebook

from ...utils import json_encode
from ...chat.base import get_nickname
from ...chat import Request, Setting
from ...chat import ChatBox, ChatClient
from ...client import Emitter


class MessageQueue:

    MAX_SIZE = 10240
    MAX_COUNT = 8

    def __init__(self):
        super().__init__()
        self.__messages = []
        self.__size = 0

    @property
    def messages(self) -> List[Dict]:
        return self.__messages

    def push(self, msg: Dict, trim: bool = False):
        # simplify message data
        if trim:
            msg = self._trim(msg=msg)
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
    def _trim(self, msg: Dict) -> Dict:
        return {
            'content': msg.get('content'),
            'role': msg.get('role'),
        }


class GPTHandler(ABC):

    # Override
    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>\n    API: "%s%s"\n</%s module="%s">' % (cname, self.base_url, self.api_path, cname, mod)

    # Override
    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>\n    API: "%s%s"\n</%s module="%s">' % (cname, self.base_url, self.api_path, cname, mod)

    @property
    @abstractmethod
    def base_url(self) -> str:
        """ API base """
        raise NotImplemented

    @property
    @abstractmethod
    def api_path(self) -> str:
        """ API path """
        raise NotImplemented

    @abstractmethod
    def query(self, messages: List[Dict]) -> Optional[Dict]:
        """ Build query data and post to remote server
            return message item with content text
        """
        raise NotImplemented


class GPTChatBox(ChatBox):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook, setting: Setting, handlers: List[GPTHandler]):
        super().__init__(identifier=identifier, facebook=facebook)
        self.__setting = setting
        self.__handlers = handlers
        self.__message_queue = MessageQueue()

    @property
    def system_setting(self) -> Optional[Dict]:
        text = self.__setting.text
        if text is None or len(text) == 0:
            return None
        return {
            'content': text,
            'role': 'system',
        }

    def _append_message(self, msg: Dict):
        self.__message_queue.push(msg=msg, trim=True)

    def _build_messages(self, prompt: str) -> List[Dict]:
        # 1. get all messages after appended
        self.__message_queue.push(msg={
            'content': prompt,
            'role': 'user',
        })
        messages = self.__message_queue.messages
        # 2. check system setting
        settings = self.system_setting
        if settings is not None:
            # 3. insert system setting in the front
            messages = messages.copy()
            messages.insert(0, settings)
        # OK
        return messages

    def _query(self, prompt: str) -> Optional[str]:
        """ query by handler """
        messages = self._build_messages(prompt=prompt)
        index = 0
        for handler in self.__handlers:
            # try to query by each handler
            msg = handler.query(messages=messages)
            if msg is None:
                self.error(msg='failed to query handler: %s' % handler)
                index += 1
                continue
            answer = msg.get('content')
            if answer is None or len(answer) == 0:
                self.error(msg='response error from handler: %s' % handler)
                index += 1
                continue
            # append responded message item
            self._append_message(msg=msg)
            if index > 0:
                # move this handler to the front
                self.warning(msg='move handler position: %d, %s' % (index, handler))
                self.__handlers.pop(index)
                self.__handlers.insert(0, handler)
            # OK
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
        identifier = request.identifier
        name = get_nickname(identifier=identifier, facebook=self.facebook)
        self.info(msg='<<< received prompt from "%s": "%s"' % (name, prompt))
        answer = self._query(prompt=prompt)
        self.info(msg='>>> responding answer to "%s": "%s"' % (name, answer))
        if answer is None:
            answer = self.NOT_FOUND
        elif len(answer) == 0:
            answer = self.NO_CONTENT
        self.respond_text(text=answer, request=request)
        self._save_response(prompt=prompt, text=answer, request=request)
        return True

    # Override
    def _send_content(self, content: Content, receiver: ID) -> bool:
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)
        return True


class GPTChatClient(ChatClient):

    SYSTEM_SETTING = 'Your name is "Gigi", a smart and beautiful girl.' \
                     ' You are set as a little assistant who is good at listening' \
                     ' and willing to answer any questions.'

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook
        self.__system_setting = Setting(definition=self.SYSTEM_SETTING)
        self.__handlers: List[GPTHandler] = []

    def add_handler(self, handler: GPTHandler):
        self.__handlers.append(handler)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        setting = self.__system_setting
        handlers = self.__handlers.copy()
        return GPTChatBox(identifier=identifier, facebook=facebook, setting=setting, handlers=handlers)
