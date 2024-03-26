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

from typing import Optional, List, Dict

from dimples import ID
from dimples import Content
from dimples import TextContent, FileContent
from dimples import CommonFacebook
from dimples import PlainKey

from ....utils import filename_from_url
from ....utils import Logging
from ....utils import HttpClient

from ....client import Emitter

from ....chat import Request
from ....chat import ChatBox, ChatClient
from ....chat.base import get_nickname

from .model import TensorArt


#
#   Chat Box
#


class SDChatBox(ChatBox, Logging):

    NO_CONTENT = '''{
        "code": 204,
        "error": "No Content."
    }'''

    NOT_FOUND = '''{
        "code": 404,
        "error": "No response, please try again later."
    }'''

    def __init__(self, identifier: ID, facebook: CommonFacebook,
                 referer: str, http_client: HttpClient):
        super().__init__(identifier=identifier)
        self.__facebook = facebook
        sd = TensorArt(referer=referer, http_client=http_client)
        self.__sd = sd

    # Override
    def _say_hi(self, prompt: str, request: Request):
        pass

    # Override
    def _ask_question(self, prompt: str, content: TextContent, request: Request):
        projects = self.__sd.search(keywords=prompt)
        count = 0 if projects is None else len(projects)
        if count == 0:
            text = self.NO_CONTENT
            self.respond_text(text=text, request=request)
            return
        # build text message
        text = self.__build_text(projects=projects)
        if count > 3:
            projects = projects[:3]
        responses = []
        for item in projects:
            responses.append(item)
        responses.append(text)
        self.__chat_response(results=responses, request=request)

    # Override
    def _send_content(self, content: Content, receiver: ID):
        emitter = Emitter()
        emitter.send_content(content=content, receiver=receiver)

    # noinspection PyMethodMayBeStatic
    def __build_text(self, projects: List[Dict]) -> str:
        names = []
        for item in projects:
            text = item.get('name')
            if text is not None and len(text) > 0:
                names.append(text)
        return 'You can also input:\n    %s' % '\n    '.join(names)

    def __chat_response(self, results: List, request: Request):
        emitter = Emitter()
        req_time = request.time
        identifier = request.sender
        name = get_nickname(identifier=identifier, facebook=self.__facebook)
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
                self.warning(msg='replace respond time: %s => %s + %d' % (res_time, req_time, order))
                content['time'] = req_time + order
            else:
                content['time'] = res_time + order
            self.info(msg='responding: %s, %s' % (identifier, content))
            emitter.send_content(content=content, receiver=identifier)


class SDChatClient(ChatClient):

    BASE_URL = 'https://api.tensor.art'
    REFERER_URL = 'https://tensor.art/'

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook
        self.__http_client = HttpClient(long_connection=True, verify=False, base_url=self.BASE_URL)

    # Override
    def _new_box(self, identifier: ID) -> Optional[ChatBox]:
        facebook = self.__facebook
        referer = self.REFERER_URL
        http_client = self.__http_client
        return SDChatBox(identifier=identifier, facebook=facebook,
                         referer=referer, http_client=http_client)
