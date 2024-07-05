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
import weakref
from abc import ABC, abstractmethod
from typing import Optional, Set

from dimples import DateTime
from dimples import ID

from ..utils import Logging
from ..utils import Runner

from .base import Request
from .box import ChatBox


class ChatClient(Runner, Logging, ABC):
    """ Chat Boxes Pool """

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__lock = threading.Lock()
        self.__requests = []
        # boxes pool
        self.__map = weakref.WeakValueDictionary()  # ID => ChatBox
        self.__boxes: Set[ChatBox] = set()          # Set[ChatBox]
        self.__next_purge_time = 0

    def append(self, request: Request):
        """ Add request """
        with self.__lock:
            self.__requests.append(request)

    def _next(self) -> Optional[Request]:
        """ Pop request """
        with self.__lock:
            if len(self.__requests) > 0:
                return self.__requests.pop(0)

    #
    #   Boxes Pool
    #

    @abstractmethod
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        """ create chat box """
        raise NotImplemented

    def _get_box(self, identifier: ID) -> Optional[ChatBox]:
        with self.__lock:
            box = self.__map.get(identifier)
            if box is None:
                box = self._new_box(identifier=identifier)
                if box is not None:
                    self.__map[identifier] = box
                    self.__boxes.add(box)
            return box

    def _purge(self) -> int:
        now = DateTime.now()
        if now < self.__next_purge_time:
            return 0
        else:
            self.__next_purge_time = now + 60
        # remove expired box(es)
        count = 0
        with self.__lock:
            boxes = self.__boxes.copy()
            for box in boxes:
                if box.is_expired(now=now):
                    self.__boxes.discard(box)
                    count += 1
        return count

    # Override
    async def process(self) -> bool:
        request = self._next()
        if request is not None:
            text = await request.build()
            if text is None:
                self.warning(msg='ignore this request: %s' % request)
                return True
            box = self._get_box(identifier=request.identifier)
            if box is not None:
                # try to process the request
                try:
                    await box.process_request(request=request)
                except Exception as error:
                    self.error(msg='failed to process request: %s, error: %s' % (request, error))
                    return False
            # else:
            #     assert False, 'failed to get chat box, drop request: %s' % request
            return True
        # nothing to do now
        self._purge()
        return False
