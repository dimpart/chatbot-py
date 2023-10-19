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
from dimples import CustomizedContent, CustomizedContentProcessor, CustomizedContentHandler
from dimples import BaseContentProcessor
from dimples import TwinsHelper
from dimples import CommonFacebook, CommonMessenger
from dimples import Anonymous
from dimples.utils import Singleton
from dimples.utils import Log, Logging
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.chatgpt.fakeopen import ChatClient
from libs.chatgpt import ChatCallback, ChatRequest
from libs.client import ClientProcessor, ClientContentProcessorCreator

from bots.shared import start_bot


@Singleton
class Footprint:

    EXPIRES = 36000  # vanished after 10 hours

    def __init__(self):
        super().__init__()
        self.__active_times = {}  # ID => float

    def __get_time(self, identifier: ID, when: Optional[float]) -> Optional[float]:
        now = time.time()
        if when is None or when <= 0 or when >= now:
            return now
        elif when > self.__active_times.get(identifier, 0):
            return when
        # else:
        #     # time expired, drop it
        #     return None

    def touch(self, identifier: ID, when: float = None):
        when = self.__get_time(identifier=identifier, when=when)
        if when is not None:
            self.__active_times[identifier] = when
            return True

    def is_vanished(self, identifier: ID, now: float = None) -> bool:
        last_time = self.__active_times.get(identifier)
        if last_time is None:
            return True
        if now is None:
            now = time.time()
        return now > (last_time + self.EXPIRES)


def replace_at(text: str, name: str) -> str:
    at = '@%s' % name
    if text.endswith(at):
        text = text[:-len(at)]
    at = '@%s ' % name
    return text.replace(at, '')


class ChatHelper(TwinsHelper, ChatCallback, Logging):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def my_name(self) -> Optional[str]:
        current = self.facebook.current_user
        if current is not None:
            return self.get_name(identifier=current.identifier)

    def get_name(self, identifier: ID) -> Optional[str]:
        doc = self.facebook.document(identifier=identifier)
        if doc is None:
            # document not found, query from station
            self.messenger.query_document(identifier=identifier)
            return identifier.name
        name = doc.name
        if name is not None and len(name) > 0:
            return name
        return Anonymous.get_name(identifier=identifier)

    def ask(self, question: str, sender: ID, group: Optional[ID], now: float = None) -> bool:
        s_name = self.get_name(identifier=sender)
        g_name = None if group is None else self.get_name(identifier=group)
        # 1. update active time
        if now is None:
            now = time.time()
        elif now < (time.time() - 600):
            self.warning(msg='question timeout from %s (%s): %s' % (sender, s_name, question))
            return False
        fp = Footprint()
        fp.touch(identifier=sender, when=now)
        # 2. check for group message
        if group is None:
            identifier = sender
        else:
            identifier = group
            # received group message, check '@xxx' for message to this bot
            my_name = self.my_name
            if my_name is None or len(my_name) == 0:
                self.error(msg='failed to get the bot name')
                return False
            naked = replace_at(text=question, name=my_name)
            if len(naked) == question:
                self.debug(msg='ignore group message from %s (%s) in group: %s (%s)' % (sender, s_name, group, g_name))
                return False
            else:
                question = naked.strip()
        # 3. request with question text
        if len(question) == 0:
            self.warning(msg='drop empty question from %s (%s) in group: %s (%s)' % (sender, s_name, group, g_name))
            return False
        self.info(msg='[Dialog] ChatGPT <<< %s (%s): "%s"' % (sender, s_name, question))
        g_client.request(question=question, identifier=identifier, callback=self)
        return True

    # Override
    def chat_response(self, answer: str, request: ChatRequest):
        identifier = request.identifier
        name = self.get_name(identifier=identifier)
        self.info(msg='[Dialog] ChatGPT >>> %s (%s): "%s"' % (identifier, name, answer))
        content = TextContent.create(text=answer)
        self.messenger.send_content(sender=None, receiver=identifier, content=content)


class ActiveUsersHandler(ChatHelper, CustomizedContentHandler):

    @property
    def hi_text(self) -> str:
        return random.choice(['Hello!', 'Hi!'])

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        users = content.get('users')
        self.info(msg='received users: %s' % users)
        if isinstance(users, List):
            self.__say_hi(users=users, when=content.time)
        else:
            self.error(msg='content error: %s, sender: %s' % (content, sender))
        return []

    def __say_hi(self, users: List[dict], when: Optional[float]):
        if when is None:
            when = time.time()
        elif when < (time.time() - 300):
            self.warning(msg='users timeout %f: %s' % (when, users))
            return False
        fp = Footprint()
        for item in users:
            identifier = ID.parse(identifier=item.get('U'))
            if identifier is None or identifier.type != EntityType.USER:
                self.warning(msg='ignore user: %s' % item)
            elif not fp.is_vanished(identifier=identifier, now=when):
                self.info(msg='footprint not vanished yet: %s' % identifier)
            elif self.ask(question=self.hi_text, sender=identifier, group=None, now=when):
                self.info(msg='say hi for %s' % identifier)


class BotTextContentProcessor(BaseContentProcessor, Logging):
    """ Process text content """

    def __init__(self, facebook, messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Module(s) for customized contents
        self.__helper = ChatHelper(facebook=facebook, messenger=messenger)

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        sender = r_msg.sender
        group = content.group
        text = content.text.strip()
        if sender.type != EntityType.USER:
            self.debug(msg='ignore message from %s, group: %s' % (sender, group))
        elif len(text) == 0:
            self.warning(msg='empty text content from %s, group: %s' % (sender, group))
        else:
            self.__helper.ask(question=text, sender=sender, group=group, now=content.time)
        # text = 'Text message received'
        # group = content.group
        # return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope)
        return []


class BotCustomizedContentProcessor(CustomizedContentProcessor, Logging):
    """ Process customized content """

    def __init__(self, facebook, messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Module(s) for customized contents
        self.__handler = ActiveUsersHandler(facebook=facebook, messenger=messenger)

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == 'chat.dim.monitor':
            # App ID match
            # return None to fetch module handler
            return None
        # unknown app ID
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    def _fetch(self, mod: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[CustomizedContentHandler]:
        assert mod is not None, 'module name empty: %s' % content
        if mod == 'users':
            # customized module: "users"
            return self.__handler
        # TODO: define your modules here
        # ...
        return super()._fetch(mod=mod, content=content, msg=msg)


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


# start chat gpt
g_client = ChatClient()
g_client.start()

if __name__ == '__main__':
    # start chat bot
    g_terminal = start_bot(default_config=DEFAULT_CONFIG,
                           app_name='ChatBot: GPT',
                           ans_name='gigi',
                           processor_class=BotMessageProcessor)
