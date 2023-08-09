
"""
    Chat-GPT
    ~~~~~~~~

    3.5
"""

from .http import HttpClient, HttpSession

from .token import SharedToken
from .gpt35 import SharedGPT

from .client import ChatCallback, ChatRequest  # , ChatTask, ChatTaskPool
# from .client import ChatBox, ChatBoxPool
from .client import ChatClient  # , ChatBox


__all__ = [

    'HttpClient', 'HttpSession',
    'SharedGPT',
    'SharedToken',

    'ChatCallback', 'ChatRequest',  # 'ChatTask', 'ChatTaskPool',
    # 'ChatBox', 'ChatBoxPool',
    'ChatClient',  # 'ChatBox',
]
