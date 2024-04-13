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

from ...utils import json_encode


class MessageQueue:

    MAX_SIZE = 65536
    MAX_COUNT = 16

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
