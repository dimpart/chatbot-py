#! /usr/bin/env python3
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

"""
    Chat bot: 'GPT-3.5'
    ~~~~~~~~~~~~~~~~~~~

    Chat bot powered by OpenAI
"""

import random
import time
from typing import Optional, Union, List

from dimples import EntityType, ID
from dimples import ReliableMessage
from dimples import ContentType, Content, TextContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import CustomizedContent, CustomizedContentProcessor
from dimples import BaseContentProcessor
from dimples import CommonFacebook
from dimples.utils import Log, Logging
from dimples.utils import Path

from libs.chat_gpt.client import ChatRequest

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.chat_gpt import ChatClient, ChatCallback
from libs.client import ClientMessenger
from libs.client import ClientProcessor, ClientContentProcessorCreator

from bots.shared import GlobalVariable
from bots.shared import start_bot


class GPTHandler(ChatCallback, Logging):

    EXPIRES = 36000  # say hi after 10 hours

    def __init__(self):
        super().__init__()
        self.__active_times = {}  # ID => float

    @property
    def facebook(self) -> CommonFacebook:
        shared = GlobalVariable()
        return shared.facebook

    @property
    def messenger(self) -> ClientMessenger:
        return g_terminal.messenger

    @property
    def hi_text(self) -> str:
        return random.choice(['Hello!', 'Hi!'])

    def get_name(self, identifier: ID) -> str:
        doc = self.facebook.document(identifier=identifier)
        name = None if doc is None else doc.name
        return str(identifier) if name is None else '%s (%s)' % (identifier, name)

    def __touch(self, identifier: ID, now: float = None):
        if now is None:
            now = time.time()
        else:
            last_time = self.__active_times.get(identifier)
            if last_time is not None and last_time >= now:
                return False
        self.__active_times[identifier] = now
        return True

    def __is_expired(self, identifier: ID, now: float = None):
        last_time = self.__active_times.get(identifier)
        if last_time is None:
            return True
        if now is None:
            now = time.time()
        return last_time < (now - self.EXPIRES)

    def say_hi(self, identifier: ID, now: float = None) -> bool:
        if now is None:
            now = time.time()
        if self.__is_expired(identifier=identifier, now=now):
            # update active time
            self.__touch(identifier=identifier, now=now)
            # request to say hi
            text = self.hi_text
            name = self.get_name(identifier=identifier)
            self.info(msg='[Dialog] ChatGPT <<< %s: say hi' % name)
            g_client.request(question=text, identifier=identifier, callback=self)
            return True

    def ask(self, question: str, sender: ID, group: Optional[ID], now: float = None):
        # update active time
        if now is None:
            now = time.time()
        self.__touch(identifier=sender, now=now)
        # request for question
        text = question.strip()
        if len(text) > 0:
            name = self.get_name(identifier=sender)
            self.info(msg='[Dialog] ChatGPT <<< %s: "%s"' % (name, text))
            identifier = sender if group is None else group
            g_client.request(question=text, identifier=identifier, callback=self)

    # Override
    def chat_response(self, answer: str, request: ChatRequest):
        identifier = request.identifier
        name = self.get_name(identifier=identifier)
        self.info(msg='[Dialog] ChatGPT >>> %s: "%s"' % (name, answer))
        content = TextContent.create(text=answer)
        self.messenger.send_content(sender=None, receiver=identifier, content=content)


class BotTextContentProcessor(BaseContentProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        when = content.time
        if when is None or when > (time.time() - 300):
            g_handler.ask(question=content.text, sender=msg.sender, group=content.group, now=when)
        else:
            self.warning(msg='drop expired message from %s: %s' % (msg.sender, content))
        # text = 'Text message received'
        # group = content.group
        # return self._respond_receipt(text=text, msg=msg, group=group)
        return []


class BotCustomizedContentProcessor(CustomizedContentProcessor, Logging):
    """ Process customized stat content """

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'stat content error: %s' % content
        app = content.application
        mod = content.module
        act = content.action
        sender = msg.sender
        self.debug(msg='received content from %s: %s, %s, %s' % (sender, app, mod, act))
        return super().process(content=content, msg=msg)

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == 'chat.dim.monitor':
            # app ID matched
            return None
        # unknown app ID
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        mod = content.module
        if mod == 'users':
            users = content.get('users')
            self.info(msg='received users: %s' % users)
            when = content.time
            if when is None or when > (time.time() - 300):
                if isinstance(users, List):
                    self.__say_hi(users=users, when=when)
                else:
                    self.error(msg='content error: %s, sender: %s' % (content, sender))
            else:
                self.warning(msg='drop expired message from %s: %s' % (msg.sender, content))
        else:
            self.error(msg='unknown module: %s, action: %s, content: %s' % (mod, act, content))
        # respond nothing
        return []

    def __say_hi(self, users: List[dict], when: Optional[float]):
        if when is None:
            when = time.time()
        for item in users:
            identifier = ID.parse(identifier=item.get('U'))
            if identifier is None or identifier.type != EntityType.USER:
                self.warning(msg='ignore user: %s' % item)
                continue
            if g_handler.say_hi(identifier=identifier, now=when):
                self.info(msg='say hi for %s' % identifier)


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return BotTextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # application customized
        if msg_type == ContentType.CUSTOMIZED:
            return BotCustomizedContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim_bots/config.ini'


# chat gpt handler
g_handler = GPTHandler()

# start chat gpt
g_client = ChatClient()
g_client.start()

if __name__ == '__main__':
    # start chat bot
    g_terminal = start_bot(default_config=DEFAULT_CONFIG,
                           app_name='ChatBot: GPT',
                           ans_name='chat_gpt',
                           processor_class=BotMessageProcessor)
