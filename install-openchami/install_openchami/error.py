# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# pylint: disable=consider-using-f-string
"""Exception classes to support the OpenCHAMI installer

"""
# pylint: disable=unused-import
from vtds_base import ContextualError  # Pass this along to importers


class ConfigError(Exception):  # pylint: disable=too-few-public-methods
    """Exception to specifically report errors in validation of
    configuration.

    """
