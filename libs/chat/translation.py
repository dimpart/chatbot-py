# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2025 Albert Moky
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

import threading
from typing import Optional, Dict

from dimples import DateTime, Dictionary
from dimples import Content, AppCustomizedContent

from ..utils import Singleton
from .base import TranslateRequest


"""
        translate content : {
            type : 0xCC,
            sn   : 123,

            app   : "chat.dim.translate",  // application
            mod   : "translate",           // module name
            act   : "request",             // action name (or "respond")

            tag   : 123,

            text   : "{TEXT}",  // or {TRANSLATION} in respond
            code   : "{LANG_CODE}",
            result : {
                from        : "{SOURCE_LANGUAGE}",
                to          : "{TARGET_LANGUAGE}",
                code        : "{LANG_CODE}",
                text        : "{TEXT}",        // source text
                translation : "{TRANSLATION}"  // target text
            }
        }
"""


class TranslateResult(Dictionary):

    @property
    def from_lang(self) -> Optional[str]:
        return self.get_str(key='from', default=None)

    @property
    def to_lang(self) -> Optional[str]:
        return self.get_str(key='to', default=None)

    @property
    def to_code(self) -> Optional[str]:
        return self.get_str(key='code', default=None)

    @property
    def text(self) -> Optional[str]:
        return self.get_str(key='text', default=None)

    @property
    def translation(self) -> Optional[str]:
        return self.get_str(key='translation', default=None)

    @property
    def valid(self) -> bool:
        if self.from_lang is None:
            return False
        elif self.to_lang is None:
            return False
        elif self.to_code is None:
            return False
        # sometimes the AI server would return translation in 'text' field
        return self.translation is not None or self.text is not None


class TranslateContent(AppCustomizedContent):

    @property
    def tag(self) -> Optional[int]:
        return self.get_int(key='tag', default=None)

    @property
    def text(self) -> Optional[str]:
        return self.get_str(key='text', default=None)

    @property
    def to_code(self) -> Optional[str]:
        result = self.result
        if result is not None:
            code = result.to_code
            if code is not None:
                return code
        return self.get_str(key='code', default=None)

    @property
    def result(self) -> Optional[TranslateResult]:
        info = self.get('result')
        if info is not None:
            return TranslateResult(dictionary=info)

    @property
    def success(self) -> bool:
        result = self.result
        if result is not None:
            return result.valid

    @classmethod
    def respond(cls, result: TranslateResult, query: Content):
        response = TranslateContent(app=Translator.APP, mod=Translator.MOD, act='respond')
        #
        #  check translation
        #
        text = result.translation
        if text is None:
            text = result.text
            if text == query.get('text'):
                text = None
        if text is not None and len(text) > 0:
            response['text'] = text
            response['result'] = result.dictionary
        #
        #  extra param: serial number
        #
        tag = query.get('tag')
        if tag is None:
            tag = query.sn
        response['tag'] = tag
        #
        #  extra param: language code
        #
        code = query.get('code')
        if code is not None:
            response['code'] = code
        #
        #  extra param: text format
        #
        txt_fmt = query.get('format')  # markdown
        if txt_fmt is not None:
            response['format'] = txt_fmt
        #
        #  extra param: visibility
        #
        hidden = query.get('hidden')
        if hidden is not None:
            response['hidden'] = hidden
            response['muted'] = hidden
        return response


@Singleton
class Translator:

    APP = 'chat.dim.translate'
    MOD = 'translate'

    def __init__(self):
        super().__init__()
        self.__cache = TranslateCache()
        self.__lock = threading.Lock()
        self.__expired = DateTime.current_timestamp() + 600

    def purge(self):
        now = DateTime.current_timestamp()
        if now < self.__expired:
            return -1
        else:
            self.__expired = now + 600
        # clear expired responses
        with self.__lock:
            return self.__cache.purge()

    def fetch(self, request: TranslateRequest) -> Optional[str]:
        with self.__lock:
            return self.__cache.fetch(request=request)

    def cache(self, request: TranslateRequest, response: str):
        with self.__lock:
            self.__cache.cache(request=request, response=response)


# private
class TranslateCache:

    def __init__(self):
        super().__init__()
        # lang_code => text => response
        self.__table: Dict[str, Dict[str, TranslateResponse]] = {}

    def purge(self):
        count = 0
        for code in self.__table:
            dictionary = self.__table.get(code)
            if dictionary is None:
                continue
            empties = []
            for text in dictionary:
                response = dictionary.get(text)
                if response is None:
                    empties.append(text)
                elif response.expired:
                    empties.append(text)
            for text in empties:
                dictionary.pop(text, None)
                count += 1
        return count

    def fetch(self, request: TranslateRequest) -> Optional[str]:
        content = request.content
        text = content.get('text')
        code = request.code
        # get dictionary with language code
        dictionary = self.__table.get(code)
        if dictionary is not None:
            record = dictionary.get(text)
            if record is None:
                # not found
                return None
            elif record.expired:
                # expired
                dictionary.pop(text, None)
                return None
            else:
                # got it
                return record.response

    def cache(self, request: TranslateRequest, response: str):
        content = request.content
        text = content.get('text')
        code = request.code
        # get dictionary with language code
        dictionary = self.__table.get(code)
        if dictionary is None:
            dictionary = {}
            self.__table[code] = dictionary
        # cache with expires
        mod = content.get('mod')
        if mod == 'test':
            expires = TranslateResponse.WARNING_EXPIRES
        else:
            expires = TranslateResponse.TEXT_EXPIRES
        # update dictionary
        dictionary[text] = TranslateResponse(response=response, expires=expires)


# private
class TranslateResponse:

    TEXT_EXPIRES = 3600
    WARNING_EXPIRES = 3600 * 24

    def __init__(self, response: str, expires: float):
        super().__init__()
        self.__response = response
        self.__expired = DateTime.current_timestamp() + expires

    @property
    def response(self) -> str:
        return self.__response

    @property
    def expired(self) -> bool:
        return self.__expired < DateTime.current_timestamp()
