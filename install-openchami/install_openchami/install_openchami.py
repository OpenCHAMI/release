# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# pylint: disable=consider-using-f-string
"""Orchestrate the installation of OpenCHAMI on a single node or cluster.

"""

import sys
from getopt import (
    getopt,
    GetoptError
)

from .installer import Installer
from .error import ContextualError, ConfigError


def error(msg):
    """Produce an error message on stderr

    """
    sys.stderr.write("ERROR: %s\n" % msg)


class UsageError(Exception):  # pylint: disable=too-few-public-methods
    """Exception to report usage errors

    """


def usage(msg=None):
    """Produce a usage message on stderr
    """
    if msg:
        sys.stderr.write("%s\n" % msg)
    sys.stderr.write(USAGE_MSG)


USAGE_MSG = """
Usage: install_openchami [-p|--prep-host][-f|--files-only] [<conf-overlay> ...]
       install_openchami [-p|--prep-host] -v|--validate [<conf-overlay> ...]
       install_openchami -c|--config [<conf-overlay> ...]
       install_openchami -b|--base-config
       install_openchami -h|--help

Where:
    -b|--base-config
       displays the base configuration with comments on standard output
    -c|--config
       displays the merged configuration (without comments) on standard output
    -f|--files-only
       generates and places the files in the manifest configuration but
       does not run the OpenCHAMI installation
    -p|--prep-host
       run the installer in 'prepare-host' mode which will set up the initial
       necessary conditions for the install instead of installing OpenCHAMI.
       For validation, this skips validation steps that verify that those
       initial conditions are met, while without this option, those conditions
       would be checked.
    -v|--validate
       validates the merged configuration but does not generate files or
       install anything
    -h|--help
       displays this message

    <conf-overlay> is the path to a YAML file containing a configuration
                     overlay to be applied to the base installation
                     configuration for the OpenCHAMI system.
"""[1:]


# pylint: disable=too-many-branches, too-many-statements
def process_args(argv):
    """Split the arguments found in 'argv' into an input file and an
    output file. Use options from a config file for defaults.

    """
    action_error = (
        "requested action may only be one of "
        "'show base config' (-b, --base-config)"
        "'show config' (-c, --config) "
        "'help' (-h, --help) or "
        "'validate' (-v, --validate)"
    )
    ret_opts = {
        'operation': 'install',
        'files-only': False,
        'prep-host': False,
    }
    try:
        opts, args = getopt(
            argv, "bcfhpv", [
                'base-config',
                'config',
                'files-only',
                'help',
                'prep-host',
                'validate',
            ]
        )
    except GetoptError as err:
        raise UsageError(err) from err
    for opt in opts:
        if opt[0] in ('-h', 'help'):
            # Don't raise a usage error here because this is not an
            # error, just set the operation to 'help'
            if ret_opts['operation'] != 'install':
                raise UsageError(action_error)
            ret_opts['operation'] = 'help'
        elif opt[0] in ('-b', 'base-config'):
            if ret_opts['operation'] != 'install':
                raise UsageError(action_error)
            ret_opts['operation'] = 'show-base-config'
        elif opt[0] in ('-c', '--config'):
            if ret_opts['operation'] != 'install':
                raise UsageError(action_error)
            ret_opts['operation'] = 'show-config'
        elif opt[0] in ('-f', '--files-only'):
            ret_opts['files-only'] = True
        elif opt[0] in ('-p', '--prep-host'):
            ret_opts['prep-host'] = True
        elif opt[0] in ('-v', '--validate'):
            if ret_opts['operation'] != 'install':
                raise UsageError(action_error)
            ret_opts['operation'] = 'validate'
        else:
            # Getopt will handle any unrecognized option, so if we
            # get here, there is a recognized option that was never
            # handled.  Need to add option handling for that.
            raise UsageError(
                "INTERNAL ERROR: unprocessed option '%s'" % opt[0]
            )
    if ret_opts['files-only'] and ret_opts['operation'] != 'install':
        raise UsageError(
            "'files-only' option is only valid with the install operation"
        )
    if (
            ret_opts['prep-host'] and
            ret_opts['operation'] not in ('install', 'validate')
    ):
        raise UsageError(
            "'prep-host' option is only valid with the install or validate "
            "operation"
        )
    return ret_opts, args


def main(argv):
    """main

    """
    options, config_overlays = process_args(argv[1:])
    operation = options['operation']
    installer = Installer(options, config_overlays)

    # Okay, we know what to do and the installer is ready to do
    # it. Time to do something.
    if operation == 'install':
        installer.install()
        return 0
    if operation == 'show-base-config':
        installer.show_base_config()
        return 0
    if operation == 'show-config':
        installer.show_config()
        return 0
    if operation == 'validate':
        installer.validate()
        return 0
    if operation == 'help':
        usage()
        return 0
    raise ContextualError(
        "INTERNAL ERROR: unrecognized operation specified: '%s'" % operation
    )


def entrypoint(argv):
    """Entrypoint function to handle exceptions from main and turn them
    into return codes and error reports that will, eventually, become
    exit status.

    """
    try:
        return main(argv)
    except UsageError as err:
        usage(err)
        return 1
    except ContextualError as err:
        error(err)
        return 1
    except ConfigError as err:
        error("CONFIGURATION ERROR: %s" % str(err))
        return 1
    except KeyboardInterrupt:
        return 1
    return 0


def entry():
    """Command entrypoint

    """
    entrypoint(sys.argv)


# Start here
if __name__ == "__main__":               # pragma no unit test
    sys.exit(entrypoint(sys.argv[1:]))   # pragma no unit test
