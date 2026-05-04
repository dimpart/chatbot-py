# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2026 Albert Moky
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

from typing import Set, List
from typing import Iterable

from dimples import ID
from dimples import Facebook
from dimples import CommonFacebook
from dimples.utils import Config
from dimples.utils import Supervisor


"""
    System Administrators
    ~~~~~~~~~~~~~~~~~~~~~
"""


async def get_supervisors(config: Config, facebook: Facebook, section: str = 'system') -> Set[ID]:
    """ Get system administrators """
    assert facebook is not None, 'facebook not ready'
    admin = Supervisor(facebook=facebook)
    users = await admin.get_users(config=config, section=section)
    if len(users) == 0 and section != 'system':
        users = await admin.get_users(config=config, section='system')
    return users


async def md_supervisors(config: Config, facebook: CommonFacebook, section: str = 'system',) -> str:
    """ Build markdown format name list of supervisors """
    supervisors = await get_supervisors(config=config, facebook=facebook, section=section)
    lines = await md_user_name_list(users=supervisors, facebook=facebook)
    return '\n'.join(lines)


async def md_user_name_list(users: Iterable[ID], facebook: CommonFacebook) -> List[str]:
    lines = []
    for did in users:
        name = await facebook.get_name(identifier=did)
        # if name is None or len(name) == 0:
        #     text += '* %s\n' % did
        #     continue
        text = '* "%s" - %s' % (name, did)
        lines.append(text)
    # OK
    return lines
