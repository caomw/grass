# -*- coding: utf-8 -*-

import sys
from grass.gunittest import TestCase, test


class TestSysExit(TestCase):
    # pylint: disable=R0904

    def test_something(self):
        sys.exit(1)


if __name__ == '__main__':
    test()
