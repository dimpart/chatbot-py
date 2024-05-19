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

from typing import Optional, Tuple, Dict

from dimples import TransportableData
from dimples import EncryptKey, ID
from dimples import InstantMessage, ReliableMessage
from dimples import Envelope, Content
from dimples import TextContent, FileContent
from dimples.client import ClientMessenger

from ..utils import md5, hex_encode
from ..utils import filename_from_data
from ..utils import Singleton, Log, Logging

from .group import SharedGroupManager


@Singleton
class Emitter(Logging):

    def __init__(self):
        super().__init__()
        self.__messenger: Optional[ClientMessenger] = None
        # filename => task
        self.__outgoing: Dict[str, InstantMessage] = {}

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: ClientMessenger):
        self.__messenger = transceiver

    def _add_task(self, filename: str, msg: InstantMessage):
        self.__outgoing[filename] = msg

    def _pop_task(self, filename: str) -> Optional[InstantMessage]:
        return self.__outgoing.pop(filename, None)

    def purge(self):
        # TODO: remove expired messages in the map
        pass

    async def upload_success(self, filename: str, url: str):
        """ callback when file data uploaded to CDN and download URL responded """
        msg = self._pop_task(filename=filename)
        if msg is None:
            self.error(msg='failed to get task: %s, url: %s' % (filename, url))
            return
        self.info(msg='get task for file: %s, url: %s' % (filename, url))
        # file data uploaded to FTP server, replace it with download URL
        # and send the content to station
        content = msg.content
        assert isinstance(content, FileContent), 'file content error: %s' % content
        # content.data = None
        content.url = url
        await self._send_instant_message(msg=msg)

    async def upload_failed(self, filename: str):
        """ callback when failed to upload file data """
        msg = self._pop_task(filename=filename)
        if msg is None:
            self.error(msg='failed to get task: %s' % filename)
            return
        self.info(msg='get task for file: %s' % filename)
        # file data failed to upload, mark it error
        msg['error'] = {
            'message': 'failed to upload file'
        }
        await self._save_instant_message(msg=msg)

    async def _save_instant_message(self, msg: InstantMessage):
        # TODO: save into local storage
        pass

    async def _send_instant_message(self, msg: InstantMessage) -> Optional[ReliableMessage]:
        self.info(msg='send message (type=%d): %s -> %s' % (msg.content.type, msg.sender, msg.receiver))
        receiver = msg.receiver
        if receiver.is_group:
            # send by group manager
            g_man = SharedGroupManager()
            r_msg = await g_man.send_message(msg=msg)
        else:
            # send by shared messenger
            messenger = self.messenger
            r_msg = await messenger.send_instant_message(msg=msg, priority=1)
        # save instant message
        await self._save_instant_message(msg=msg)
        return r_msg

    async def send_content(self, content: Content, receiver: ID) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        if receiver.is_group:
            assert 'group' not in content or content.group == receiver, 'group ID error: %s, %s' % (receiver, content)
            content.group = receiver
        messenger = self.messenger
        facebook = messenger.facebook
        current = facebook.current_user
        assert current is not None, 'current user not set'
        sender = current.identifier
        # 1. pack instant message
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        muted = content.get('muted', None)
        if muted is not None:
            i_msg['muted'] = muted
        # 2. check file content
        if isinstance(content, FileContent):
            # encrypt & upload file data before send out
            if content.data is not None:  # and content.url is None:
                key = await messenger.get_encrypt_key(msg=i_msg)
                assert key is not None, 'failed to get msg key for: %s -> %s' % (i_msg.sender, i_msg.receiver)
                r_msg = await self.send_file_message(msg=i_msg, password=key)
                return i_msg, r_msg
        # 3. send
        r_msg = await self._send_instant_message(msg=i_msg)
        if r_msg is None and not i_msg.receiver.is_group:
            self.warning(msg='not send yet (type=%d): %s' % (content.type, receiver))
        return i_msg, r_msg

    #
    #   File Message
    #

    async def send_file_message(self, msg: InstantMessage, password: EncryptKey) -> Optional[ReliableMessage]:
        """
        Send file content message with password

        :param msg:      outgoing message
        :param password: key for encrypt/decrypt file data
        """
        content = msg.content
        assert isinstance(content, FileContent), 'file content error: %s' % content
        # 1. save origin file data
        data = content.data
        filename = content.filename
        assert data is not None and filename is not None, 'file content error: %s' % content
        size = await cache_file_data(data=data, filename=filename)
        if size != len(data):
            self.error(msg='failed to save file data (len=%d): %s' % (len(data), filename))
            return
        # 2. save instant message without file data
        content.data = None
        await self._save_instant_message(msg=msg)
        # 3. add upload task with encrypted data
        encrypted = password.encrypt(data=data, extra=msg.dictionary)
        filename = filename_from_data(data=encrypted, filename=filename)
        sender = msg.sender
        url = await upload_encrypted_data(data=encrypted, filename=filename, sender=sender)
        if url is None:
            # uploading in background thread
            self.info(msg='wait for uploading: %s -> %s' % (content.filename, filename))
            self._add_task(filename=filename, msg=msg)
        else:
            # uploaded before
            self.info(msg='uploaded filename: %s -> %s => %s' % (content.filename, filename, url))
            content.url = url
            return await self._send_instant_message(msg=msg)

    async def send_image_message(self, image: bytes, thumbnail: bytes, receiver: ID):
        """
        Send image message to receiver

        :param image:     image data
        :param thumbnail: image thumbnail
        :param receiver:  destination
        """
        filename = '%s.jpeg' % hex_encode(data=md5(data=image))
        ted = TransportableData.create(data=image)
        content = FileContent.image(filename=filename, data=ted)
        content['length'] = len(image)
        content.thumbnail = thumbnail
        return await self.send_content(content=content, receiver=receiver)

    async def send_text_message(self, text: str, receiver: ID):
        """
        Send text message to receiver

        :param text:     text message
        :param receiver: destination
        """
        content = TextContent.create(text=text)
        return await self.send_content(content=content, receiver=receiver)


#
#   CDN Utils
#


async def cache_file_data(data: bytes, filename: str) -> int:
    # TODO: save file data
    size = len(data)
    Log.info(msg='save file: %s, length: %d' % (filename, size))
    return size


async def upload_encrypted_data(data: bytes, filename: str, sender: ID) -> Optional[str]:
    # TODO: save file data
    size = len(data)
    Log.info(msg='upload file: %s, length: %d, sender: %s' % (filename, size, sender))
    return None
