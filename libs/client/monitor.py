# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

import threading
from typing import Optional, ValuesView, List

from dimples.utils import Config
from dimples import DateTime
from dimples import ID
from dimples import TextContent

from ..utils import Runner
from ..utils import Singleton
from ..utils import Log, Logging
from .emitter import Emitter


class Bottle:
    """ Container for Agent """

    def __init__(self, agent: str):
        super().__init__()
        self.__agent = agent
        self.__success = 0
        self.__failure = 0

    @property
    def agent(self) -> str:
        """ bottle name """
        return self.__agent

    @property
    def success(self) -> int:
        """ success count """
        return self.__success

    @property
    def failure(self) -> int:
        """ failure count """
        return self.__failure

    # Override
    def __str__(self) -> str:
        return '<%s success=%d failure=%d />' % (self.agent, self.success, self.failure)

    # Override
    def __repr__(self) -> str:
        return '<%s success=%d failure=%d />' % (self.agent, self.success, self.failure)

    def increase_success(self):
        self.__success += 1

    def increase_failure(self):
        self.__failure += 1


class Barrel:
    """ Container for Service """

    def __init__(self, service: str):
        super().__init__()
        self.__service = service
        self.__bottles = {}  # agent -> Bottle
        self.__time = DateTime.now()
        self.__success = 0
        self.__crash = 0

    @property
    def service(self) -> str:
        """ barrel name """
        return self.__service

    @property
    def bottles(self) -> ValuesView[Bottle]:
        return self.__bottles.values()

    @property
    def time(self) -> DateTime:
        """ start time """
        return self.__time

    @property
    def success(self) -> int:
        return self.__success

    @property
    def crash(self) -> int:
        return self.__crash

    # Override
    def __str__(self) -> str:
        cnt = len(self.__bottles)
        return '<%s bottles=%d success=%d crash=%d />' % (self.service, cnt, self.success, self.crash)

    # Override
    def __repr__(self) -> str:
        cnt = len(self.__bottles)
        return '<%s bottles=%d success=%d crash=%d />' % (self.service, cnt, self.success, self.crash)

    def increase_failure(self, agent: str):
        bottle = self.__bottles.get(agent)
        if bottle is None:
            bottle = Bottle(agent=agent)
            self.__bottles[agent] = bottle
        bottle.increase_failure()

    def increase_success(self, agent: str):
        bottle = self.__bottles.get(agent)
        if bottle is None:
            bottle = Bottle(agent=agent)
            self.__bottles[agent] = bottle
        bottle.increase_success()
        self.__success += 1

    def increase_crash(self):
        self.__crash += 1


@Singleton
class Monitor(Runner, Logging):

    TIME_INTERVAL = 3600  # seconds

    def __init__(self):
        super().__init__(interval=60)
        self.__barrels = {}  # service -> Barrel
        self.__lock = threading.Lock()
        self.__config = None
        # start ticking
        self.__report_time = None
        # auto start
        self.start()

    @property
    def config(self) -> Optional[Config]:
        return self.__config

    @config.setter
    def config(self, conf: Config):
        self.__config = conf

    def _update_report_time(self):
        if self.__report_time is None:
            self.__report_time = DateTime.current_timestamp() + self.TIME_INTERVAL

    def _check_report_time(self) -> Optional[DateTime]:
        with self.__lock:
            report_time = self.__report_time
            if report_time is not None:
                # check report time
                now = DateTime.now()
                if now >= report_time:
                    # clear report time
                    self.__report_time = None
                    return now
                # waiting for report time

    def report_success(self, service: str, agent: str):
        with self.__lock:
            barrel = self.__barrels.get(service)
            if barrel is None:
                barrel = Barrel(service=service)
                self.__barrels[service] = barrel
            barrel.increase_success(agent=agent)
            self._update_report_time()

    def report_failure(self, service: str, agent: str):
        with self.__lock:
            barrel = self.__barrels.get(service)
            if barrel is None:
                barrel = Barrel(service=service)
                self.__barrels[service] = barrel
            barrel.increase_failure(agent=agent)
            self._update_report_time()

    def report_crash(self, service: str):
        with self.__lock:
            barrel = self.__barrels.get(service)
            if barrel is None:
                barrel = Barrel(service=service)
                self.__barrels[service] = barrel
            barrel.increase_crash()
            self._update_report_time()

    def _get_barrels(self) -> ValuesView[Barrel]:
        with self.__lock:
            barrels = self.__barrels
            self.__barrels = {}
            return barrels.values()

    def _get_supervisors(self) -> List[ID]:
        config = self.config
        if config is None:
            self.error(msg='failed to get config')
            return []
        supervisors = config.get_list(section='admin', option='supervisors')
        return ID.convert(array=supervisors)

    def start(self):
        thr = Runner.async_thread(coro=self.run())
        thr.start()

    # Override
    async def process(self) -> bool:
        now = self._check_report_time()
        if now is None:
            return False
        # check admins
        admins = self._get_supervisors()
        barrels = self._get_barrels()
        self.info(msg='reporting %d service(s) to supervisor: %s' % (len(barrels), admins))
        # try to report one by one
        for bar in barrels:
            try:
                await _report(barrel=bar, now=now, supervisors=admins)
            except Exception as error:
                self.error(msg='failed to report barrel: %s, error: %s' % (bar, error))
        return False


async def _report(barrel: Barrel, now: DateTime, supervisors: List[ID]):
    # build report
    text = '[%s] -> [%s]\n' % (barrel.time, now)
    text += '## **%s**:\n' % barrel.service
    bottles = barrel.bottles
    for bot in bottles:
        text += '- **%s** - success: %d, failure: %d\n' % (bot.agent, bot.success, bot.failure)
    text += '\n'
    text += 'Totaling success: **%d**, crash: **%d**' % (barrel.success, barrel.crash)
    # respond
    content = TextContent.create(text=text)
    content['format'] = 'markdown'
    emitter = Emitter()
    for receiver in supervisors:
        Log.info(msg='[Monitor] sending report to supervisor: %s, %s' % (receiver, text))
        await emitter.send_content(content=content, receiver=receiver)
