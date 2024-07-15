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

from typing import Optional, Union, Dict

import requests
from requests import Response, Session
from requests.cookies import RequestsCookieJar

from dimples.utils import Log, Logging
from dimples.utils import SharedCacheManager
from dimples import DateTime


def fetch_cookies(response: Response) -> Optional[Dict]:
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

    def __init__(self, long_connection: bool = False, proxies: Dict[str, str] = None, verify: bool = True):
        super().__init__()
        self.__long_connection = long_connection
        self.__session = None
        self.__proxies = proxies
        self.__verify = verify

    @property
    def session(self) -> Session:
        network = self.__session
        if network is None:
            network = requests.session()
            self.__session = network
        return network

    @property
    def proxies(self) -> Optional[Dict[str, str]]:
        return self.__proxies

    @proxies.setter
    def proxies(self, values: Dict[str, str]):
        self.__proxies = values

    def set_proxy(self, scheme: str, proxy: Optional[str]):
        values = self.__proxies
        if proxy is not None:
            if values is None:
                values = self.__proxies = {}
            values[scheme] = proxy
        elif values is not None:
            values.pop(scheme, None)

    def http_get(self, url: str, headers: Dict = None, cookies: Dict = None) -> Response:
        network = self.session if self.__long_connection else requests
        proxies = self.__proxies
        verify = self.__verify
        return network.request(method='GET', url=url,
                               headers=headers, cookies=cookies,
                               proxies=proxies, verify=verify)

    def http_post(self, url: str, data: Union[Dict, bytes], headers: Dict = None, cookies: Dict = None) -> Response:
        network = self.session if self.__long_connection else requests
        proxies = self.__proxies
        verify = self.__verify
        return network.request(method='POST', url=url, data=data,
                               headers=headers, cookies=cookies,
                               proxies=proxies, verify=verify)


class HttpClient(Logging):

    CACHE_EXPIRES = 60*60  # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, session: HttpSession = None,
                 long_connection: bool = False, proxies: Dict[str, str] = None, verify: bool = True,
                 base_url: str = None):
        super().__init__()
        if session is None:
            session = HttpSession(long_connection=long_connection, proxies=proxies, verify=verify)
        self.__session = session
        self.__cookies = {}
        self.__base = base_url
        man = SharedCacheManager()
        self.__web_cache = man.get_pool(name='web_pages')  # url => html

    @property
    def base_url(self) -> Optional[str]:
        return self.__base

    @property
    def proxies(self) -> Optional[Dict[str, str]]:
        return self.__session.proxies

    @proxies.setter
    def proxies(self, values: Dict[str, str]):
        self.__session.proxies = values

    def set_proxy(self, scheme: str, proxy: Optional[str]):
        self.__session.set_proxy(scheme=scheme, proxy=proxy)

    @property
    def cookies(self) -> Dict:
        return self.__cookies

    def set_cookie(self, key: str, value: str):
        self.__cookies[key] = value

    def get_cookie(self, key: str) -> Optional[str]:
        return self.__cookies.get(key)

    def clear_cookies(self):
        self.__cookies.clear()

    def _update_cookies(self, response: Response):
        cookies = fetch_cookies(response=response)
        if cookies is None:
            self.info(msg='cookies not found')
            return None
        for key in cookies:
            # TODO: store with domain & path
            self.__cookies[key] = cookies[key]
        return cookies

    def remove_cache(self, url: str):
        self.__web_cache.erase(key=url)

    def cache_get(self, url: str, headers: Dict = None):
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__web_cache.fetch(key=url, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__web_cache.update(key=url, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. query remote server
            response = self.http_get(url=url, headers=headers)
            if response.status_code == 200:
                value = response.text
                # 3. update memory cache
                self.__web_cache.update(key=url, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def http_get(self, url: str, headers: Dict = None) -> Response:
        url = self._get_url(url=url)
        self.info(msg='GET %s' % url)
        response = self.__session.http_get(url=url, headers=headers, cookies=self.cookies)
        self._update_cookies(response=response)
        return response

    def http_post(self, url: str, data: Union[Dict, bytes], headers: Dict = None) -> Response:
        url = self._get_url(url=url)
        self.info(msg='POST %s' % url)
        response = self.__session.http_post(url=url, data=data, headers=headers, cookies=self.cookies)
        self._update_cookies(response=response)
        return response

    def _get_url(self, url: str) -> str:
        if url.find('://') > 0:
            return url
        base = self.__base
        return url if base is None else '%s%s' % (base, url)
