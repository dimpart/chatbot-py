
"""
    Chat-GPT
    ~~~~~~~~

    3.5
"""

from ..gpt.http import HttpClient, HttpSession

from .gpt35 import AIChatOS

from .client import ChatCallback, ChatRequest  # , ChatTask, ChatTaskPool
# from .client import ChatBox, ChatBoxPool
from .client import ChatClient  # , ChatBox


__all__ = [

    'HttpClient', 'HttpSession',
    'AIChatOS',

    'ChatCallback', 'ChatRequest',  # 'ChatTask', 'ChatTaskPool',
    # 'ChatBox', 'ChatBoxPool',
    'ChatClient',  # 'ChatBox',
]
