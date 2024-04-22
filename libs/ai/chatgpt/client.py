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

import random
from typing import Optional, Tuple, List, Dict

from dimples import ID
from dimples import Content, TextContent
from dimples import CommonFacebook

from ...chat.base import get_nickname
from ...chat import Request, Setting
from ...chat import ChatBox, ChatClient
from ...client import Emitter
from ...client import Monitor

from .handler import MessageQueue
from .handler import GPTHandler


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

    def _query(self, prompt: str, identifier: ID) -> Tuple[Optional[str], Optional[GPTHandler]]:
        """ query by handler """
        all_handlers = self.__handlers
        if len(all_handlers) == 0:
            self.error(msg='gpt handlers not set')
            return 'GPT handler not set', None
        monitor = Monitor()
        service = 'ChatGPT'
        messages = self._build_messages(prompt=prompt)
        index = 0
        for handler in all_handlers:
            # try to query by each handler
            try:
                msg = handler.query(messages=messages, identifier=identifier)
            except Exception as error:
                self.error(msg='failed to query handler: %s, error: %s' % (handler, error))
                msg = None
            if msg is None:
                self.error(msg='failed to query handler: %s' % handler)
                index += 1
                monitor.report_failure(service=service, agent=handler.agent)
                continue
            answer = msg.get('content')
            if answer is None or len(answer) == 0:
                self.error(msg='response error from handler: %s' % handler)
                index += 1
                monitor.report_failure(service=service, agent=handler.agent)
                continue
            else:
                monitor.report_success(service=service, agent=handler.agent)
            # got an answer
            if index > 0:
                # move this handler to the front
                self.warning(msg='move handler position: %d, %s' % (index, handler))
                self.__handlers.pop(index)
                self.__handlers.insert(0, handler)
            # OK, append responded message item
            self._append_message(msg=msg)
            return answer, handler
        # failed to get answer
        monitor.report_crash(service=service)
        return None, None

    # Override
    def _say_hi(self, prompt: str, request: Request) -> bool:
        identifier = request.identifier
        answer, handler = self._query(prompt=prompt, identifier=identifier)
        if answer is not None and len(answer) > 0:
            self.respond_text(text=answer, request=request)
        # save response with handler
        if handler is None:
            text = answer
        else:
            text = '[%s] %s' % (handler.agent, answer)
        self._save_response(prompt=prompt, text=text, request=request)
        return True

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request) -> bool:
        identifier = request.identifier
        name = get_nickname(identifier=identifier, facebook=self.facebook)
        self.info(msg='<<< received prompt from "%s": "%s"' % (name, prompt))
        answer, handler = self._query(prompt=prompt, identifier=identifier)
        self.info(msg='>>> responding answer to "%s": "%s"' % (name, answer))
        if answer is None:
            answer = self.NOT_FOUND
        elif len(answer) == 0:
            answer = self.NO_CONTENT
        self.respond_text(text=answer, request=request)
        # save response with handler
        if handler is None:
            text = answer
        else:
            text = '[%s] %s' % (handler.agent, answer)
        self._save_response(prompt=prompt, text=text, request=request)
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
        # copy handlers in random order
        handlers = self.__handlers.copy()
        count = len(handlers)
        if count > 1:
            handlers = random.sample(handlers, count)
        return GPTChatBox(identifier=identifier, facebook=facebook, setting=setting, handlers=handlers)
