#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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
    Game Bot: 'Drift Bottle'
    ~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, Union, List, Dict

from dimples import ID
from dimples import ContentType
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import ReliableMessage
from dimples import Content, CustomizedContent, AppCustomizedContent
from dimples import ReceiptCommand
from dimples import CustomizedContentProcessor, CustomizedContentHandler
from dimples import TwinsHelper
from dimples.client import ClientContentProcessorCreator
from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client import ClientProcessor
from bots.shared import start_bot


class AppContentHandler(TwinsHelper, CustomizedContentHandler):
    """ Handler for App Customized Content """

    # Application ID for customized content
    APP_ID = 'chat.dim.sechat'

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        """ Override for customized actions """
        app = content.application
        mod = content.module
        return self._respond_receipt(text='Content not support.', msg=msg, group=content.group, extra={
            'template': 'Customized content (app: ${app}, mod: ${mod}, act: ${act}) not support yet!',
            'replacements': {
                'app': app,
                'mod': mod,
                'act': act,
            }
        })

    # noinspection PyMethodMayBeStatic
    def _respond_receipt(self, text: str, msg: ReliableMessage = None,
                         group: Optional[ID] = None, extra: Dict = None) -> List[Content]:
        res = ReceiptCommand.create(text=text, msg=msg)
        if group is not None:
            res.group = group
        if extra is not None:
            for key in extra:
                res[key] = extra[key]
        return [res]

    @classmethod
    def create(cls, mod: str, act: str) -> CustomizedContent:
        """ Create application customized content """
        msg_type = ContentType.APPLICATION
        return AppCustomizedContent(msg_type=msg_type, app=cls.APP_ID, mod=mod, act=act)


class DriftBottleHandler(AppContentHandler):
    """
        Drift Bottle Game
        ~~~~~~~~~~~~~~~~~
        Handler for customized content
    """

    # module name
    MOD_NAME = 'drift_bottle'

    # action names
    ACT_THROW = 'throw'
    ACT_CATCH = 'catch'

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        assert act is not None, 'action name empty: %s' % content
        if act == self.ACT_THROW:
            # action 'throw'
            return self.__throw(sender=sender, content=content, msg=msg)
        elif act == self.ACT_CATCH:
            # action 'catch'
            return self.__catch(sender=sender, content=content, msg=msg)
        # TODO: define your actions here
        # ...
        return super().handle_action(act=act, sender=sender, content=content, msg=msg)

    #
    #  Actions
    #

    def __throw(self, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        # TODO: handle customized action with message content
        pass

    def __catch(self, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        # TODO: handle customized action with message content
        pass


class AppContentProcessor(CustomizedContentProcessor):
    """
        Application Customized Content Processor
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Process customized contents for this application only
    """

    def __init__(self, facebook, messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Module(s) for customized contents
        self.__drift_bottle = DriftBottleHandler(facebook=facebook, messenger=messenger)

    @property
    def drift_bottle(self) -> CustomizedContentHandler:
        return self.__drift_bottle

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == AppContentHandler.APP_ID:
            # App ID match
            # return None to fetch module handler
            return None
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    def _fetch(self, mod: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[CustomizedContentHandler]:
        assert mod is not None, 'module name empty: %s' % content
        if mod == DriftBottleHandler.MOD_NAME:
            # customized module: "drift_bottle"
            return self.drift_bottle
        # TODO: define your modules here
        # ...
        return super()._fetch(mod=mod, content=content, msg=msg)


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # application customized
        if msg_type == ContentType.APPLICATION:
            return AppContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # elif msg_type == ContentType.CUSTOMIZED:
        #     return AppContentProcessor(facebook=self.facebook, messenger=self.messenger)
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


if __name__ == '__main__':
    start_bot(default_config=DEFAULT_CONFIG,
              app_name='Game: Drift Bottle',
              ans_name='bottle',
              processor_class=BotMessageProcessor)
