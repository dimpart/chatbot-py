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

from aiou import Path, TextFile

from .types import URI, MapInfo
from .utils import Log
from .utils import parse_json
from .utils import hex_md5


class Config(MapInfo):

    def get_option(self, section: str, option: str) -> Optional[Any]:
        sub: Dict = self.get(key=section, default={})
        return sub.get(option)

    @classmethod
    async def load(cls, path: str):
        info = await _file_read(path=path)
        if info is not None:
            info = parse_json(text=info)
            return cls(info=info)


class LiveConfig(Config):

    @property
    def sources(self) -> List[URI]:
        array = self.get_option(section='tvbox', option='sources')
        return [] if array is None else array

    @property
    def lives(self) -> List[URI]:
        array = self.get_option(section='tvbox', option='lives')
        return [] if array is None else array

    @property
    def base_url(self) -> Optional[URI]:
        """ base url """
        return self.get_option(section='tvbox', option='base-url')

    @property
    def output_dir(self) -> Optional[str]:
        """ output directory """
        return self.get_option(section='tvbox', option='output-dir')

    def get_index_file(self) -> Optional[str]:
        return self.get_option(section='tvbox', option='index-file')

    def get_lives_file(self, url: URI) -> Optional[str]:
        file = self.get_option(section='tvbox', option='lives-file')
        if file is not None:
            digest = hex_md5(data=url)
            return file.replace(r'{HASH}', digest)

    def get_source_file(self, url: URI) -> Optional[str]:
        file = self.get_option(section='tvbox', option='source-file')
        if file is not None:
            digest = hex_md5(data=url)
            return file.replace(r'{HASH}', digest)

    #
    #   Output file path
    #

    def get_output_index_path(self) -> str:
        """ output index """
        file = self.get_index_file()
        return join_path(base=self.output_dir, file=file)

    def get_output_lives_path(self, url: URI) -> str:
        """ output lives """
        file = self.get_lives_file(url=url)
        return join_path(base=self.output_dir, file=file)

    def get_output_source_path(self, url: URI) -> str:
        file = self.get_source_file(url=url)
        return join_path(base=self.output_dir, file=file)

    #
    #   Output URL
    #

    def get_output_index_url(self) -> Optional[URI]:
        file = self.get_index_file()
        return join_path(base=self.base_url, file=file)

    def get_output_lives_url(self, url: URI):
        file = self.get_lives_file(url=url)
        return join_path(base=self.base_url, file=file)


def join_path(base: str, file: str) -> str:
    assert base is not None and len(base) > 0, 'base path empty, file: %s' % file
    assert file is not None and len(file) > 0, 'file name empty, path: %s' % base
    # standard base path
    if base.endswith(r'/'):
        base = base.rstrip(r'/')
    else:
        base = Path.dir(path=base)
    # standard file name
    if file.startswith(r'./'):
        file = file[2:]
    return '%s/%s' % (base, file)


async def _file_read(path: str) -> Optional[str]:
    try:
        return await TextFile(path=path).read()
    except Exception as error:
        Log.error(msg='failed to read file: %s, error: %s' % (path, error))
