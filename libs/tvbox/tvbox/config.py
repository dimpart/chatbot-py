# -*- coding: utf-8 -*-
#
#   TV-Box: Live Stream
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
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

from typing import Optional, Any, List, Dict

from .types import URI, MapInfo
from .utils import hex_md5
from .utils import path_join
from .utils import json_file_read


class LiveConfig(MapInfo):

    SECTION_NAME = 'tvbox'

    def get_section(self, section: str) -> Dict[str, Any]:
        return self.get(key=section, default={})

    def get_option(self, option: str, section: str = None) -> Optional[Any]:
        if section is None:
            section = self.SECTION_NAME
        sub = self.get_section(section=section)
        return sub.get(option)

    #
    #   Source URLs
    #

    @property
    def sources(self) -> List[URI]:
        array = self.get_option(option='sources')
        return [] if array is None else array

    @property
    def lives(self) -> List[URI]:
        array = self.get_option(option='lives')
        return [] if array is None else array

    @property
    def base_url(self) -> Optional[URI]:
        """ base url """
        return self.get_option(option='base-url')

    @property
    def output_dir(self) -> Optional[str]:
        """ output directory """
        return self.get_option(option='output-dir')

    #
    #   Output file names
    #

    def get_index_file(self) -> str:
        file: str = self.get_option(option='index-file')
        if file is None:
            return 'tvbox.json'
        else:
            return file

    def get_lives_file(self, url: URI) -> str:
        file: str = self.get_option(option='lives-file')
        if file is None or file.find(r'{HASH}') < 0:
            file = 'lives-{HASH}.txt'
        digest = hex_md5(data=url)
        return file.replace(r'{HASH}', digest)

    def get_source_file(self, url: URI) -> str:
        file: str = self.get_option(option='source-file')
        if file is None or file.find(r'{HASH}') < 0:
            file = 'source-{HASH}.txt'
        digest = hex_md5(data=url)
        return file.replace(r'{HASH}', digest)

    #
    #   Output file paths
    #

    def get_output_index_path(self) -> Optional[str]:
        """ output index """
        base = self.output_dir
        if base is not None:
            file = self.get_index_file()
            return path_join(base, file)

    def get_output_lives_path(self, url: URI) -> Optional[str]:
        """ output lives """
        base = self.output_dir
        if base is not None:
            file = self.get_lives_file(url=url)
            return path_join(base, file)

    def get_output_source_path(self, url: URI) -> Optional[str]:
        base = self.output_dir
        if base is not None:
            file = self.get_source_file(url=url)
            return path_join(base, file)

    #
    #   Output URLs
    #

    def get_output_index_url(self) -> Optional[URI]:
        base = self.base_url
        if base is not None:
            file = self.get_index_file()
            return path_join(base, file)

    def get_output_lives_url(self, url: URI) -> Optional[URI]:
        base = self.base_url
        if base is not None:
            file = self.get_lives_file(url=url)
            return path_join(base, file)

    #
    #   Factory
    #

    @classmethod
    async def load(cls, path: str):
        info = await json_file_read(path=path)
        if info is not None:
            return cls(info=info)
