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

import os
import time
from typing import Optional

from dimples import DateTime
from dimples import ID
from dimples.database import Storage

from ..utils import json_encode
from ..utils import Logging
from ..utils import Singleton


@Singleton
class ChatStorage(Logging):

    def __init__(self):
        super().__init__()
        self.__root = None  # '/var/dim/protected'
        self.__user = None

    @property
    def root(self) -> Optional[str]:
        return self.__root

    @root.setter
    def root(self, path: str):
        self.__root = path

    @property
    def bot(self) -> Optional[ID]:
        return self.__user

    @bot.setter
    def bot(self, identifier: ID):
        self.__user = identifier

    def get_path(self, now: DateTime) -> Optional[str]:
        """ get current save path """
        root = self.root
        user = self.bot
        if root is None or user is None:
            self.debug(msg='chat history not config')
            return None
        filename = 'chat-%s.txt' % time.strftime('%Y-%m-%d', now.localtime)
        return os.path.join(root, str(user), filename)

    async def save_response(self, question: str, answer: str, identifier: ID, name: str) -> bool:
        now = DateTime.now()
        path = self.get_path(now=now)
        if path is None:
            self.info(msg='cannot get storage path for chat response')
            return False
        info = {
            'ID': str(identifier),
            'name': name,
            'time': str(now),
            'prompt': question,
            'result': answer,
        }
        text = '%s,\n' % json_encode(info)
        self.info(msg='saving response for %s into %s' % (identifier, path))
        return await Storage.append_text(text=text, path=path)
