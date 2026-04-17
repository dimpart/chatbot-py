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


"""
    User Info
    ~~~~~~~~~

"""

from typing import Optional, Dict

from dimples import ID
from dimples import Visa


def get_name(visa: Visa) -> str:
    name = visa.name
    if name is None or len(name) == 0:
        did = visa.get('did')
        identifier = ID.parse(identifier=did)
        name = identifier.name
        if name is None or len(name) == 0:
            name = str(identifier.address)
    return name


def get_locale(visa: Visa) -> Optional[str]:
    app = visa.get_property(name='app')
    if isinstance(app, Dict):
        language = app.get('language')
    else:
        language = None
    sys = visa.get_property(name='sys')
    if isinstance(sys, Dict):
        locale = sys.get('locale')
    else:
        locale = None
    # OK
    if language is None:
        return locale
    elif locale is None:
        return language
    else:
        return '%s(%s)' % (language, locale)
