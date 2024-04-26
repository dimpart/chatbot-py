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

from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Log
from libs.chat import ChatClient
from libs.client import ClientProcessor
from libs.client import Monitor

from libs.ai.gemini import GeminiChatClient


from bots.shared import GlobalVariable
from bots.shared import start_bot


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_chat_client(self) -> ChatClient:
        api_key = shared.config.get_string(section='gemini', option='google_api_key')
        client = GeminiChatClient(facebook=self.facebook, api_key=api_key)
        client.start()
        return client


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim_bots/config.ini'


shared = GlobalVariable()


if __name__ == '__main__':
    # start chat bot
    g_terminal = start_bot(default_config=DEFAULT_CONFIG,
                           app_name='ChatBot: Gemini',
                           ans_name='gege',
                           processor_class=BotMessageProcessor)
    g_monitor = Monitor()
    g_monitor.start()
