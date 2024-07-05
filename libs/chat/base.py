# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from abc import ABC, abstractmethod
from typing import Optional, Dict

from dimples import DateTime
from dimples import EntityType, ID
from dimples import Envelope, Content
from dimples import CommonFacebook

from ..utils import Logging


class Request(ABC):
    """ Request from sender """

    @property
    @abstractmethod
    def identifier(self) -> ID:
        """ Sender, or group ID """
        raise NotImplemented

    @property
    @abstractmethod
    def time(self) -> Optional[DateTime]:
        raise NotImplemented

    @property
    @abstractmethod
    def text(self) -> Optional[str]:
        raise NotImplemented

    # Override
    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s identifier="%s">\n\t[%s] %s\n</%s module="%s">' \
               % (cname, self.identifier, self.time, self.text, cname, mod)

    # Override
    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s identifier="%s">\n\t[%s] %s\n</%s module="%s">' \
               % (cname, self.identifier, self.time, self.text, cname, mod)

    @abstractmethod
    async def build(self) -> Optional[str]:
        raise NotImplemented


class Setting(Request):
    """ System Setting """

    def __init__(self, definition: str):
        super().__init__()
        self.__definition = definition

    @property  # Override
    def identifier(self) -> ID:
        return ID.parse(identifier='system@anywhere')

    @property  # Override
    def time(self) -> Optional[DateTime]:
        return None

    @property  # Override
    def text(self) -> Optional[str]:
        return self.__definition

    # Override
    async def build(self) -> Optional[str]:
        return self.__definition


class Greeting(Request, Logging):
    """ Say Hi """

    def __init__(self, identifier: ID, envelope: Envelope, content: Content, facebook: CommonFacebook):
        super().__init__()
        self.__identifier = identifier
        self.__envelope = envelope
        self.__content = content
        self.__facebook = facebook
        self.__text = None

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property
    def envelope(self) -> Envelope:
        return self.__envelope

    @property
    def content(self) -> Content:
        return self.__content

    @property  # Override
    def identifier(self) -> ID:
        return self.__identifier

    @property  # Override
    def time(self) -> Optional[DateTime]:
        return self.content.time

    @property  # Override
    def text(self) -> Optional[str]:
        return self.__text

    # Override
    async def build(self) -> Optional[str]:
        sender = self.identifier
        assert sender.is_user, 'greeting sender error: %s' % sender
        name = await get_nickname(identifier=sender, facebook=self.facebook)
        if name is None or len(name) == 0:
            self.error(msg='failed to get nickname for sender: %s' % sender)
            return None
        language = await get_language(identifier=sender, facebook=self.facebook)
        text = 'My name is "%s", my current language environment code is "%s".' \
               ' Please try to greet me in a language that suits me,' \
               ' considering my language habits and location.' \
               ' Please keep our names unchanged and' \
               ' not to translate them in your response.' % (name, language)
        self.__text = text
        return text


class ChatRequest(Request, Logging):
    """ Prompt from sender """

    def __init__(self, envelope: Envelope, content: Content, facebook: CommonFacebook):
        super().__init__()
        self.__envelope = envelope
        self.__content = content
        self.__facebook = facebook
        self.__text = None

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property
    def envelope(self) -> Envelope:
        return self.__envelope

    @property
    def content(self) -> Content:
        return self.__content

    @property  # Override
    def identifier(self) -> ID:
        group = self.content.group
        if group is not None:
            return group
        return self.envelope.sender

    @property  # Override
    def time(self) -> Optional[DateTime]:
        return self.content.time

    @property  # Override
    def text(self) -> Optional[str]:
        return self.__text

    # Override
    async def build(self) -> Optional[str]:
        text = self.content.get('text')
        if text is not None and len(text) > 0:
            text = await self.__filter(text=text)
        self.__text = text
        return text

    async def __filter(self, text: str) -> Optional[str]:
        sender = self.envelope.sender
        if EntityType.BOT == sender.type:
            self.info('ignore message from another bot: %s, "%s"' % (sender, text))
            return None
        elif EntityType.STATION == sender.type:
            self.info('ignore message from station: %s, "%s"' % (sender, text))
            return None
        # check request time
        req_time = self.time
        assert req_time is not None, 'request error: %s' % self
        dt = DateTime.now() - req_time
        if dt > 600:
            # Old message, ignore it
            self.warning(msg='ignore expired message from %s: %s' % (sender, req_time))
            return None
        # check group message
        content = self.content
        if content.group is None:
            # personal message
            return text
        # checking '@nickname '
        receiver = self.envelope.receiver
        facebook = self.facebook
        bot_name = await get_nickname(identifier=receiver, facebook=facebook)
        assert bot_name is not None and len(bot_name) > 0, 'receiver error: %s' % receiver
        at = '@%s ' % bot_name
        naked = text.replace(at, '')
        at = '@%s' % bot_name
        if text.endswith(at):
            naked = naked[:-len(at)]
        if naked != text:
            return naked
        self.info('ignore group message that not querying me(%s): %s' % (at, text))


#
#   Nickname
#
async def get_nickname(identifier: ID, facebook: CommonFacebook) -> Optional[str]:
    visa = await facebook.get_document(identifier=identifier)
    if visa is not None:
        return visa.name


#
#   Language
#
async def get_language(identifier: ID, facebook: CommonFacebook) -> str:
    visa = await facebook.get_document(identifier=identifier)
    if visa is None:
        return 'en'
    # check 'app:language'
    app = visa.get_property(key='app')
    if isinstance(app, Dict):
        language = app.get('language')
    else:
        language = None
    # check 'sys:locale'
    sys = visa.get_property(key='sys')
    if isinstance(sys, Dict):
        locale = sys.get('locale')
    else:
        locale = None
    # combine them
    return _combine_language(language=language, locale=locale, default='en')


def _combine_language(language: Optional[str], locale: Optional[str], default: str) -> str:
    # if 'language' not found:
    #     return 'locale' or default code
    if language is None or len(language) == 0:
        if locale is None or len(locale) == 0:
            return default
        else:
            return locale
    # if 'locale' not found
    #     return 'language'
    if locale is None or len(locale) == 0:
        return language
    assert isinstance(language, str)
    assert isinstance(locale, str)
    # combine 'language' and 'locale'
    lang = language.lower()
    if lang == 'zh_cn':
        language = 'zh_Hans'
    elif lang == 'zh_tw':
        language = 'zh_Hant'
    else:
        pos = language.rfind('_')
        if pos > 0:
            language = language[:pos]
    pos = locale.rfind('_')
    if pos > 0:
        locale = locale[pos+1:]
    return '%s_%s' % (language, locale)
