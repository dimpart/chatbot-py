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
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # make sure visa.key exists before encrypting message
        content = msg.content
        if isinstance(content, FileContent):
            if content.get('data') is not None:  # and content.get('URL') is not None:
                sender = msg.sender
                receiver = msg.receiver
                messenger = self.messenger
                key = messenger.cipher_key(sender=sender, receiver=receiver, generate=True)
                assert key is not None, 'failed to get msg key for: %s -> %s' % (sender, receiver)
                # call emitter to encrypt & upload file data before send out
                send_file_message(msg=msg, password=key)
                return None
        try:
            s_msg = super().encrypt_message(msg=msg)
        except Exception as error:
            self.error(msg='failed to encrypt message: %s' % error)
            return None
        receiver = msg.receiver
        if receiver.is_group:
            # reuse group message keys
            messenger = self.messenger
            key = messenger.cipher_key(sender=msg.sender, receiver=receiver)
            key['reused'] = True
        # TODO: reuse personal message key?
        return s_msg

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        i_msg = super().decrypt_message(msg=msg)
        if i_msg is not None:
            content = i_msg.content
            if isinstance(content, FileContent):
                if content.get('data') is None and content.get('URL') is not None:
                    sender = i_msg.sender
                    receiver = i_msg.receiver
                    messenger = self.messenger
                    key = messenger.cipher_key(sender=sender, receiver=receiver)
                    assert key is not None, 'failed to get password: %s -> %s' % (sender, receiver)
                    # keep password to decrypt data after downloaded
                    content.password = key
        return i_msg


def send_file_message(msg: InstantMessage, password: SymmetricKey):
    emitter = Emitter()
    emitter.send_file_message(msg=msg, password=password)
