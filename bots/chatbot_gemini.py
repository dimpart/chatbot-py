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
    Chat bot: 'Gemini'
    ~~~~~~~~~~~~~~~~~~

    Chat bot powered by Google AI
"""

from typing import Optional, Union, List

from dimples import DateTime
from dimples import EntityType, ID, Document
from dimples import ReliableMessage
from dimples import ContentType, Content, TextContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import CustomizedContent, CustomizedContentProcessor, CustomizedContentHandler
from dimples import BaseContentProcessor
from dimples import TwinsHelper
from dimples import CommonFacebook, CommonMessenger
from dimples import Anonymous
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import greeting_prompt
from libs.utils import Footprint
from libs.utils import Log, Logging

from libs.gemini import ChatCallback, ChatRequest
from libs.gemini import ChatStorage
from libs.gemini.googleapis import ChatClient

from libs.client import ClientProcessor, ClientContentProcessorCreator
from libs.client import Emitter

from bots.shared import start_bot


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
        if identifier.is_user:
            doc_type = Document.VISA
        elif identifier.is_group:
            doc_type = Document.BULLETIN
        else:
            doc_type = '*'
        # get name from document
        doc = self.facebook.document(identifier=identifier, doc_type=doc_type)
        if doc is not None:
            name = doc.name
            if name is not None and len(name) > 0:
                return name
        # get name from ID
        return Anonymous.get_name(identifier=identifier)

    def ask(self, question: str, sender: ID, group: Optional[ID], now: DateTime) -> bool:
        s_name = self.get_name(identifier=sender)
        g_name = None if group is None else self.get_name(identifier=group)
        # 1. update active time
        if now is None:
            now = DateTime.now()
        elif now < (DateTime.current_timestamp() - 600):
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
            naked = ChatCallback.replace_at(text=question, name=my_name)
            if naked == question:
                self.info(msg='ignore group message from %s (%s) in group: %s (%s)' % (sender, s_name, group, g_name))
                return False
            else:
                question = naked.strip()
        # 3. request with question text
        if len(question) == 0:
            self.warning(msg='drop empty question from %s (%s) in group: %s (%s)' % (sender, s_name, group, g_name))
            return False
        self.info(msg='[Dialog] Gemini <<< %s (%s): "%s"' % (sender, s_name, question))
        g_client.request(prompt=question, time=now, identifier=identifier, callback=self)
        return True

    # Override
    def chat_response(self, results: List, request: ChatRequest):
        emitter = Emitter()
        storage = ChatStorage()
        req_time = request.time
        identifier = request.identifier
        name = self.get_name(identifier=identifier)
        for answer in results:
            self.info(msg='[Dialog] Gemini >>> %s (%s): "%s"' % (identifier, name, answer))
            if answer == ChatCallback.NOT_FOUND and request.is_greeting:
                self.warning(msg='ignore 404 for greeting: %s "%s"' % (identifier, name))
                continue
            # respond text message
            content = TextContent.create(text=answer)
            res_time = content.time
            if res_time is None or res_time <= req_time:
                self.warning(msg='replace respond time: %s => %s + 1' % (res_time, req_time))
                content['time'] = req_time + 1
            emitter.send_content(content=content, receiver=identifier)
            # save chat history
            storage.save_response(question=request.prompt, answer=answer, identifier=identifier, name=name)


class ActiveUsersHandler(ChatHelper, CustomizedContentHandler):

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        users = content.get('users')
        self.info(msg='received users: %s' % users)
        if isinstance(users, List):
            self.__say_hi(users=users, when=content.time)
        else:
            self.error(msg='content error: %s, sender: %s' % (content, sender))
        return []

    def __say_hi(self, users: List[dict], when: Optional[DateTime]):
        if when is None:
            when = DateTime.now()
        elif when < (DateTime.current_timestamp() - 300):
            self.warning(msg='users timeout %s: %s' % (when, users))
            return False
        fp = Footprint()
        facebook = self.facebook
        for item in users:
            identifier = ID.parse(identifier=item.get('U'))
            if identifier is None or identifier.type != EntityType.USER:
                self.warning(msg='ignore user: %s' % item)
                continue
            elif not fp.is_vanished(identifier=identifier, now=when):
                self.info(msg='footprint not vanished yet: %s' % identifier)
                continue
            hello = greeting_prompt(identifier=identifier, facebook=facebook)
            if self.ask(question=hello, sender=identifier, group=None, now=when):
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


# start google gemini
g_client = ChatClient()
g_client.start()

if __name__ == '__main__':
    # start chat bot
    g_terminal = start_bot(default_config=DEFAULT_CONFIG,
                           app_name='ChatBot: Gemini',
                           ans_name='gege',
                           processor_class=BotMessageProcessor)
