# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT
"""Module initialization

"""

from os import sep as separator
from os.path import (
    join as path_join,
    dirname
)
BASE_CONFIG_PATH = path_join(dirname(__file__), "config", "config.yaml")
TEMPLATE_DIR_PATH = path_join(dirname(__file__), 'templates')


def template(filename):
    """Translate a file name into a full path name to a file in the
    scripts directory.

    """
    return path_join(TEMPLATE_DIR_PATH, filename)
