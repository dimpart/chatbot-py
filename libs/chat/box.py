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
from typing import Optional, Set, List

from mkm.types import DateTime
from dimples import ID
from dimples import Content, TextContent
from dimples import FileContent, ImageContent, AudioContent, VideoContent

from dimples.utils import Runner, Logging

from .base import Request
from .base import Setting, Greeting, ChatRequest


class ChatBox(ABC):

    EXPIRES = 36000  # seconds

    def __init__(self, identifier: ID, setting: Setting = None):
        super().__init__()
        self.__identifier = identifier
        self.__setting = setting
        self.__expired = DateTime.current_timestamp() + self.EXPIRES

    @property
    def identifier(self) -> ID:
        """ Conversation ID """
        return self.__identifier

    @property
    def setting(self) -> Optional[Setting]:
        """ System setting """
        return self.__setting

    def is_expired(self, now: DateTime) -> bool:
        return now > self.__expired

    # Override
    def __hash__(self) -> int:
        """ Return hash(self). """
        return self.__identifier.__hash__()

    # Override
    def __eq__(self, x: str) -> bool:
        """ Return self==value. """
        if isinstance(x, ChatBox):
            if self is x:
                # same object
                return True
            x = x.identifier
        # check inner string
        return self.__identifier.__eq__(x)

    # Override
    def __ne__(self, x: str) -> bool:
        """ Return self!=value. """
        if isinstance(x, ChatBox):
            if self is x:
                # same object
                return False
            x = x.identifier
        # check inner string
        return self.__identifier.__ne__(x)

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" />' % (cname, self.identifier)

    # Override
    def __repr__(self) -> str:
        cname = self.__class__.__name__
        return '<%s identifier="%s" />' % (cname, self.identifier)

    #
    #   Request
    #

    def process_request(self, request: Request) -> bool:
        # greeting
        if isinstance(request, Greeting):
            text = request.text
            if text is None or len(text) == 0:
                return False
            return self._say_hi(prompt=text, request=request)
        # chatting
        assert isinstance(request, ChatRequest), 'unknown request: %s' % request
        content = request.content
        if isinstance(content, TextContent):
            return self._process_text_content(content=content, request=request)
        elif isinstance(content, FileContent):
            return self._process_file_content(content=content, request=request)
        # else:
        #     assert False, 'unsupported content: %s, envelope: %s' % (content, request.envelope)

    def _process_text_content(self, content: TextContent, request: ChatRequest) -> bool:
        # text message
        text = request.text
        if text is None or len(text) == 0:
            return False
        return self._ask_question(prompt=text, content=content, request=request)

    def _process_file_content(self, content: FileContent, request: ChatRequest) -> bool:
        # file message
        if isinstance(content, ImageContent):
            # image message
            return self._process_image_content(content=content, request=request)
        elif isinstance(content, AudioContent):
            # audio message
            return self._process_audio_content(content=content, request=request)
        elif isinstance(content, VideoContent):
            # video message
            return self._process_video_content(content=content, request=request)
        # else:
        #     assert False, 'unsupported file content: %s, envelope: %s' % (content, request.envelope)

    def _process_image_content(self, content: ImageContent, request: ChatRequest) -> bool:
        """ Process image message """
        pass

    def _process_audio_content(self, content: AudioContent, request: ChatRequest) -> bool:
        """ Process audio message """
        pass

    def _process_video_content(self, content: VideoContent, request: ChatRequest) -> bool:
        """ Process video message """
        pass

    def _say_hi(self, prompt: str, request: Request) -> bool:
        """ Build greeting message & query the server """
        pass

    @abstractmethod
    def _ask_question(self, prompt: str, content: TextContent, request: Request) -> bool:
        """ Build message(s) & query the server """
        raise NotImplemented

    #
    #   Respond
    #

    def respond_text(self, text: str, request: Request):
        content = TextContent.create(text=text)
        calibrate_time(content=content, request=request)
        return self.respond(responses=[content], request=request)

    def respond(self, responses: List[Content], request: Request):
        # all content time in responses must be calibrated with the request time
        receiver = request.identifier
        for res in responses:
            self._send_content(content=res, receiver=receiver)

    @abstractmethod
    def _send_content(self, content: Content, receiver: ID):
        """ Send message to DIM station """
        raise NotImplemented


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
    def process(self) -> bool:
        request = self._next()
        if request is not None:
            box = self._get_box(identifier=request.identifier)
            if box is not None:
                # try to process the request
                try:
                    box.process_request(request=request)
                except Exception as error:
                    self.error(msg='failed to process request: %s, error: %s' % (request, error))
                    return False
            # else:
            #     assert False, 'failed to get chat box, drop request: %s' % request
            return True
        # nothing to do now
        self._purge()
        return False

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()


def calibrate_time(content: Content, request: Request, period: float = 1.0):
    res_time = content.time
    req_time = request.time
    if req_time is None:
        assert False, 'request error: %s' % req_time
    elif res_time is None or res_time <= req_time:
        content['time'] = req_time + period
