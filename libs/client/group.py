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

from typing import Optional, List

from dimples import ID, Meta, Document, Bulletin
from dimples import GroupDataSource
from dimples import InstantMessage, ReliableMessage
from dimples import CommonFacebook, CommonMessenger
from dimples import GroupDelegate, GroupEmitter, GroupManager, AdminManager

from ..utils import Singleton, Logging
from ..utils import find


@Singleton
class SharedGroupManager(GroupDataSource, Logging):

    def __init__(self):
        super().__init__()
        self.__facebook = None
        self.__messenger = None
        # delegates
        self.__delegate = None
        self.__emitter = None
        self.__manager = None
        self.__admin = None

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @facebook.setter
    def facebook(self, barrack: CommonFacebook):
        self.__facebook = barrack

    @property
    def messenger(self) -> CommonMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = transceiver

    #
    #   delegates
    #

    @property  # private
    def delegate(self) -> GroupDelegate:
        ds = self.__delegate
        if ds is None:
            self.__delegate = ds = GroupDelegate(facebook=self.facebook, messenger=self.messenger)
        return ds

    @property  # private
    def manager(self) -> GroupManager:
        delegate = self.__manager
        if delegate is None:
            self.__manager = delegate = GroupManager(delegate=self.delegate)
        return delegate

    @property  # private
    def admin(self) -> AdminManager:
        delegate = self.__admin
        if delegate is None:
            self.__admin = delegate = AdminManager(delegate=self.delegate)
        return delegate

    @property  # private
    def emitter(self) -> GroupEmitter:
        delegate = self.__emitter
        if delegate is None:
            self.__emitter = delegate = GroupEmitter(delegate=self.delegate)
        return delegate

    def build_group_name(self, members: List[ID]) -> str:
        delegate = self.delegate
        return delegate.build_group_name(members=members)

    #
    #   Entity DataSource
    #

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        delegate = self.delegate
        return delegate.meta(identifier=identifier)

    # Override
    def documents(self, identifier: ID) -> List[Document]:
        delegate = self.delegate
        return delegate.documents(identifier=identifier)

    #
    #   Group DataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        delegate = self.delegate
        return delegate.founder(identifier=identifier)

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        delegate = self.delegate
        return delegate.owner(identifier=identifier)

    # Override
    def members(self, identifier: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.members(identifier=identifier)

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.assistants(identifier=identifier)

    def administrators(self, identifier: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.administrators(group=identifier)

    def is_owner(self, user: ID, group: ID) -> bool:
        delegate = self.delegate
        return delegate.is_owner(user=user, group=group)

    def broadcast_document(self, document: Document) -> bool:
        assert isinstance(document, Bulletin), 'group document error: %s' % document
        delegate = self.admin
        return delegate.broadcast_document(document=document)

    #
    #   Group Manage
    #

    def create_group(self, members: List[ID]) -> Optional[ID]:
        """ Create new group with members """
        delegate = self.manager
        return delegate.create_group(members=members)

    def update_administrators(self, administrators: List[ID], group: ID) -> bool:
        """ Update 'administrators' in bulletin document """
        delegate = self.admin
        return delegate.update_administrators(administrators=administrators, group=group)

    def reset_members(self, members: List[ID], group: ID) -> bool:
        """ Reset group members """
        delegate = self.manager
        return delegate.reset_members(members=members, group=group)

    def expel_members(self, members: List[ID], group: ID) -> bool:
        """ Expel members from this group """
        assert group.is_group and len(members) > 0, 'params error: %s, %s' % (group, members)
        user = self.facebook.current_user
        assert user is not None, 'failed to get current user'
        me = user.identifier
        delegate = self.delegate
        old_members = delegate.members(identifier=group)
        is_owner = delegate.is_owner(user=me, group=group)
        is_admin = delegate.is_administrator(user=me, group=group)
        # 0. check permission
        can_reset = is_owner or is_admin
        if can_reset:
            # You are the owner/admin, then
            # remove the members and 'reset' the group
            all_members = old_members.copy()
            for item in members:
                pos = find(item, all_members)
                if pos < 0:
                    self.warning(msg='member not exists: %s, group: %s' % (item, group))
                else:
                    all_members.pop(pos)
            return self.reset_members(members=all_members, group=group)
        # not an admin/owner
        raise AssertionError('Cannot expel members from group: %s' % group)

    def invite_members(self, members: List[ID], group: ID) -> bool:
        """ Invite new members to this group """
        delegate = self.manager
        return delegate.invite_members(members=members, group=group)

    def quit_group(self, group: ID) -> bool:
        """ Quit from this group """
        delegate = self.manager
        return delegate.quit_group(group=group)

    #
    #   Sending group message
    #

    def send_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        assert msg.content.group is not None, 'group message error: %s' % msg
        delegate = self.emitter
        return delegate.send_message(msg=msg, priority=priority)
