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

from typing import Optional, Union, List, Dict

from dimples import DateTime
from dimples import PlainKey
from dimples import EntityType, ID
from dimples import ReliableMessage
from dimples import ContentType, Content, TextContent, FileContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseContentProcessor
from dimples import TwinsHelper
from dimples import CommonFacebook, CommonMessenger
from dimples import Anonymous
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import filename_from_url
from libs.utils import Footprint
from libs.utils import Log, Logging

from libs.chatgpt import ChatCallback, ChatRequest

from libs.stable_diffusion.tensor_art import DrawClient

from libs.client import ClientProcessor, ClientContentProcessorCreator
from libs.client import Emitter

from bots.shared import start_bot


class DrawHelper(TwinsHelper, ChatCallback, Logging):

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

    def ask(self, question: str, sender: ID, group: Optional[ID], now: DateTime) -> bool:
        s_name = self.get_name(identifier=sender)
        g_name = None if group is None else self.get_name(identifier=group)
        # 1. update active time
        if now is None:
            now = DateTime.now()
        elif now < (DateTime.now() - 600):
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
        self.info(msg='[Dialog] SD <<< %s : "%s"' % (identifier, question))
        g_painter.request(prompt=question, time=now, identifier=identifier, callback=self)
        return True

    # Override
    def chat_response(self, results: List, request: ChatRequest):
        emitter = Emitter()
        req_time = request.time
        identifier = request.identifier
        name = self.get_name(identifier=identifier)
        for item in results:
            if isinstance(item, str):
                self.info(msg='[Dialog] SD >>> %s (%s): "%s"' % (identifier, name, item))
                # respond text message
                content = TextContent.create(text=item)
                order = 2  # ordered responses
            elif isinstance(item, Dict):
                url = item.get('url')
                if url is None:
                    self.error(msg='response error: %s' % item)
                    continue
                filename = filename_from_url(url=url, filename=None)
                if filename is None or len(filename) == 0:
                    filename = 'image.png'
                content = FileContent.image(filename=filename, url=url, password=PlainKey())
                order = 1  # ordered responses
            else:
                self.error(msg='response error: %s' % item)
                continue
            res_time = content.time
            if res_time is None or res_time <= req_time:
                self.warning(msg='replace respond time: %s => %s + 1' % (res_time, req_time))
                content['time'] = req_time + order
            else:
                content['time'] = res_time + order
            self.info(msg='responding: %s, %s' % (identifier, content))
            emitter.send_content(content=content, receiver=identifier)


class BotTextContentProcessor(BaseContentProcessor, Logging):
    """ Process text content """

    def __init__(self, facebook, messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Module(s) for customized contents
        self.__helper = DrawHelper(facebook=facebook, messenger=messenger)

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


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return BotTextContentProcessor(facebook=self.facebook, messenger=self.messenger)
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


# start draw bot
g_painter = DrawClient()
g_painter.start()

if __name__ == '__main__':
    # start chat bot
    g_terminal = start_bot(default_config=DEFAULT_CONFIG,
                           app_name='ChatBot: GPT',
                           ans_name='simon',
                           processor_class=BotMessageProcessor)
