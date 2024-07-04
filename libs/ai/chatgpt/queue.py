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

import threading
from typing import Optional, List, Dict

from ...utils import json_encode
from ...chat import Setting


class MessageQueue:

    MAX_SIZE = 65536
    MAX_COUNT = 16

    def __init__(self, setting: Setting):
        super().__init__()
        self.__messages: List[Dict] = []
        self.__size = 0
        self.__setting = setting

    @property
    def system_setting(self) -> Optional[Dict]:
        setting = self.__setting
        if setting is None:
            return None
        else:
            text = setting.text
            if text is None or len(text) == 0:
                return None
        return {
            'content': text,
            'role': 'system',
        }

    def build_messages(self, prompt: str) -> List[Dict]:
        # 1. get all messages after appended
        self.push(msg={
            'content': prompt,
            'role': 'user',
        })
        messages = self.messages
        # 2. check system setting
        settings = self.system_setting
        if settings is not None:
            # messages = messages.copy()
            messages.insert(0, settings)
        # OK
        return messages

    @property
    def messages(self) -> List[Dict]:
        return self.__messages.copy()

    def push(self, msg: Dict, trim: bool = False):
        # simplify message data
        if trim:
            msg = self._trim(msg=msg)
        # check last message
        cnt = len(self.__messages)
        if cnt > 0 and self.__messages[cnt - 1] == msg:
            return False
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

    @classmethod
    def create(cls, setting: Setting):
        return LockedQueue(setting=setting)


class LockedQueue(MessageQueue):

    def __init__(self, setting: Setting):
        super().__init__(setting=setting)
        self.__lock = threading.Lock()

    @property  # Override
    def messages(self) -> List[dict]:
        with self.__lock:
            return super().messages

    # Override
    def push(self, msg: dict, trim: bool = False):
        with self.__lock:
            super().push(msg=msg, trim=trim)
