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
    Markdown
    ~~~~~~~~

"""

from typing import Dict

from dimples import utf8_encode, base64_encode
from dimples import Visa

from .visa import get_name


def md_esc(text: str) -> str:
    if text is None:
        return ''
    elif not isinstance(text, str):
        text = str(text)
    escape = ''
    for c in text:
        if c in _md_chars:
            escape += '\\'
        escape += c
    return escape


_md_chars = {
    '\\',
    '#', '*', '_', '-', '+',
    '~', '`',
    '|', ':', '!', '.',
    '[', ']', '(', ')',
    '<', '>', '{', '}',
    '"', "'",
}


def md_user_url(visa: Visa) -> str:
    name = get_name(visa=visa)
    text = md_user_info(visa=visa)
    href = _data_url(text=text)
    return '[%s](%s "")' % (name, href)


def md_user_info(visa: Visa) -> str:
    lines = [
        '## **%s**' % get_name(visa=visa),
        '- ID - %s' % visa.identifier,
    ]
    # avatar
    avatar = visa.get_property(name='avatar')
    if isinstance(avatar, str) and avatar.find('://') > 0:
        lines.append('')
        lines.append(
            '![](%s "")' % avatar
        )
    # app info
    app = visa.get_property(name='app')
    if isinstance(app, Dict):
        lines.append('')
        lines.append('### visa.app')
        lines.append('| Key | Value |')
        lines.append('|-----|-------|')
        for key in app:
            lines.append(
                '| %s | %s |' % (key, app[key])
            )
    # sys info
    sys = visa.get_property(name='sys')
    if isinstance(sys, Dict):
        lines.append('')
        lines.append('### visa.sys')
        lines.append('| Key | Value |')
        lines.append('|-----|-------|')
        for key in sys:
            lines.append(
                '| %s | %s |' % (key, sys[key])
            )
    return '\n'.join(lines)


def _data_url(text: str) -> str:
    base64 = base64_encode(data=utf8_encode(string=text))
    return 'data:text/plain;charset=UTF-8;base64,%s' % base64
