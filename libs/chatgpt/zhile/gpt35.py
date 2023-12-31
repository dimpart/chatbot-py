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

from typing import Optional, List

from ...utils import hex_encode, utf8_encode, json_encode, json_decode
from ...utils import random_bytes
from ...utils import Log
from ...utils import HttpClient, HttpSession, show_response


def random_hex(size: int) -> str:
    data = random_bytes(size)
    return hex_encode(data=data)


def new_msg_id() -> str:
    a = random_hex(size=4)
    b = random_hex(size=2)
    c = random_hex(size=2)
    d = random_hex(size=2)
    e = random_hex(size=6)
    return '%s-%s-%s-%s-%s' % (a, b, c, d, e)


class MessageQueue:

    MAX_SIZE = 10240
    MAX_COUNT = 8

    def __init__(self):
        super().__init__()
        self.__messages = []
        self.__size = 0

    @property
    def messages(self) -> List[dict]:
        return self.__messages

    def push(self, msg: dict, trim: bool = False):
        # simplify message data
        if trim:
            msg = self.__trim(msg=msg)
        # append to tail
        self.__messages.append(msg)
        self.__size += len(json_encode(obj=msg))
        # check data size of the queue
        while self.__size > self.MAX_SIZE:
            if len(self.__messages) < self.MAX_COUNT:
                break
            first = self.__messages.pop(0)
            self.__size -= len(json_encode(obj=first))

    # noinspection PyMethodMayBeStatic
    def __trim(self, msg: dict) -> dict:
        mid = msg.get('id')
        author = msg.get('author')
        role = None if author is None else author.get('role')
        content = msg.get('content')
        c_type = None if content is None else content.get('content_type')
        parts = None if content is None else content.get('parts')
        return {
            'id': mid,
            'author': {
                'role': role,
            },
            'content': {
                'content_type': c_type,
                'parts': parts,
            }

        }


class SharedGPT(HttpClient):
    """
        Shared GPT
        ~~~~~~~~~~

        https://chat-shared.zhile.io/shared.html
    """

    def __init__(self, base_url: str, session_key: str, data_token: str, http_session: HttpSession = None):
        super().__init__(session=http_session, long_connection=True, base_url=base_url)
        self.set_cookie(key='session_password', value=session_key)
        self.__session_key = session_key
        self.__data_token = data_token
        self.__access_token = None
        self.__default_model = None  # 'ext-davinci-002-render-sha'
        # multiple rounds
        self.__account_id = None
        self.__conversation_id = None
        self.__last_message_id = None
        self.__message_queue = MessageQueue()

    @property
    def session_key(self) -> str:
        return self.__session_key

    @property
    def data_token(self) -> str:
        return self.__data_token

    @property
    def access_token(self) -> Optional[str]:
        return self.__access_token

    @property
    def default_model(self) -> Optional[str]:
        return self.__default_model

    @property
    def account_id(self) -> Optional[str]:
        return self.__account_id

    @property
    def conversation_id(self) -> Optional[str]:
        return self.__conversation_id

    def auth_login(self):
        """ login and update 'credential' into cookies """
        response = self.http_post(url='/auth/login', headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        }, data={
            'token_key': self.data_token,
            'session_password': self.session_key,
        })
        show_response(response=response)

    def auth_session(self):
        """ fetch 'accessToken' """
        response = self.http_get(url='/api/auth/session', headers={
        })
        show_response(response=response)
        info = response.json()
        token = info.get('accessToken')
        if token is None:
            self.error(msg='failed to get accessToken: %s' % info)
        else:
            self.info(msg='accessToken: %s' % token)
            self.__access_token = token
            self.set_cookie(key='credential', value=token)

    def accounts_check(self, v_date: str = 'v4-2023-04-27'):
        """ fetch 'account_id' """
        response = self.http_get(url='/api/accounts/check/%s' % v_date, headers={
            'X-Authorization': self.access_token,
        })
        show_response(response=response)
        info = response.json()
        accounts = info.get('accounts')
        if accounts is None:
            self.warning(msg='failed to get accounts: %s' % info)
        else:
            default_account = accounts.get('default')
            if default_account is None:
                self.warning(msg='default account not found: %s' % accounts)
            else:
                account = default_account.get('account')
                if account is None:
                    self.error(msg='default account error: %s' % default_account)
                else:
                    aid = account.get('account_id')
                    self.info(msg='account id: %s' % aid)
                    self.__account_id = aid
                subs = default_account.get('last_active_subscription')
                if subs is None:
                    self.info(msg='last_active_subscription not found: %s' % default_account)
                else:
                    sid = subs.get('subscription_id')
                    self.info(msg='subscription id: %s' % sid)
                    # self.__conversation_id = sid

    def models(self):
        """ fetch 'default_model' """
        params = 'history_and_training_disabled=false'
        response = self.http_get(url='/api/models?%s' % params, headers={
            'X-Authorization': self.access_token,
        })
        show_response(response=response)
        info = response.json()
        categories = info.get('categories')
        if categories is None or len(categories) == 0:
            self.error(msg='failed to get model: %s' % info)
        else:
            default_cat = categories[0]
            default_model = default_cat.get('default_model')
            self.info(msg='default model: %s' % default_model)
            if default_model is None:
                self.error(msg='failed to get default_model: %s' % categories)
            else:
                self.__default_model = default_model

    def conversations(self):
        """ fetch conversations """
        params = 'offset=0&limit=28&order=updated'
        response = self.http_get(url='/api/conversations?%s' % params, headers={
            'X-Authorization': self.access_token,
        })
        show_response(response=response)
        info = response.json()
        items = info.get('items')
        if items is None or len(items) == 0:
            self.warning(msg='failed to get conversations: %s' % info)
        else:
            cid = items[0].get('id')
            self.info(msg='last conversation: %s, total count: %d' % (items[0], len(items)))
            self.__conversation_id = cid

    def conversation_limit(self):
        response = self.http_get(url='/api/conversation_limit', headers={
            'X-Authorization': self.access_token,
        })
        show_response(response=response)

    def ask(self, question: str) -> Optional[str]:
        pid = self.__last_message_id
        mid = new_msg_id()
        msg = {
            'id': mid,
            'author': {'role': 'user'},
            'content': {
                'content_type': 'text',
                'parts': [question],
            }
        }
        self.__message_queue.push(msg=msg)
        info = {
            'action': 'next',
            'history_and_training_disabled': 0,
            'model': self.default_model,
            'parent_message_id': pid,
            'parent_id': pid,
            'timezone_offset_min': -480,
            'messages': self.__message_queue.messages,
        }
        self.info(msg='sending message: %s' % info)
        data = utf8_encode(string=json_encode(obj=info))
        response = self.http_post(url='/api/conversation', headers={
            'Content-Type': 'application/json',
            'X-Authorization': self.access_token,
        }, data=data)
        # show_response(response=response)
        res = parse_response(text=response.text)
        if res is None:
            self.error(msg='failed to parse response: %s' % response.text)
        else:
            cid = res.get('conversation_id')
            if cid is not None:
                self.__conversation_id = cid
            msg = res['message']
            mid = msg['id']
            self.__last_message_id = mid
            self.__message_queue.push(msg=msg, trim=True)
            # respond text
            content = msg['content']
            if isinstance(content, str):
                return content
            parts = content['parts']
            if isinstance(parts, List) and len(parts) > 0:
                return parts[0]


def parse_response(text: str) -> Optional[dict]:
    response = None
    messages = text.splitlines()
    for item in messages:
        if item.startswith('data: '):
            line = item[6:].strip()
        else:
            Log.debug(msg='skip line: %s' % item)
            continue
        if len(line) < 2 or not line.startswith('{') or not line.endswith('}'):
            Log.debug(msg='skip line: %s' % item)
            continue
        info = json_decode(string=line)
        msg = info.get('message')
        if msg is None:
            Log.error(msg='error line: %s' % item)
        elif 'id' in msg and 'author' in msg and 'content' in msg:
            response = info
            text = line
        else:
            Log.warning(msg='skip message: %s' % item)
    Log.debug(msg='pick last message data: %s' % text)
    return response
