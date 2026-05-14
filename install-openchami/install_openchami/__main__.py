# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT
"""Module entrypoint for the OpenCHAMI Installer

"""
import sys
from .install_openchami import entrypoint

# Start here
if __name__ == "__main__":           # pragma no unit test
    sys.exit(entrypoint(sys.argv))   # pragma no unit test
