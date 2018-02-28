
import argparse
import uuid

import sml.auth
import sml.casebook

from .models import Configuration
from .projects import Projects
from .version import version


DEFAULT_IGNORE_PATTERNS = [
    'node_modules',
    '__pycache__',
    '*.pyc',
    '.ipynb_checkpoints',
    '.tox',
    '.git',
    '.mypy_cache',
    '.cache'
]


class NoValidServer(Exception):
    pass


def parse_command_line(argv=None):
    parser = argparse.ArgumentParser(
        prog='sml-sync',
        description='Autosync a local directory to a SherlockML project'
    )
    parser.add_argument('project', help='Project name or ID')
    parser.add_argument(
        '--remote',
        default=None,
        help=(
            'Remote directory, e.g. /project/src. If omitted, '
            'you will be prompted for a directory.')
    )
    parser.add_argument(
        '--local',
        default='.',
        help='Local directory to sync from. Defaults to the current directory.'
    )
    parser.add_argument(
        '--ignore',
        nargs='+',
        help='Path fragments to ignore (e.g. node_modules, __pycache__).'
    )
    parser.add_argument(
        '--debug',
        default=False,
        action='store_true',
        help='Run in debug mode (sets the log level to info).'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='sml-sync {version}'.format(version=version)
    )
    parser.add_argument(
        '--server',
        default=None,
        help=('The name of the server in the project to use. If omitted, '
              'a random server is used.')
    )
    arguments = parser.parse_args(argv)
    project = _resolve_project(arguments.project)
    server_id = _resolve_server(project.id_, arguments.server)
    # server_id = _any_server(project.id_, server_name=arguments.server)
    local_dir = arguments.local
    remote_dir = arguments.remote
    local_dir = local_dir.rstrip('/') + '/'
    if remote_dir is not None:
        remote_dir = remote_dir.rstrip('/') + '/'
    if arguments.ignore is None:
        ignore = DEFAULT_IGNORE_PATTERNS
    else:
        ignore = arguments.ignore + DEFAULT_IGNORE_PATTERNS
    configuration = Configuration(
        project, server_id, local_dir, remote_dir,
        arguments.debug, ignore
    )
    return configuration


def _resolve_project(project):
    """Resolve a project name or ID to a project ID."""
    projects_client = Projects()
    try:
        project_id = uuid.UUID(project)
        project = projects_client.get_project_by_id(project_id)
    except ValueError:
        user_id = sml.auth.user_id()
        project = projects_client.get_project_by_name(
            user_id, project)
    return project


def _server_by_name(project_id, server_name, status=None):
    """Resolve a project ID and server name to a server ID."""
    client = sml.galleon.Galleon()
    matching_servers = client.get_servers(project_id, server_name, status)
    if len(matching_servers) == 1:
        return matching_servers[0]
    else:
        if not matching_servers:
            tpl = 'no {} server of name "{}" in this project'
        else:
            tpl = ('more than one {} server of name "{}", please select by '
                   'server ID instead')
        adjective = 'available' if status is None else status
        raise NoValidServer(tpl.format(adjective, server_name))


def _resolve_server(project_id, server=None, ensure_running=True):
    """Resolve project and server names to project and server IDs."""
    # project_id = _resolve_project(project)
    status = 'running' if ensure_running else None
    try:
        server_id = uuid.UUID(server)
    except ValueError:
        server_id = _server_by_name(project_id, server, status).id_
    except TypeError:
        server_id = _any_server(project_id, status)
    return server_id


def _any_server(project_id, status=None):
    """Get any running server from project."""
    client = sml.galleon.Galleon()
    servers_ = client.get_servers(project_id, status=status)
    if not servers_:
        adjective = 'available' if status is None else status
        message = 'No {} server in project.'.format(adjective)
        raise NoValidServer(message)
    return servers_[0].id_
