# SPDX-FileCopyrightText: (C) Copyright 2024-2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT
""" Nox definitations for tests, docs, and linting
"""
from __future__ import absolute_import
import os

import nox  # pylint: disable=import-error


COVERAGE_FAIL = 95

PYTHON = ['3']

@nox.session(python=PYTHON)
def lint(session):
    """Run linters.
    Returns a failure if the linters find linting errors or sufficiently
    serious code quality issues.
    """
    run_cmd = [
        'pylint',
        'install_openchami',
    ]
    if session.python:
        session.install('.[lint]')
    session.run(*run_cmd)


@nox.session(python=PYTHON)
def style(session):
    """Run code style checker.
    Returns a failure if the style checker fails.
    """
    run_cmd = [
        'pycodestyle',
        '--config=.pycodestyle',
        'install_openchami',
    ]
 
    if session.python:
        session.install('.[style]')
    session.run(*run_cmd)


@nox.session(python=PYTHON)
def tests(session):
    """Default unit test session.
    """
    # Install all test dependencies, then install this package in-place.
    path = 'tests'
    if session.python:
        session.install('.[test]')

    # XXX - disable tests until we have some...
    session.run('/usr/bin/true', external=True)
#    # Run py.test against the tests.
#    session.run(
#        'py.test',
#        '--quiet',
#        '-W',
#        'ignore::DeprecationWarning',
#        '--cov=install_openchami',
#        '--cov=tests',
#        '--cov-append',
#        '--cov-config=.coveragerc',
#        '--cov-report=',
#        '--cov-fail-under={}'.format(COVERAGE_FAIL),
#        os.path.join(path),
#        env={}
#    )



@nox.session(python=PYTHON)
def cover(session):
    """Run the final coverage report.
    This outputs the coverage report aggregating coverage from the unit
    test runs, and then erases coverage data.
    """
    if session.python:
        session.install('.[cover]')
    # Disable coverage tests until we have some...
    session.run('/usr/bin/true', external=True)
#    session.run('coverage', 'report', '--show-missing',
#                '--fail-under={}'.format(COVERAGE_FAIL))
#    session.run('coverage', 'erase')
