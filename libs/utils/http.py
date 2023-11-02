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

from typing import Optional, Union

import requests
from requests import Response, Session
from requests.cookies import RequestsCookieJar

from dimples.utils import Log, Logging


def fetch_cookies(response: Response) -> Optional[dict]:
    cookies = response.cookies
    if isinstance(cookies, RequestsCookieJar):
        return cookies.get_dict()


def show_response(response: Response):
    status_code = response.status_code
    text = response.text
    Log.info(msg='[HTTP]\t> response: code=%d, len=%d' % (status_code, len(text)))
    Log.debug(msg='[HTTP]\t> response: %d, %s' % (status_code, text))
    Log.info(msg='[HTTP]\t> cookies: %s' % fetch_cookies(response=response))


class HttpSession:

    def __init__(self, long_connection: bool = False, verify: bool = True):
        super().__init__()
        self.__long_connection = long_connection
        self.__session = None
        self.__verify = verify

    @property
    def session(self) -> Session:
        network = self.__session
        if network is None:
            network = requests.session()
            self.__session = network
        return network

    def http_get(self, url: str, headers: dict = None, cookies: dict = None) -> Response:
        network = self.session if self.__long_connection else requests
        verify = self.__verify
        return network.request(method='GET', url=url, headers=headers, cookies=cookies, verify=verify)

    def http_post(self, url: str, data: Union[dict, bytes], headers: dict = None, cookies: dict = None) -> Response:
        network = self.session if self.__long_connection else requests
        verify = self.__verify
        return network.request(method='POST', url=url, data=data, headers=headers, cookies=cookies, verify=verify)


class HttpClient(Logging):

    def __init__(self, session: HttpSession = None, long_connection: bool = False, verify: bool = True,
                 base_url: str = None):
        super().__init__()
        if session is None:
            session = HttpSession(long_connection=long_connection, verify=verify)
        self.__session = session
        self.__cookies = {}
        self.__base = base_url

    @property
    def cookies(self) -> dict:
        return self.__cookies

    def set_cookie(self, key: str, value: str):
        self.__cookies[key] = value

    def get_cookie(self, key: str) -> Optional[str]:
        return self.__cookies.get(key)

    def _update_cookies(self, response: Response):
        cookies = fetch_cookies(response=response)
        if cookies is None:
            self.info(msg='cookies not found')
            return None
        for key in cookies:
            # TODO: store with domain & path
            self.__cookies[key] = cookies[key]
        return cookies

    def _get_url(self, url: str) -> str:
        if url.find('://') > 0:
            return url
        base = self.__base
        return url if base is None else '%s%s' % (base, url)

    def http_get(self, url: str, headers: dict = None) -> Response:
        url = self._get_url(url=url)
        self.info(msg='GET %s' % url)
        response = self.__session.http_get(url=url, headers=headers, cookies=self.cookies)
        self._update_cookies(response=response)
        return response

    def http_post(self, url: str, data: Union[dict, bytes], headers: dict = None) -> Response:
        url = self._get_url(url=url)
        self.info(msg='POST %s' % url)
        response = self.__session.http_post(url=url, data=data, headers=headers, cookies=self.cookies)
        self._update_cookies(response=response)
        return response
