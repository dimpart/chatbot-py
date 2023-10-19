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

from typing import Optional, Tuple, List

from dimples import SymmetricKey
from dimples import ID, Meta, Document, Bulletin
from dimples import GroupDataSource
from dimples import Content, FileContent
from dimples import InstantMessage, ReliableMessage
from dimples import CommonFacebook, CommonMessenger
from dimples import GroupDelegate, GroupEmitter, GroupManager, AdminManager

from ..utils import Singleton


@Singleton
class SharedGroupManager(GroupDataSource):

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

    @property
    def delegate(self) -> GroupDelegate:
        ds = self.__delegate
        if ds is None:
            self.__delegate = ds = GroupDelegate(facebook=self.facebook, messenger=self.messenger)
        return ds

    @property
    def emitter(self) -> GroupEmitter:
        delegate = self.__emitter
        if delegate is None:
            self.__emitter = delegate = _GroupEmitter(delegate=self.delegate)
        return delegate

    @property
    def manager(self) -> GroupManager:
        delegate = self.__manager
        if delegate is None:
            self.__manager = delegate = GroupManager(delegate=self.delegate)
        return delegate

    @property
    def admin(self) -> AdminManager:
        delegate = self.__admin
        if delegate is None:
            self.__admin = delegate = AdminManager(delegate=self.delegate)
        return delegate

    #
    #   Entity DataSource
    #

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.delegate.meta(identifier=identifier)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        return self.delegate.document(identifier=identifier, doc_type=doc_type)

    #
    #   Group DataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        return self.delegate.founder(identifier=identifier)

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        return self.delegate.owner(identifier=identifier)

    # Override
    def members(self, identifier: ID) -> List[ID]:
        return self.delegate.members(identifier=identifier)

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        return self.delegate.assistants(identifier=identifier)

    def administrators(self, identifier: ID) -> List[ID]:
        return self.delegate.administrators(group=identifier)

    def is_owner(self, user: ID, group: ID) -> bool:
        return self.delegate.is_owner(user=user, group=group)

    def broadcast_document(self, document: Document) -> bool:
        assert isinstance(document, Bulletin), 'group document error: %s' % document
        return self.admin.broadcast_document(document=document)

    #
    #   Group Manage
    #

    def create_group(self, members: List[ID]) -> Optional[ID]:
        """ Create new group with members """
        return self.manager.create_group(members=members)

    def update_administrators(self, administrators: List[ID], group: ID) -> bool:
        """ Update 'administrators' in bulletin document """
        return self.admin.update_administrators(administrators=administrators, group=group)

    def reset_members(self, members: List[ID], group: ID) -> bool:
        """ Reset group members """
        return self.manager.reset_members(members=members, group=group)

    def expel_members(self, members: List[ID], group: ID) -> bool:
        """ Expel members from this group """
        pass

    def invite_members(self, members: List[ID], group: ID) -> bool:
        """ Invite new members to this group """
        return self.manager.invite_members(members=members, group=group)

    def quit_group(self, group: ID) -> bool:
        """ Quit from this group """
        return self.manager.quit_group(group=group)

    #
    #   Sending group message
    #

    def send_content(self, content: Content, group: ID,
                     priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        content.group = group
        return self.emitter.send_content(content=content, priority=priority)


class _GroupEmitter(GroupEmitter):

    # Override
    def _upload_file_data(self, content: FileContent, password: SymmetricKey, sender: ID) -> bool:
        # TODO: encrypt & upload file data
        pass
