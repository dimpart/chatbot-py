# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2025 Albert Moky
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
    Reduce
    ~~~~~~

"""

from typing import List


def zigzag_reduce(array: List[List]) -> List:
    snake = []
    #
    #  check size
    #
    h = len(array)
    w = 0
    for line in array:
        s = len(line)
        if s > w:
            w = s
    n = w + h - 1
    #
    #  traverse
    #
    x = 0
    y = 0
    while x < n and y < n:
        # pick up existing item
        if y < len(array):
            line = array[y]
            if x < len(line):
                snake.append(line[x])
        # move pointers to next position
        if y == 0:
            # next slash
            y = x + 1
            x = 0
        else:
            x = x + 1
            y = y - 1
    #############################################
    #                                           #
    #   0 1 2 3                                 #
    #   4 5         =>    0 4 1 6 5 2 7 3 8 9   #
    #   6 7 8 9                                 #
    #                                           #
    #############################################
    return snake
