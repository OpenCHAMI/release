# SPDX-FileCopyrightText: (C) Copyright 2026 OpenCHAMI a Series of LF Projects, LLC
# SPDX-License-Identifier: MIT

# pylint: disable=consider-using-f-string
"""The home of the Config class that holds, validates and prepares the
configuration for OpenCHAMI installation.

"""


import sys
from json import dumps as json_dumps
from tempfile import NamedTemporaryFile
from os.path import (
    sep as path_separator,
    join as path_join,
)
from os import (
    makedirs,
    chown,
    chmod
)
import re
from grp import getgrnam
from pwd import getpwnam
from pathlib import Path
from random import randint

from yaml import (
    SafeDumper,
    YAMLError,
    dump as yaml_dumps,
    safe_load,
)
from passlib.pwd import genword as generate_password
from vtds_base import (
    merge_configs,
    render_template_file,
)

from . import (
    template,
    BASE_CONFIG_PATH
)
from .error import ContextualError, ConfigError


# Create a custom representer for yaml SafeDumper to dump multiline strings
# using the '|' notation and multiline string output properly indented
def __representer_strings_multiline(dumper, data):
    """String representer for yaml that dumps multiline strings using
    pipe notation.

    """
    if '\n' in data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style="|"
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Create a yaml SafeDumper class that uses '|' notation for multiline
# strings
class MultilineStringSafeDumper(SafeDumper):
    """Safe Dumper Class for multiline strings so that when I register
    my representer I don't corrupt the standard SafeDumper

    """


# Register the multiline string representer with the custom safe dumper
MultilineStringSafeDumper.add_representer(
    str, __representer_strings_multiline
)


class Config:
    """The OpenCHAMI configuration class that holds, validates and
    prepares the configuration for OpenCHAMI installation.

    """
    def __init__(self, options, config_overlays):
        """Construct the installer instance using the config overlays
        and options provided from the caller.

        """
        self.config_overlays = [BASE_CONFIG_PATH] + config_overlays
        self.options = options
        self.config = None

    def load_config(self):
        """Read in the configuration and attach it to this object

        """
        overlays = []
        for overlay_path in self.config_overlays:
            try:
                with open(overlay_path, 'r', encoding='UTF-8') as config_file:
                    overlays.append(safe_load(config_file))
            except OSError as err:
                raise ContextualError(
                    "cannot open config_overlay file '%s' - %s" % (
                        overlay_path, str(err)
                    )
                ) from err
            except YAMLError as err:
                raise ContextualError(
                    "error parsing config overlay file '%s' - %s" % (
                        overlay_path, str(err)
                    )
                ) from err
        self.config = overlays[0]
        for overlay in overlays[1:]:
            self.config = merge_configs(self.config, overlay)

    def config_by_path(self, config_path, **kwargs):
        """Look up a configuration item using its dotted path
        notation, for example, 'hosting_config.cluster_name', and
        return what is found there. The caller can supply an explicit
        keyword argument of 'default' which provides a value to return
        if nothing is found at the final element of the path (all
        preceding elements must still exist). If the 'default' value
        is not provided, config_by_path raises a ConfigError
        exception.

        """
        have_default = 'default' in kwargs
        default = kwargs.get('default', None)
        elements = config_path.split('.')
        tmp_path = ""
        found = self.config
        for element in elements:
            tmp_path += element
            if not isinstance(found, dict) or element not in found:
                if have_default and len(elements) == len(tmp_path.split('.')):
                    # We have reached the end of the path and the last
                    # item is missing. The caller said missing was okay,
                    # so just return None
                    return default
                # Could not find this element and either no default was
                # provided, or we have not reached the end of the path so
                # it is a parent item that is missing. Raise a
                # ConfigError.
                raise ConfigError(
                    "unable to resolve path '%s' in configuration" % tmp_path
                )
            found = found[element]
            tmp_path += '.'
        return found

    def find_annotated_files(self, annotation):
        """Find the list of manifest files with a specific annotation and
        return the list fully resolved target paths.

        """
        manifest_files = self.config_by_path('manifest.files')
        # Get all the target paths
        found = [
            manifest_file['target']
            for manifest_file in manifest_files.values()
            if annotation in manifest_file.get('annotations', [])
        ]
        # Fix the ones that are not absolute
        deploy_dir = self.config_by_path('manifest.deployment_directory')
        found = [
            path_join(deploy_dir, path) if path[0] != path_separator else path
            for path in found
        ]
        return found

    def dump_yaml(self, config_path=None):
        """Dump the configuration found at 'config_path' to a YAML
        string

        """
        data = self.config_by_path(config_path) if config_path else self.config
        return yaml_dumps(
            data,
            Dumper=MultilineStringSafeDumper,
            default_flow_style=False, sort_keys=False, indent=2
        )

    def dump_json(self, config_path):
        """Dump the configuration found at 'config_path' to a JSON
        string

        """
        return json_dumps(self.config_by_path(config_path), indent=2)

    def __render_manifest_file(self, manifest_file):
        """Render the file described in 'manifest_file'.

        """
        template_name = manifest_file.get('template_name', None)
        target = manifest_file['target']
        if target[0] != path_separator:
            # This is a relative pathname, prepend the configured deployment
            # directory to it to make it absolute.
            deploy_dir = self.config_by_path('manifest.deployment_directory')
            target = path_join(deploy_dir, target)
        # Create an empty 'target' file and set its ownership and access
        # so that it is protected from the start.
        deploy_uid = self.config_by_path('manifest.deployment_user.uid')
        deploy_gid = self.config_by_path('manifest.deployment_user.gid')
        file_uid = manifest_file.get('uid', None)
        file_gid = manifest_file.get('gid', None)
        uid = file_uid if file_uid is not None else deploy_uid
        gid = file_gid if file_gid is not None else deploy_gid
        mode = int(manifest_file['mode'], base=8)
        make_dir = manifest_file.get('mkdir', False)
        if make_dir:
            target_dir = str(Path(target).parent)
            try:
                makedirs(target_dir, mode=0o755, exist_ok=True)
                chown(target_dir, uid, gid)
            except OSError as err:
                raise ContextualError(
                    "unable to make directory path '%s' - %s" % (
                        target_dir, err
                    )
                ) from err
        try:
            with open(target, "w", encoding='UTF-8'):
                # don't really need to do this with the file open, but we did
                # need to create the file, so this makes a good thing to do in
                # the 'with ...' block, why not?
                chown(target, uid, gid)
                chmod(target, mode)
        except OSError as err:
            raise ContextualError(
                "unable to create manifest target file  '%s' - %s" % (
                    target, err
                )
            ) from err
        # Now we are ready to render the file safely
        if template_name is None:
            # What were are doing here is finding the configuration from
            # which to write out the template file by the configuration
            # path specified in the manifest item's generation parameters,
            # hence the weird indirection.
            file_template_path = manifest_file['generation']['config_path']
            with NamedTemporaryFile(mode='w+', encoding='UTF-8') as tmp_file:
                template_file = tmp_file.name
                if manifest_file['generation']['type'] == 'yaml':
                    tmp_file.write(self.dump_yaml(file_template_path))
                else:
                    tmp_file.write(self.dump_json(file_template_path))
                tmp_file.flush()
                tmp_file.seek(0)
                render_template_file(template_file, self.config, target)
        else:
            render_template_file(template(template_name), self.config, target)

    def render_manifest(self, annotations=None):
        """Use Jinj2 to render all of the files in a supplied manifest to
        their specified destinations providing 'config' as the templating
        data. If 'annotations' are provided only the files that have one
        or more of the provided annotations are rendered. If 'annotations'
        are not provided or None, all files are rendered.

        """
        manifest_files = self.config_by_path('manifest.files')
        for manifest_file in manifest_files.values():
            if annotations:
                # Annotations were specified, see if this file matches any
                file_annotations = manifest_file.get('annotations', [])
                matches = [
                    file_annotation
                    for file_annotation in file_annotations
                    if file_annotation in annotations
                ]
                if not matches:
                    # No matching annotations, skip this file
                    continue
            self.__render_manifest_file(manifest_file)

    def __prep_manifest_file(self, file_key):
        """Prepare the pieces of the manifest file configuration that
        need to be resolved at run time.

        """
        # Stash an owning UID and GID in the file manifest if there is an owner
        file_manifest = self.config_by_path('manifest.files.%s' % file_key)
        owner = self.config_by_path(
            'manifest.files.%s.owner' % file_key, default=None
        )
        if owner is not None:
            file_manifest['uid'] = getpwnam(owner).pw_uid
        group = self.config_by_path(
            'manifest.files.%s.group' % file_key, default=None
        )
        if group is not None:
            file_manifest['gid'] = getgrnam(group).gr_gid

    def __prep_manifest(self):
        """Prepare the contents of the manifest portion of the
        configuration

        """
        # Set up the user id and primary group id of the deployment user
        deploy_user = self.config_by_path('manifest.deployment_user')
        username = self.config_by_path('manifest.deployment_user.username')
        prep_host = self.options.get('prep-host', False)
        if not prep_host:
            # Validation already checked, so the user exists
            user_info = getpwnam(username)
            deploy_user['uid'] = user_info.pw_uid
            deploy_user['gid'] = user_info.pw_gid
            deploy_dir = self.config_by_path('manifest.deployment_directory')
            makedirs(deploy_dir, mode=0o755, exist_ok=True)
            chown(deploy_dir, deploy_user['uid'], deploy_user['gid'])
        annotations = (
            ['host-prep-entrypoint', 'host-prep-support'] if prep_host
            else []
        )
        manifest_files = self.config_by_path('manifest.files')
        for file_key, manifest_file in manifest_files.items():
            file_annotations = manifest_file.get('annotations', [])
            matches = [
                file_annotation
                for file_annotation in file_annotations
                if file_annotation in annotations
            ]
            if annotations and not matches:
                # No matching annotations, skip this file
                continue
            self.__prep_manifest_file(file_key)

    @staticmethod
    def __random_mac(prefix=None):
        """Generate a MAC address using a specified prefix specified
        as a string containing colon separated hexadecimal octet
        values for the length of the desired prefix. By default use
        the KVM reserved, locally administered, unicast prefix
        '52:54:00'.

        """
        prefix = prefix if prefix is not None else "52:54:00"
        try:
            prefix_octets = [
                int(octet, base=16) for octet in prefix.split(':')
            ]
        except Exception as err:
            raise ContextualError(
                "internal error: parsing MAC prefix '%s' failed - %s" % (
                    prefix, str(err)
                )
            ) from err
        if len(prefix_octets) > 6:
            raise ContextualError(
                "internal error: MAC address prefix '%s' has too "
                "many octets" % prefix
            )
        mac_binary = prefix_octets + [
            randint(0x00, 0xff) for i in range(0, 6 - len(prefix_octets))
        ]
        return ":".join(["%2.2x" % octet for octet in mac_binary])

    def __prep_bmcs(self):
        """Prepare the configuration of BMCs

        """
        # Run through the BMCs and generate redfish passwords for the
        # ones that don't have one explicitly set.
        bmcs = self.config_by_path('bmcs')
        for bmc in bmcs.values():
            if bmc['network'].get('redfish_password', None) is None:
                bmc['network']['redfish_password'] = generate_password(
                    length=20
                )
            if bmc['network'].get('mac', None) is None:
                bmc['network']['mac'] = self.__random_mac()

    def __prep_hosting(self):
        """Prepare the hosting configuration

        """
        # nothing to do, just return

    def __prep_nodes(self):
        """Prepare the 'nodes' section of the config

        """
        # nothing to do, just return

    def __prep_images(self):
        """Prepare the 'images' section of the config

        """
        # Nothing to do, just return

    def prepare(self):
        """Prepare the Installer to install the system by reading in
        the configuration, merging the overlays onto the
        configuration, and generating any configuration data that need
        to be generated.

        """
        self.__prep_manifest()
        self.__prep_bmcs()
        self.__prep_hosting()
        self.__prep_nodes()
        self.__prep_images()
        return 0

    def __check_and_get_dict_key(
            self, key, dictionary, value_type, none_ok=False
    ):
        """Validate and return the contents of a path in the
        configuration, checking that the path exists and has the
        correct type.

        """
        if key not in dictionary:
            if none_ok:
                return None
            raise ConfigError("key '%s' not found" % key)
        if not isinstance(dictionary[key], value_type):
            raise ConfigError(
                "key '%s' is a %s and should be a %s" % (
                    key, str(type(dictionary[key])), str(value_type)
                )
            )
        return dictionary[key]

    def __check_and_get_config_path(
            self, config_path, value_type, none_ok=False
    ):
        """Validate and return the contents of a path in the
        configuration, checking that the path exists and has the
        correct type.

        """
        value = self.config_by_path(config_path)
        if value is None and none_ok:
            return value
        if not isinstance(value, value_type):
            raise ConfigError(
                "'%s' has a value of type '%s' and should have a value of "
                "type '%s'" % (
                    config_path, str(type(value)), str(value_type)
                )
            )
        return value

    def __valid_manifest_deploy_dir(self):
        """Make sure the 'deployment_directory' field of the manifest
        is specified, is a string and looks like it might be an
        absolute pathname

        """
        deployment_directory = self.__check_and_get_config_path(
            'manifest.deployment_directory', str
        )
        if deployment_directory[0] != path_separator:
            raise ConfigError(
                "'manifest.deployment_directory' value '%s' is not an "
                "absolute pathname"
            )

    def __valid_manifest_deploy_user(self):
        """Validate the 'deployment_user' section of the manifest

        """
        self.__check_and_get_config_path(
            'manifest.deployment_user', dict
        )
        username = self.__check_and_get_config_path(
            'manifest.deployment_user.username', str
        )
        primary_group = self.__check_and_get_config_path(
            'manifest.deployment_user.primary_group', str
        )
        supplementary_groups = self.__check_and_get_config_path(
            'manifest.deployment_user.supplementary_groups', list
        )
        for group in supplementary_groups:
            if not isinstance(str, group):
                raise ConfigError(
                    "supplementary group '%s' in "
                    "'manifest.deployment_user.supplmentary_groups "
                    "should be a string but is of type '%s'" % (
                        str(group), str(type(group))
                    )
                )
        if not self.options['prep-host']:
            try:
                user_info = getpwnam(username)
            except KeyError as err:
                raise ConfigError(
                    "'manifest.deployment_user.username' user '%s' is not "
                    "provisioned as a user on this host "
                    "try running installer in 'prep-host' mode "
                    "before installing OpenCHAMI" % username
                ) from err
            try:
                primary_info = getgrnam(primary_group)
            except KeyError as err:
                raise ContextualError(
                    "error looking up deployment user primary "
                    "group '%s' (try running installer in 'prep-host' "
                    "mode before installing OpenCHAMI) - %s" % (
                        primary_group, str(err)
                    )
                ) from err
            try:
                supplementary_info = [
                    getgrnam(group)
                    for group in supplementary_groups
                ]
            except KeyError as err:
                raise ContextualError(
                    "error looking up deployment user supplmentary "
                    "groups (try running installer in 'prep-host' "
                    "mode before installing OpenCHAMI) - %s" % str(err)
                ) from err
            if user_info.pw_gid != primary_info.gr_gid:
                raise ConfigError(
                    "deployment user '%s' does not have group '%s' as "
                    "its primary group try running installer in 'prep-host' "
                    "mode before installing OpenCHAMI" % (
                        username,
                        primary_group
                    )
                )
            for group_info in supplementary_info:
                if username not in group_info.gr_mem:
                    raise ConfigError(
                        "user '%s' is not a member of group '%s' as a "
                        "supplementary group try running installer in "
                        "'prep-host' mode before installing OpenCHAMI" % (
                            username,
                            group_info.gr_name
                        )
                    )

    def __valid_manifest_file_gen(self, file_key):
        """For generated manifest file items (items that have no
        template specified) validate the manifest contents with
        respect to generation parameters.

        """
        config_path = self.__check_and_get_config_path(
            "manifest.files.%s.generation.config_path" % file_key, str
        )
        # Make sure that the configuration path from which the
        # template file will be composed is, in fact, present and a
        # dictionary.
        self.__check_and_get_config_path(config_path, dict)

        # Make sure the generation type is either YAML or JSON
        gen_type = self.__check_and_get_config_path(
            "manifest.files.%s.generation.type" % file_key, str
        )
        if gen_type not in ('yaml', 'json'):
            raise ConfigError(
                "'manifest.files.%s.generation.type' is '%s' but must "
                "be either 'yaml' or 'json'" % (file_key, gen_type)
            )

    def __valid_manifest_file_tpl(self, file_key):
        """For template based manifest file items (items with a
        template specified) validate the template information.

        """
        template_name = self.__check_and_get_config_path(
            "manifest.files.%s.template_name" % file_key, str
        )
        template_path = Path(template(template_name))
        if not template_path.exists():
            raise ConfigError(
                "(internal) missing template file '%s' "
                "referenced from 'manifest.files.%s.template_name'" % (
                    template_name, file_key
                )
            )

    def __valid_manifest_file(self, file_key):
        """Validate the contents of a manifest item

        """
        # Look at the template name for the specified file
        # structure. It it is None, then the template is generated, if
        # not the template is a file. It needs to be explicitely None
        # to be generated, missing is not okay.
        template_name = self.__check_and_get_config_path(
            "manifest.files.%s.template_name" % file_key, str, none_ok=True
        )
        if template_name is None:
            self.__valid_manifest_file_gen(file_key)
        else:
            self.__valid_manifest_file_tpl(file_key)
        # Verify that 'target' is specified and is a string
        self.__check_and_get_config_path(
            "manifest.files.%s.target" % file_key, str
        )
        # Verify that 'mode' is specified and is a legal value
        mode = self.__check_and_get_config_path(
            "manifest.files.%s.mode" % file_key, str
        )
        mode_re = re.compile("^[0-7][0-7][0-7]$")
        if not mode_re.match(mode):
            raise ConfigError(
                "'manifest.files.%s.mode' has a value of '%s' which "
                "is invalid since it should be a three digit octal "
                "value" % (file_key, mode)
            )
        # The owner and group fields in a file manifest are optional,
        # but they have to be strings and exist on the installation
        # host if they are present. Also, if we are doing host
        # preparation, an explicit and existing owner and group must
        # be present.
        owner = self.config_by_path(
            'manifest.files.%s.owner' % file_key, default=None
        )
        if self.options.get('prep-host', False) and owner is None:
            raise ConfigError(
                "manifest file 'manifest.files.%s' must have an explicit "
                "owner"
            )
        if owner is not None:
            if not isinstance(owner, str):
                raise ConfigError(
                    "'manifest.files.%s.owner' has a value of type '%s' and "
                    "should have a value of type '%s' or be null" % (
                        file_key, str(type(owner)), str(str)
                    )
                )
            try:
                getpwnam(owner)
            except KeyError as err:
                raise ContextualError(
                    "'manifest.files.%s.owner' specifies a username '%s' "
                    "that is not yet provisioned on the host" % (
                        file_key, owner
                    )
                ) from err
        group = self.config_by_path(
            'manifest.files.%s.group' % file_key, default=None
        )
        if self.options.get('prep-host', False) and group is None:
            raise ConfigError(
                "manifest file 'manifest.files.%s' must have an explicit "
                "group"
            )
        if group is not None:
            if not isinstance(group, str):
                raise ConfigError(
                    "'manifest.files.%s.group' has a value of type '%s' and "
                    "should have a value of type '%s' or be null" % (
                        file_key, str(type(group)), str(str)
                    )
                )
            try:
                getgrnam(group)
            except KeyError as err:
                raise ContextualError(
                    "'manifest.files.%s.group' specifies a group '%s' that is "
                    "not yet provisioned on the host" % (
                        file_key, group
                    )
                ) from err

    def __valid_manifest_files(self):
        """Validate the 'files' section of the manifest

        """
        manifest_files = self.__check_and_get_config_path(
            'manifest.files', dict
        )
        if not manifest_files:
            raise ConfigError(
                "'manifest.files' must contain at least one item"
            )
        # If we are running in prep-host mode, we are only going to
        # deploy a subset of the manifest, only check the files we
        # plan to deploy.
        prep_host = self.options.get('prep-host', False)
        annotations = (
            ['host-prep-entrypoint', 'host-prep-support'] if prep_host
            else []
        )
        for file_key, manifest_file in manifest_files.items():
            file_annotations = manifest_file.get('annotations', [])
            matches = [
                file_annotation
                for file_annotation in file_annotations
                if file_annotation in annotations
            ]
            if annotations and not matches:
                # No matching annotations, skip this file
                continue
            self.__valid_manifest_file(file_key)

    def __valid_required_annotation(self, annotation, max_count=None):
        """Make sure that the specified 'annotation' is present on at
        least one file in the manifest and, if 'max_count' is
        specified, no more than 'max_count' files.

        """
        manifest_files = self.__check_and_get_config_path(
            'manifest.files', dict
        )
        found = [
            manifest_file_key
            for manifest_file_key, manifest_file in manifest_files.items()
            if annotation in manifest_file.get('annotations', [])
        ]
        if not found:
            raise ConfigError(
                "there is no file with the required annotation "
                "'%s' in 'manifest.files'" % annotation
            )
        if max_count is not None and len(found) > max_count:
            raise ConfigError(
                "there should be a maximum of %d file%s with the "
                "annotation '%s' in 'manifest.files', these files "
                "all have that annotation: %s" % (
                    max_count,
                    's' if max_count > 1 else '',
                    annotation,
                    str(found)
                )
            )

    def __valid_manifest(self):
        """Validate the contents of the manifest portion of the
        configuration

        """
        self.__check_and_get_config_path('manifest', dict)
        self.__valid_manifest_deploy_dir()
        self.__valid_manifest_deploy_user()
        self.__valid_manifest_files()
        self.__valid_required_annotation('image-builder')
        self.__valid_required_annotation('install-entrypoint', 1)
        self.__valid_required_annotation('host-prep-entrypoint', 1)

    def __valid_bmcs(self):
        """Validate the configuration of BMCs

        """
        bmcs = self.__check_and_get_config_path('bmcs', dict)
        for bmc_name, bmc in bmcs.items():
            if 'network' not in bmc:
                raise ConfigError(
                    "bmc '%s' has no 'network' specification" % bmc_name
                )
            if 'ipv4' not in bmc['network']:
                raise ConfigError(
                    "bmc '%s' 'network' specification has no 'ipv4'" % bmc_name
                )
            if 'redfish_username' not in bmc['network']:
                raise ConfigError(
                    "bmc '%s' 'network' specification has "
                    "no 'redfish_username'" % bmc_name
                )

    def __valid_hosting(self):
        """Validate the hosting configuration

        """
        self.__check_and_get_config_path('hosting_config', dict)

    def __valid_node(self, node):
        """Verify that the contents of a node is complete and
        consistent.
        """
        name = "<unnamed-node>"
        try:
            name = self.__check_and_get_dict_key('name', node, str)
            self.__check_and_get_dict_key('bmc_name', node, str)
            cluster_net_interface = self.__check_and_get_dict_key(
                'cluster_net_interface', node, str
            )
            self.__check_and_get_dict_key('hostname', node, str)
            self.__check_and_get_dict_key('nid', node, int)
            self.__check_and_get_dict_key('node_group', node, str)
            interfaces = self.__check_and_get_dict_key(
                'interfaces', node, list
            )
        except ConfigError as err:
            raise ConfigError(
                "node '%s' is not properly formed - %s" % (name, str(err))
            ) from err
        cluster_interface = None
        for interface in interfaces:
            network_name = "<unnamed-network>"
            try:
                network_name = self.__check_and_get_dict_key(
                    'network_name', interface, str
                )
                self.__check_and_get_dict_key(
                    'mac_addr', interface, str
                )
                if network_name == cluster_net_interface:
                    cluster_interface = interface
            except ConfigError as err:
                raise ConfigError(
                    "network '%s' in node '%s' is not properly formed - %s" % (
                        name, network_name, str(err)
                    )
                ) from err
        if cluster_interface is None:
            raise ConfigError(
                "node '%s' has no interface connected to the cluster "
                "network ('%s')" % (name, cluster_net_interface)
            )

    def __valid_nodes(self):

        """Validate the 'nodes' section of the config

        """
        nodes = self.__check_and_get_config_path('nodes', list)
        if not nodes:
            raise ConfigError(
                "the 'nodes' section is empty"
            )
        for node_key in nodes:
            self.__valid_node(node_key)

    def __valid_images(self):
        """Validate the 'images' section of the config

        """
        self.__check_and_get_config_path('images', dict)
        self.__check_and_get_config_path('images.build_order', list)
        builders = self.__check_and_get_config_path('images.builders', dict)
        if not builders:
            raise ConfigError(
                "config must provide at least one image builder in "
                "'images.builders' section"
            )
        deployment_targets = self.__check_and_get_config_path(
            'images.deployment_targets', dict
        )
        if not deployment_targets:
            raise ConfigError(
                "config must provide at least one deployment target in "
                "'images.deployment_targets' section"
            )
        # Check that all deployment targets are deploying an image
        # built by a known image builder and are targeting a known
        # node group.
        #
        # First, make a set of node groups to use in validating
        # deployment target keys.
        nodes = self.config.get('nodes', {})
        node_groups = {
            node['node_group']
            for node in nodes
            if 'node_group' in node
        }
        for node_group, image_key in deployment_targets.items():
            if image_key not in builders:
                raise ConfigError(
                    "unknown image builder key '%s' used for node group "
                    "'%s' in 'images.deployment_targets'" % (
                        image_key, node_group
                    )
                )
            if node_group not in node_groups:
                raise ConfigError(
                    "unknown config target node group '%s' "
                    "found in 'images.deployment_targets' section "
                    "known node groups are: %s" % (
                        node_group,
                        " % ".join(sorted(list(node_groups)))
                    )
                )

    def validate(self):
        """Validate the final configuration to be sure that everything
        is reasonable before attempting an installation.

        """
        self.load_config()
        deployment_mode = self.__check_and_get_config_path(
            'deployment_mode', str
        )
        if deployment_mode not in ('host', 'cluster'):
            raise ConfigError(
                "unknown deployment_mode: '%s' "
                "expected 'host' or 'cluster'" % deployment_mode
            )
        self.__valid_manifest()
        self.__valid_bmcs()
        self.__valid_hosting()
        self.__valid_nodes()
        self.__valid_images()

    def show_config(self):
        """Display the configuration resulting from applying the base
        configuration and all of the overlay files on standard output.

        """
        self.load_config()
        sys.stdout.write(self.dump_yaml())

    def show_base_config(self):
        """Display the base configuration file (with comments) on
        standard output.

        """
        with open(BASE_CONFIG_PATH, 'r', encoding='UTF-8') as base_config:
            sys.stdout.write(base_config.read() + '\n')
