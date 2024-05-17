#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Chat bot: 'LingLing'
    ~~~~~~~~~~~~~~~~~~~~

    Chat bot powered by Tuling
"""

from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Log, Runner
from libs.chat import ChatClient
from libs.client import ClientProcessor

from libs.ai.nlp import NLPChatClient

from bots.shared import GlobalVariable
from bots.shared import chat_bots
from bots.shared import start_bot


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_chat_client(self) -> ChatClient:
        shared = GlobalVariable()
        bots = chat_bots(names=['tuling'], shared=shared)  # chat bot
        client = NLPChatClient(bots=bots, facebook=self.facebook)
        # Runner.async_run(coroutine=client.start())
        Runner.thread_run(runner=client)
        return client


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim_bots/config.ini'


async def main():
    # create & start bot
    client = await start_bot(default_config=DEFAULT_CONFIG,
                             app_name='ChatBot: Tuling',
                             ans_name='ling',
                             processor_class=BotMessageProcessor)
    # main run loop
    await client.start()
    await client.run()
    # await client.stop()
    Log.warning(msg='bot stopped: %s' % client)


if __name__ == '__main__':
    Runner.sync_run(main=main())
