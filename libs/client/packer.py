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

from typing import Optional

from dimples import SymmetricKey
from dimples import InstantMessage, SecureMessage
from dimples import FileContent

from dimples.client import ClientMessagePacker

from .emitter import Emitter


class ClientPacker(ClientMessagePacker):

    # Override
    async def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # make sure visa.key exists before encrypting message
        content = msg.content
        if isinstance(content, FileContent):
            if content.get('data') is not None:  # and content.get('URL') is not None:
                key = await self.messenger.get_encrypt_key(msg=msg)
                assert key is not None, 'failed to get msg key for: %s -> %s' % (msg.sender, msg.receiver)
                # call emitter to encrypt & upload file data before send out
                await send_file_message(msg=msg, password=key)
                return None
        try:
            s_msg = await super().encrypt_message(msg=msg)
        except Exception as error:
            self.error(msg='failed to encrypt message: %s' % error)
            return None
        # receiver = msg.receiver
        # if receiver.is_group:
        #     # reuse group message keys
        #     messenger = self.messenger
        #     key = messenger.cipher_key(sender=msg.sender, receiver=receiver)
        #     key['reused'] = True
        # # TODO: reuse personal message key?
        return s_msg

    # Override
    async def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        i_msg = await super().decrypt_message(msg=msg)
        if i_msg is not None:
            content = i_msg.content
            if isinstance(content, FileContent):
                if content.password is None and content.url is not None:
                    key = await self.messenger.get_decrypt_key(msg=msg)
                    assert key is not None, 'failed to get password: %s -> %s' % (i_msg.sender, i_msg.receiver)
                    # keep password to decrypt data after downloaded
                    content.password = key
        return i_msg


async def send_file_message(msg: InstantMessage, password: SymmetricKey):
    emitter = Emitter()
    return await emitter.send_file_message(msg=msg, password=password)
