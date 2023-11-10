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

from typing import Optional, Union, Any, List, Dict

from requests import Response

from ...utils import utf8_encode, json_encode, json_decode
from ...utils import Log, Logging
from ...utils import HttpClient


class TensorArt(Logging):
    """
        Tensor Art
        ~~~~~~~~~~

        https://tensor.art/
    """

    def __init__(self, referer: str, http_client: HttpClient = None):
        super().__init__()
        self.__http_client = http_client
        self.__referer = referer

    def http_post(self, url: str, data: Union[dict, bytes], headers: dict = None) -> Response:
        return self.__http_client.http_post(url=url, data=data, headers=headers)

    def search(self, keywords: str) -> List[Dict]:
        payload = {
            "query": keywords,
            "visibility": "ORDINARY",
            "type": "MODEL",
            "limit": 20,
            "offset": 0,
        }
        body = json_encode(obj=payload)
        self.info(msg='sending payload: %s' % body)
        data = utf8_encode(string=body)
        response = self.http_post(url='/community-web/v1/search/general/v2', headers={
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Content-Type': 'application/json',
            'Origin': self.__referer,
            'Referer': self.__referer,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/116.0.0.0 Safari/537.36',
        }, data=data)
        return fetch_projects(text=response.text)


def fetch_projects(text: str) -> List[Dict]:
    projects = []
    array = parse_response(text=text)
    if array is not None:
        for item in array:
            result = parse_project(info=item)
            if result is not None:
                projects.append(result)
    return projects


def parse_response(text: str) -> Optional[List]:
    try:
        info = json_decode(string=text)
    except Exception as e:
        Log.error(msg='failed to parse response: %s, error: %s' % (text, e))
        return None
    data = info.get('data')
    if isinstance(data, Dict):
        data = data.get('projectData')
    if isinstance(data, Dict):
        return data.get('projects')


def parse_project(info: Any) -> Optional[Dict]:
    if isinstance(info, Dict):
        project = {
            'name': info.get('name')
        }
        model = info.get('model')
        if isinstance(model, Dict):
            cover = model.get('cover')
            if isinstance(cover, Dict):
                project['url'] = cover.get('url')
        return project
