# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Database module
    ~~~~~~~~~~~~~~~

"""

from typing import Optional, Tuple, List, Dict

from dimples import URI, DateTime
from dimples import SymmetricKey, PrivateKey, SignKey, DecryptKey
from dimples import ID, Meta, Document
from dimples import ReliableMessage
from dimples import LoginCommand, GroupCommand, ResetCommand
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples import ProviderInfo, StationInfo
from dimples.database import DbInfo
from dimples.database import PrivateKeyTable
from dimples.database import CipherKeyTable
from dimples.database import MetaTable
from dimples.database import DocumentTable
from dimples.database import GroupTable
from dimples.database import GroupHistoryTable

from ..common import Season, VideoDBI

from .t_video import SeasonTable, VideoSearchTable


class Database(AccountDBI, MessageDBI, SessionDBI, VideoDBI):

    def __init__(self, info: DbInfo):
        super().__init__()
        self.__users = []
        self.__contacts = {}
        # Entity
        self.__private_table = PrivateKeyTable(info=info)
        self.__meta_table = MetaTable(info=info)
        self.__document_table = DocumentTable(info=info)
        self.__group_table = GroupTable(info=info)
        self.__history_table = GroupHistoryTable(info=info)
        # Message
        self.__cipherkey_table = CipherKeyTable(info=info)
        # # ANS
        # self.__ans_table = AddressNameTable(info=info)
        # Video
        self.__season_table = SeasonTable(info=info)
        self.__search_table = VideoSearchTable(info=info)

    def show_info(self):
        # Entity
        self.__private_table.show_info()
        self.__meta_table.show_info()
        self.__document_table.show_info()
        self.__group_table.show_info()
        self.__history_table.show_info()
        # Message
        self.__cipherkey_table.show_info()
        # # ANS
        # self.__ans_table.show_info()
        # Video
        self.__season_table.show_info()
        self.__search_table.show_info()

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/secret.js'
        file path: '.dim/private/{ADDRESS}/secret_keys.js'
    """

    # Override
    async def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        return await self.__private_table.save_private_key(key=key, user=user, key_type=key_type)

    # Override
    async def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        return await self.__private_table.private_keys_for_decryption(user=user)

    # Override
    async def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        return await self.__private_table.private_key_for_signature(user=user)

    # Override
    async def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        return await self.__private_table.private_key_for_visa_signature(user=user)

    """
        Meta file for entities
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
        redis key: 'mkm.meta.{ID}'
    """

    # Override
    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if not meta.match_identifier(identifier=identifier):
            raise AssertionError('meta not match ID: %s' % identifier)
        return await self.__meta_table.save_meta(meta=meta, identifier=identifier)

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        return await self.__meta_table.get_meta(identifier=identifier)

    """
        Document for Accounts
        ~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
        redis key: 'mkm.document.{ID}'
        redis key: 'mkm.docs.keys'
    """

    # Override
    async def save_document(self, document: Document) -> bool:
        # check with meta first
        meta = await self.get_meta(identifier=document.identifier)
        assert meta is not None, 'meta not exists: %s' % document
        # check document valid before saving it
        if document.valid or document.verify(public_key=meta.public_key):
            return await self.__document_table.save_document(document=document)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        return await self.__document_table.get_documents(identifier=identifier)

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
        redis key: 'mkm.user.{ID}.contacts'
    """

    # Override
    async def get_local_users(self) -> List[ID]:
        return self.__users

    # Override
    async def save_local_users(self, users: List[ID]) -> bool:
        self.__users = users
        return True

    # Override
    async def add_user(self, user: ID) -> bool:
        array = await self.get_local_users()
        if user in array:
            # self.warning(msg='user exists: %s, %s' % (user, array))
            return True
        array.insert(0, user)
        return await self.save_local_users(users=array)

    # Override
    async def remove_user(self, user: ID) -> bool:
        array = await self.get_local_users()
        if user not in array:
            # self.warning(msg='user not exists: %s, %s' % (user, array))
            return True
        array.remove(user)
        return await self.save_local_users(users=array)

    # Override
    async def current_user(self) -> Optional[ID]:
        array = await self.get_local_users()
        if len(array) > 0:
            return array[0]

    # Override
    async def set_current_user(self, user: ID) -> bool:
        array = await self.get_local_users()
        if user in array:
            index = array.index(user)
            if index == 0:
                # self.warning(msg='current user not changed: %s, %s' % (user, array))
                return True
            array.pop(index)
        array.insert(0, user)
        return await self.save_local_users(users=array)

    # Override
    async def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        self.__contacts[user] = contacts
        return True

    # Override
    async def get_contacts(self, user: ID) -> List[ID]:
        array = self.__contacts.get(user)
        if array is None:
            array = []
            self.__contacts[user] = array
        return array

    # Override
    async def add_contact(self, contact: ID, user: ID) -> bool:
        array = await self.get_contacts(user=user)
        if contact in array:
            # self.warning(msg='contact exists: %s, user: %s' % (contact, user))
            return True
        array.append(contact)
        return await self.save_contacts(contacts=array, user=user)

    # Override
    async def remove_contact(self, contact: ID, user: ID) -> bool:
        array = await self.get_contacts(user=user)
        if contact not in array:
            # self.warning(msg='contact not exists: %s, user: %s' % (contact, user))
            return True
        array.remove(contact)
        return await self.save_contacts(contacts=array, user=user)

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
        redis key: 'mkm.group.{ID}.members'
    """

    # Override
    async def get_founder(self, group: ID) -> Optional[ID]:
        return await self.__group_table.get_founder(group=group)

    # Override
    async def get_owner(self, group: ID) -> Optional[ID]:
        return await self.__group_table.get_owner(group=group)

    # Override
    async def get_members(self, group: ID) -> List[ID]:
        return await self.__group_table.get_members(group=group)

    # Override
    async def save_members(self, members: List[ID], group: ID) -> bool:
        return await self.__group_table.save_members(members=members, group=group)

    # Override
    async def get_assistants(self, group: ID) -> List[ID]:
        return await self.__group_table.get_assistants(group=group)

    # Override
    async def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        return await self.__group_table.save_assistants(assistants=assistants, group=group)

    # Override
    async def get_administrators(self, group: ID) -> List[ID]:
        return await self.__group_table.get_administrators(group=group)

    # Override
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        return await self.__group_table.save_administrators(administrators=administrators, group=group)

    #
    #   Group History DBI
    #

    # Override
    async def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        return await self.__history_table.save_group_history(group=group, content=content, message=message)

    # Override
    async def get_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        return await self.__history_table.get_group_histories(group=group)

    # Override
    async def get_reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        return await self.__history_table.get_reset_command_message(group=group)

    # Override
    async def clear_group_member_histories(self, group: ID) -> bool:
        return await self.__history_table.clear_group_member_histories(group=group)

    # Override
    async def clear_group_admin_histories(self, group: ID) -> bool:
        return await self.__history_table.clear_group_admin_histories(group=group)

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dkd.msg.{ID}.{sig}'
        redis key: 'dkd.msg.{ID}.messages'
    """

    # Override
    async def get_reliable_messages(self, receiver: ID, limit: int = 1024) -> List[ReliableMessage]:
        # TODO: get cached reliable messages
        return []

    # Override
    async def cache_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        # TODO: cache reliable messages
        return True

    # Override
    async def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        # TODO: remove sent reliable message
        return True

    """
        Message Keys
        ~~~~~~~~~~~~

        redis key: 'dkd.key.{sender}'
    """

    # Override
    async def get_cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        return await self.__cipherkey_table.get_cipher_key(sender=sender, receiver=receiver, generate=generate)

    # Override
    async def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        return await self.__cipherkey_table.cache_cipher_key(key=key, sender=sender, receiver=receiver)

    # Override
    async def get_group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        # TODO: get group keys
        pass

    # Override
    async def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        # TODO: save group keys
        pass

    # """
    #     Address Name Service
    #     ~~~~~~~~~~~~~~~~~~~~
    #
    #     file path: '.dim/ans.txt'
    #     redis key: 'dim.ans'
    # """
    #
    # async def ans_save_record(self, name: str, identifier: ID) -> bool:
    #     return await self.__ans_table.save_record(name=name, identifier=identifier)
    #
    # async def ans_record(self, name: str) -> ID:
    #     return await self.__ans_table.record(name=name)
    #
    # async def ans_names(self, identifier: ID) -> Set[str]:
    #     return await self.__ans_table.names(identifier=identifier)

    """
        Login Info
        ~~~~~~~~~~

        redis key: 'mkm.user.{ID}.login'
    """

    # Override
    async def get_login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        # TODO: get login command & messages
        return None, None

    # Override
    async def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        # TODO: save login command & messages
        return True

    #
    #   Provider DBI
    #

    # Override
    async def all_providers(self) -> List[ProviderInfo]:
        """ get list of (SP_ID, chosen) """
        return [ProviderInfo.GSP]

    # Override
    async def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        # TODO: get ISP
        return True

    # Override
    async def update_provider(self, identifier: ID, chosen: int) -> bool:
        # TODO: update ISP
        return True

    # Override
    async def remove_provider(self, identifier: ID) -> bool:
        # TODO: remove ISP
        return True

    # Override
    async def all_stations(self, provider: ID) -> List[StationInfo]:
        """ get list of (host, port, SP_ID, chosen) """
        # TODO: get stations of ISP
        return []

    # Override
    async def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID,
                          chosen: int = 0) -> bool:
        # TODO: add station for ISP
        return True

    # Override
    async def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID,
                             chosen: int = None) -> bool:
        # TODO: update station for ISP
        return True

    # Override
    async def remove_station(self, host: str, port: int, provider: ID) -> bool:
        # TODO: remove station for ISP
        return True

    # Override
    async def remove_stations(self, provider: ID) -> bool:
        # TODO: remove all stations for ISP
        return True

    #
    #   Video DBI
    #

    # Override
    async def save_season(self, season: Season, url: URI) -> bool:
        return await self.__season_table.save_season(season=season, url=url)

    # Override
    async def load_season(self, url: URI) -> Optional[Season]:
        return await self.__season_table.load_season(url=url)

    # Override
    async def save_search_results(self, results: List[URI], keywords: str) -> bool:
        return await self.__search_table.save_results(results=results, keywords=keywords)

    # Override
    async def load_search_results(self, keywords: str) -> Tuple[Optional[List[URI]], Optional[DateTime]]:
        return await self.__search_table.load_results(keywords=keywords)
