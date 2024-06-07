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

from typing import Optional, Iterator, Any, Dict
from typing import ItemsView, KeysView, ValuesView


class MapInfo:

    def __init__(self, info: Dict = None):
        super().__init__()
        if info is None:
            info = {}
        self.__dictionary = info

    @property
    def dictionary(self) -> Dict:
        return self.__dictionary

    def clear(self):
        """ D.clear() -> None.  Remove all items from D. """
        self.__dictionary.clear()

    def get(self, key: str, default: Any = None) -> Any:
        """ Return the value for key if key is in the dictionary, else default. """
        return self.__dictionary.get(key, default)

    def set(self, key: str, value: Optional[Any]):
        if value is None:
            self.__dictionary.pop(key, None)
        else:
            if isinstance(value, MapInfo):
                value = value.dictionary
            self.__dictionary[key] = value

    def items(self) -> ItemsView[str, Any]:
        """ D.items() -> a set-like object providing a view on D's items """
        return self.__dictionary.items()

    def keys(self) -> KeysView[str]:
        """ D.keys() -> a set-like object providing a view on D's keys """
        return self.__dictionary.keys()

    def values(self) -> ValuesView[Any]:
        """ D.values() -> an object providing a view on D's values """
        return self.__dictionary.values()

    def pop(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        D.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised
        """
        return self.__dictionary.pop(key, default)

    def __contains__(self, o) -> bool:
        """ True if the dictionary has the specified key, else False. """
        return self.__dictionary.__contains__(o)

    def __getitem__(self, k: str) -> Any:
        """ x.__getitem__(y) <==> x[y] """
        return self.__dictionary.__getitem__(k)

    def __setitem__(self, k: str, v: Optional[Any]):
        """ Set self[key] to value. """
        self.__dictionary.__setitem__(k, v)

    def __delitem__(self, v: str):
        """ Delete self[key]. """
        self.__dictionary.__delitem__(v)

    def __iter__(self) -> Iterator[str]:
        """ Implement iter(self). """
        return self.__dictionary.__iter__()

    def __repr__(self) -> str:
        """ Return repr(self). """
        return self.__dictionary.__repr__()

    def __sizeof__(self) -> int:
        """ D.__sizeof__() -> size of D in memory, in bytes """
        return self.__dictionary.__sizeof__()

    def __len__(self) -> int:
        """ Return len(self). """
        return self.__dictionary.__len__()

    def __eq__(self, o: Dict) -> bool:
        """ Return self==value. """
        if isinstance(o, MapInfo):
            if self is o:
                # same object
                return True
            o = o.dictionary
        # check inner map
        return self.__dictionary.__eq__(o)

    def __ne__(self, o: Dict) -> bool:
        """ Return self!=value. """
        if isinstance(o, MapInfo):
            if self is o:
                # same object
                return False
            o = o.dictionary
        # check inner map
        return self.__dictionary.__ne__(o)
