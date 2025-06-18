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

from libs.utils import Log, Runner
from libs.chat import ChatClient
from libs.client import ClientProcessor


from libs.ai.gemini import GeminiChatClient
from libs.ai.gemini import GeminiHandler


from bots.shared import GlobalVariable
from bots.shared import create_config, start_bot


class BotMessageProcessor(ClientProcessor):

    # Override
    def _create_chat_client(self) -> ChatClient:
        shared = GlobalVariable()
        api_key = shared.config.get_string(section='gemini', option='google_api_key')
        client = GeminiChatClient(facebook=self.facebook, config=shared.config)
        # TODO: add GPT handler(s)
        client.add_processor(processor=GeminiHandler(agent='API', auth_token=api_key))
        client.add_processor(processor=GeminiHandler(agent='BAK', auth_token=api_key))
        # Runner.async_task(coro=client.start())
        # Runner.thread_run(runner=client)
        thr = Runner.async_thread(coro=client.run())
        thr.start()
        return client


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/bots.ini'


async def async_main():
    # create global variable
    shared = GlobalVariable()
    config = await create_config(app_name='ChatBot: Gemini', default_config=DEFAULT_CONFIG)
    await shared.prepare(config=config)
    #
    #  Create & start the bot
    #
    client = await start_bot(ans_name='gege', section='gemini', processor_class=BotMessageProcessor)
    Log.warning(msg='bot stopped: %s' % client)


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
