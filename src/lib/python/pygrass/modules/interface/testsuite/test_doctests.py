# -*- coding: utf-8 -*-
"""
Tests checkers
"""

import doctest

import grass.gunittest
import grass.gunittest.utils

import grass.pygrass.modules as gmodules


# doctest does not allow changing the base classes of test case, skip test case
# and test suite, so we need to create a new type which inherits from our class
# and contains doctest's methods
# the alternative is to copy 500 from doctest and change what is needed
# (this might be necessary anyway beacuse of the reports and stdout and stderr)
doctest.DocFileCase = type('DocFileCase',
                           (grass.gunittest.TestCase,),
                           dict(doctest.DocFileCase.__dict__))
doctest.SkipDocTestCase = type('SkipDocTestCase',
                               (grass.gunittest.TestCase,),
                               dict(doctest.SkipDocTestCase.__dict__))


def load_tests(loader, tests, ignore):
    # TODO: this must be somewhere when doctest is called, not here
    # TODO: ultimate solution is not to use _ as a buildin in lib/python
    # for now it is the only place where it works
    grass.gunittest.utils.do_doctest_gettext_workaround()
    # this should be called at some top level
    tests.addTests(doctest.DocTestSuite(gmodules.interface.flag))
    tests.addTests(doctest.DocTestSuite(gmodules.interface.module))
    tests.addTests(doctest.DocTestSuite(gmodules.interface.parameter))

    return tests


if __name__ == '__main__':
    grass.gunittest.test()
