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

from typing import Optional, Dict

from dimples import DateTime, Dictionary
from dimples import Content, AppCustomizedContent

from ..utils import Singleton


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
        # elif self.translation is None:
        #     return False
        else:
            return True


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
        response = TranslateContent(app='chat.dim.translate', mod='translate', act='respond')
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

    def __init__(self):
        super().__init__()
        # text => lang code => response
        self.__caches: Dict[str, Dict[str, TranslateResponse]] = {}

    def fetch(self, text: str, code: str) -> Optional[str]:
        table = self.__caches.get(text)
        if table is not None:
            record = table.get(code)
            if record is None:
                # not found
                pass
            elif record.expired:
                # expired
                table.pop('code', None)
            else:
                # got it
                return record.response

    def cache(self, text: str, code: str, response: str):
        table = self.__caches.get(text)
        if table is None:
            table = {}
            self.__caches[text] = table
        table[code] = TranslateResponse(response=response)


# private
class TranslateResponse:

    EXPIRES = 3600

    def __init__(self, response: str):
        super().__init__()
        self.__response = response
        self.__expired = DateTime.current_timestamp() + self.EXPIRES

    @property
    def response(self) -> str:
        return self.__response

    @property
    def expired(self) -> bool:
        return self.__expired < DateTime.current_timestamp()
