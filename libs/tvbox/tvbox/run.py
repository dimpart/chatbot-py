# -*- coding: utf-8 -*-
#
#   TV-Box
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
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

"""
    TV Box Scanner
    ~~~~~~~~~~~~~~

"""

import getopt
import os
import sys

path = os.path.abspath(__file__)
path = os.path.dirname(path)
path = os.path.dirname(path)
sys.path.insert(0, path)

from tvbox.utils import Log
from tvbox.utils import AsyncRunner as Runner
from tvbox.config import LiveConfig
from tvbox.source import LiveHandler
from tvbox.loader import LiveLoader
from tvbox.scanner import ScanContext


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/tvbox/config.json'


def show_help():
    cmd = sys.argv[0]
    print('')
    print('    TV Box Scanner')
    print('')
    print('usages:')
    print('    %s [--config=<FILE>] scan lives' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('actions:')
    print('    scan lives      scan for live stream sources')
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % DEFAULT_CONFIG)
    print('    --help, -h      show this help message and exit')
    print('')


async def async_main():
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help()
        sys.exit(1)
    # check options
    config_file = None
    for opt, arg in opts:
        if opt == '--config':
            config_file = arg
        else:
            show_help()
            sys.exit(0)
    # check config file path
    if config_file is None:
        config_file = DEFAULT_CONFIG
    if not os.path.exists(config_file):
        show_help()
        Log.error(msg='config file not exists: %s' % config_file)
        sys.exit(0)
    # load config
    config = await LiveConfig.load(path=config_file)
    # initializing
    Log.info(msg='!!!')
    Log.info(msg='!!! Init with config: %s => %s' % (config_file, config))
    Log.info(msg='!!!')
    loader = LiveLoader(config=config)
    await loader.load(handler=LiveHandler(config=config),
                      context=ScanContext(timeout=64))
    Log.info(msg='!!!')
    Log.info(msg='!!! Mission Accomplished.')
    Log.info(msg='!!!')


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
