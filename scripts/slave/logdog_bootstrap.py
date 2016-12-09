# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implements LogDog Bootstrapping support.
"""

import collections
import json
import logging
import os
import subprocess
import sys

from common import chromium_utils
from common import env
from slave import cipd
from slave import gce
from slave import infra_platform


LOGGER = logging.getLogger('logdog_bootstrap')


class NotBootstrapped(Exception):
  pass


class BootstrapError(Exception):
  pass


# CIPD tag for LogDog Butler/Annotee to use.
_STABLE_CIPD_TAG = 'git_revision:25755a2c316937ee44a6432163dc5e2f9c85cf58'


# Platform is the set of platform-specific LogDog bootstrapping
# configuration parameters. Platform is loaded by cascading the _PLATFORM_CONFIG
# against the current running platform.
#
# See _get_streamserver_uri for "streamserver" parameter details.
#
# Loaded by '_get_platform'.
Platform = collections.namedtuple('Platform', (
    'service_host', 'viewer_host', 'max_buffer_age',
    'butler', 'butler_relpath', 'annotee', 'annotee_relpath',
    'credential_path', 'streamserver'))


# An infra_platform cascading configuration for the supported architectures.
_PLATFORM_CONFIG = {
  # All systems.
  (): {
    'service_host': 'services-dot-luci-logdog.appspot.com',
    'viewer_host': 'luci-logdog.appspot.com',
    'max_buffer_age': '30s',
  },

  # Linux
  ('linux',): {
    'credential_path': ('/creds/service_accounts/'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'unix',
    'butler_relpath': 'logdog_butler',
    'annotee_relpath': 'logdog_annotee',
  },
  ('linux', 32): {
    'butler': 'infra/tools/luci/logdog/butler/linux-386',
    'annotee': 'infra/tools/luci/logdog/annotee/linux-386',
  },
  ('linux', 64): {
    'butler': 'infra/tools/luci/logdog/butler/linux-amd64',
    'annotee': 'infra/tools/luci/logdog/annotee/linux-amd64',
  },

  # Mac
  ('mac',): {
    'credential_path': ('/creds/service_accounts/'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'unix',
    'butler_relpath': 'logdog_butler',
    'annotee_relpath': 'logdog_annotee',
  },
  ('mac', 64): {
    'butler': 'infra/tools/luci/logdog/butler/mac-amd64',
    'annotee': 'infra/tools/luci/logdog/annotee/mac-amd64',
  },

  # Windows
  ('win',): {
    'credential_path': ('c:\\creds\\service_accounts\\'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'net.pipe',
    'butler_relpath': 'logdog_butler.exe',
    'annotee_relpath': 'logdog_annotee.exe',
  },
  ('win', 32): {
    'butler': 'infra/tools/luci/logdog/butler/windows-386',
    'annotee': 'infra/tools/luci/logdog/annotee/windows-386',
  },
  ('win', 64): {
    'butler': 'infra/tools/luci/logdog/butler/windows-amd64',
    'annotee': 'infra/tools/luci/logdog/annotee/windows-amd64',
  },
}


# Params are parameters for this specific master/builder configuration.
#
# Loaded by '_get_params'.
Params = collections.namedtuple('Params', (
    'project', 'cipd_tag', 'mastername', 'buildername', 'buildnumber',
    'logdog_only',
))


def _check_call(cmd, **kwargs):
  LOGGER.debug('Executing command: %s', cmd)
  subprocess.check_call(cmd, **kwargs)


def _get_platform():
  """Returns (Platform): The constructed Platform object.

  Raises:
    TypeError: if a required configuration key/parameter is not available.
  """
  return Platform(**infra_platform.cascade_config(_PLATFORM_CONFIG))


def _load_params_dict(mastername):
  """Returns (dict or None): The parameters for the specified master.

  The parameters are loaded by locating the 'logdog-params.pyl' file for the
  currently-executing waterfall. If found, it will be parsed and the waterfall's
  parameters will be loaded from it.

  If no parameter file could be found, or no parameters are defined for the
  specified waterfall, None will be returned.

  Args:
    mastername (str): The name of the master whose parameters will be loaded.

  Raises:
    NotBootstrapped: If the parameters dictionary could not be loaded.
  """
  # Identify the directory where the master is located.
  try:
    master_dir = chromium_utils.MasterPath(mastername)
  except LookupError as e:
    LOGGER.warning('Unable to find directory for master [%s] (%s)',
                   mastername, e)
    raise NotBootstrapped('No master directory')

  # 'master_dir' is:
  #   <build_dir>/masters/<master_name>
  #
  #  We want to look up:
  #   <build_dir>/scripts/slave/logdog-params.pyl
  #
  params_path = os.path.join(master_dir, os.pardir, os.pardir, 'scripts',
                             'slave', 'logdog-params.pyl')
  if not os.path.isfile(params_path):
    LOGGER.warning('No LogDog parameters at: [%s]', params_path)
    raise NotBootstrapped('No parameters file.')

  # Load and parse our parameters.
  LOGGER.debug('Loading LogDog parameters from: [%s]', params_path)
  with open(params_path, 'r') as fd:
    params_data = fd.read()

  try:
    params = eval(params_data)
    assert isinstance(params, dict)
  except SyntaxError as e:
    LOGGER.error('Failed to parse params from [%s]: %s', params_path, e)
    raise NotBootstrapped('Invalid parameters file.')
  except AssertionError:
    LOGGER.error('Params parsed to non-dictionary (%s)', type(params).__name__)
    raise NotBootstrapped('Parameters file does not contain a dictionary.')
  return params


def _get_params(properties):
  """Returns (Params): Parameters for the given properties.

  The parameters are loaded by locating the 'logdog-params.pyl' file for the
  currently-executing waterfall. If found, it will be parsed and the waterfall's
  parameters will be loaded from it.

  If no parameter file could be found, or no parameters are defined for the
  specified waterfall, None will be returned.

  Args:
    properties (dict): Build property dictionary.

  Raises:
    NotBootstrapped: If parameters could not be built, or if this master/builder
        is disabled.
  """
  # Extract our required properties.
  props = tuple(properties.get(f) for f in (
      'mastername', 'buildername', 'buildnumber'))
  if not all(props):
    LOGGER.warning('Missing mastername/buildername/buildnumber properties.')
    raise NotBootstrapped('Insufficient properties.')
  mastername, buildername, buildnumber = props

  # Find our project name and master config.
  project = None
  for project, masters in sorted(_load_params_dict(mastername).items()):
    master_config = masters.get(mastername)
    if master_config is not None:
      break
  else:
    LOGGER.info('No master config found for [%s].', mastername)
    raise NotBootstrapped('No master config.')

  # Get builder config map, allowing overrides if one is defined for either the
  # specific builder or all builders ('*').
  builder_map = {
    'enabled': True,
    'cipd_tag': _STABLE_CIPD_TAG,
    'logdog_only': False,
  }
  for bn in (buildername, '*'):
    bn_map = master_config.get(bn)
    if bn_map is not None:
      builder_map.update(bn_map)
      break

  # If our builder is not enabled, we are done.
  if not builder_map['enabled']:
    LOGGER.info('LogDog is disabled for master / builder [%s / %s].',
                mastername, buildername)
    raise NotBootstrapped('LogDog is disabled.')

  return Params(
      project=project,
      cipd_tag=builder_map['cipd_tag'],
      mastername=mastername,
      buildername=buildername,
      buildnumber=buildnumber,
      logdog_only=builder_map['logdog_only'],
  )


def _get_streamserver_uri(rt, typ):
  """Returns (str): The Butler StreamServer URI.

  Args:
    rt (RobustTempdir): context for temporary directories.
    typ (str): The type of URI to generate. One of: ['unix'].
  Raises:
    BootstrapError: if |typ| is not a known type.
  """
  if typ == 'unix':
    # We have to use a custom temporary directory here. This is due to the path
    # length limitation on UNIX domain sockets, which is generally 104-108
    # characters. We can't make that assumption about our standard recipe
    # temporary directory.
    #
    # Bots run out of "/b/build", so this will form a path starting at
    # "/b/build/.recipe_runtime/tmp-<random>/butler.sock", which is well below
    # the socket name size limit.
    #
    # We don't drop this in "/tmp" because several build scripts assume
    # ownership of that directory and blindly clear it as part of cleanup, and
    # this socket is too important to risk.
    sockdir = rt.tempdir(env.Build)
    uri = 'unix:%s' % (os.path.join(sockdir, 'butler.sock'),)
    if len(uri) > 104:
      raise BootstrapError('Generated URI exceeds UNIX domain socket '
                                 'name size: %s' % (uri,))
    return uri
  elif typ == 'net.pipe':
    return 'net.pipe:LUCILogDogButler'
  else:
    raise BootstrapError('No streamserver URI generator.')


def _get_service_account_json(opts, credential_path):
  """Returns (str/None): If specified, the path to the service account JSON.

  This method probes the local environment and returns a (possibly empty) list
  of arguments to add to the Butler command line for authentication.

  If we're running on a GCE instance, no arguments will be returned, as GCE
  service account is implicitly authenticated. If we're running on Baremetal,
  a path to those credentials will be returned.

  Raises:
    |BootstrapError| if no credentials could be found.
  """
  path = opts.logdog_service_account_json
  if path:
    return path

  if gce.Authenticator.is_gce():
    LOGGER.info('Running on GCE. No credentials necessary.')
    return None

  if os.path.isfile(credential_path):
    return credential_path

  raise BootstrapError('Could not find service account credentials. '
                       'Tried: %s' % (credential_path,))


def _install_cipd(path, *binaries):
  """Returns (list): The paths to the binaries.

  This method bootstraps CIPD in "path", installing the packages specified
  by "binaries".

  Args:
    path (str): The CIPD installation root.
    binaries (CipdBinary): The set of CIPD binaries to install.
  """
  verbosity = 0
  level = logging.getLogger().level
  if level <= logging.INFO:
    verbosity += 1
  if level <= logging.DEBUG:
    verbosity += 1

  packages_path = os.path.join(path, 'packages.json')
  pmap = {}
  cmd = [
      sys.executable,
      os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
      '--dest-directory', path,
      '--json-output', packages_path,
  ] + (['--verbose'] * verbosity)
  for b in binaries:
    cmd += ['-P', '%s@%s' % (b.package.name, b.package.version)]
    pmap[b.package.name] = os.path.join(path, b.relpath)

  try:
    _check_call(cmd)
  except subprocess.CalledProcessError:
    LOGGER.exception('Failed to install LogDog CIPD packages: %s', binaries)
    raise BootstrapError('Failed to install CIPD packages.')

  # Resolve installed binaries.
  return tuple(pmap[b.package.name] for b in binaries)


def _build_prefix(params):
  """Constructs a LogDog stream prefix from the supplied properties.

  The returned prefix is of the form:
  bb/<mastername>/<buildername>/<buildnumber>

  Any path-incompatible characters will be flattened to underscores.
  """
  def normalize(s):
    parts = []
    for ch in str(s):
      if ch.isalnum() or ch in ':_-.':
        parts.append(ch)
      else:
        parts.append('_')
    if not parts[0].isalnum():
      parts.insert(0, 's_')
    return ''.join(parts)

  mastername, buildername, buildnumber = (normalize(p) for p in (
      params.mastername, params.buildername, params.buildnumber))
  return 'bb/%s/%s/%s' % (mastername, buildername, buildnumber)


def bootstrap(rt, opts, basedir, tempdir, properties, cmd):
  """Executes the recipe engine, bootstrapping it through LogDog/Annotee.

  This method executes the recipe engine, bootstrapping it through
  LogDog/Annotee so its output and annotations are streamed to LogDog. The
  bootstrap is configured to tee the annotations through STDOUT/STDERR so they
  will still be sent to BuildBot.

  The overall setup here is:
  [annotated_run.py] => [logdog_butler] => [logdog_annotee] => [recipes.py]

  Args:
    rt (RobustTempdir): context for temporary directories.
    opts (argparse.Namespace): Command-line options.
    basedir (str): The base (non-temporary) recipe directory.
    tempdir (str): The path to the session temporary directory.
    properties (dict): Build properties.
    cmd (list): The recipe runner command list to bootstrap.

  Returns (BootstrapState): The populated bootstrap state.

  Raises:
    NotBootstrapped: if the recipe engine was not executed because the
        LogDog bootstrap requirements are not available.
    BootstrapError: if there was an error bootstrapping the recipe runner
        through LogDog.
  """
  # If we have LOGDOG_STREAM_PREFIX defined, we are already bootstrapped. Don't
  # start a new instance.
  #
  # LOGDOG_STREAM_PREFIX is set by the Butler when it bootstraps a process, so
  # it should be set for all child processes of the initial bootstrap.
  if os.environ.get('LOGDOG_STREAM_PREFIX', None) is not None:
    raise NotBootstrapped(
       'LOGDOG_STREAM_PREFIX in enviornment, refusing to nest bootstraps.')

  # Load our bootstrap parameters based on our master/builder.
  params = _get_params(properties)

  # Get our platform configuration. This will fail if any fields are missing.
  plat = _get_platform()

  # Determine LogDog prefix.
  prefix = _build_prefix(params)
  LOGGER.debug('Using log stream prefix: [%s]', prefix)

  def var(title, v, dflt):
    v = v or dflt
    if not v:
      raise NotBootstrapped('No value for [%s]' % (title,))
    return v

  # Install our Butler/Annotee packages from CIPD.
  cipd_path = os.path.join(basedir, '.recipe_cipd')
  butler, annotee = _install_cipd(cipd_path,
      # butler
      cipd.CipdBinary(
          package=cipd.CipdPackage(name=plat.butler, version=params.cipd_tag),
          relpath=plat.butler_relpath,
      ),

      # annotee
      cipd.CipdBinary(
          package=cipd.CipdPackage(name=plat.annotee, version=params.cipd_tag),
          relpath=plat.annotee_relpath,
      ),
  )

  butler = var('butler', opts.logdog_butler_path, butler)
  if not os.path.isfile(butler):
    raise NotBootstrapped('Invalid Butler path: %s' % (butler,))

  annotee = var('annotee', opts.logdog_annotee_path, annotee)
  if not os.path.isfile(annotee):
    raise NotBootstrapped('Invalid Annotee path: %s' % (annotee,))

  service_host = var('service host', opts.logdog_service_host,
                     plat.service_host)
  viewer_host = var('viewer host', opts.logdog_viewer_host, plat.viewer_host)

  # Determine LogDog verbosity.
  if opts.logdog_verbose == 0:
    log_level = 'warning'
  elif opts.logdog_verbose == 1:
    log_level = 'info'
  else:
    log_level = 'debug'

  service_account_json = _get_service_account_json(opts, plat.credential_path)

  # Generate our Butler stream server URI.
  streamserver_uri = _get_streamserver_uri(rt, plat.streamserver)

  # If we are using file sentinel-based bootstrap error detection, enable.
  bootstrap_result_path = os.path.join(tempdir, 'bootstrap_result.json')

  # Dump the bootstrapped Annotee command to JSON for Annotee to load.
  #
  # Annotee can run accept bootstrap parameters through either JSON or
  # command-line, but using JSON effectively steps around any sort of command-
  # line length limits such as those experienced on Windows.
  cmd_json = os.path.join(tempdir, 'logdog_annotee_cmd.json')
  with open(cmd_json, 'w') as fd:
    json.dump(cmd, fd)

  # Butler Command.
  cmd = [
      butler,
      '-log-level', log_level,
      '-project', params.project,
      '-prefix', prefix,
      '-output', 'logdog,host="%s"' % (service_host,),
  ]
  if service_account_json:
    cmd += ['-service-account-json', service_account_json]
  if plat.max_buffer_age:
    cmd += ['-output-max-buffer-age', plat.max_buffer_age]
  cmd += [
      'run',
      '-stdout', 'tee=stdout',
      '-stderr', 'tee=stderr',
      '-streamserver-uri', streamserver_uri,
      '--',
  ]

  # Annotee Command.
  cmd += [
      annotee,
      '-log-level', log_level,
      '-project', params.project,
      '-butler-stream-server', streamserver_uri,
      '-logdog-host', viewer_host,
      '-name-base', 'recipes',
      '-print-summary',
      '-json-args-path', cmd_json,
      '-result-path', bootstrap_result_path,
  ]
  if params.logdog_only:
    # Only tee annotations.
    cmd += ['-tee', 'annotations']
  else:
    # Old-style Annotee parameters. This can be deleted when we bump to
    # new-style annotee, and should be replaced with:
    #
    # -tee text,annotations
    cmd += [
        '-annotate', 'tee',
        '-tee=true',
    ]
  return BootstrapState(cmd, bootstrap_result_path)


class BootstrapState(object):
  def __init__(self, cmd, bootstrap_result_path):
    self._cmd = cmd
    self._bootstrap_result_path = bootstrap_result_path

  @property
  def cmd(self):
    """Returns (list): The Butler-bootstrapped command."""
    return self._cmd[:]

  def get_result(self):
    """Retrieves and returns the return code of the bootstrapped process.

    Returns (int): The bootstrapped process' return code.

    Raises:
      BootstrapError: If the bootstrapped process didn't even run.
    """
    try:
      with open(self._bootstrap_result_path) as fd:
        result = json.load(fd)
    except (IOError, ValueError) as e:
      raise BootstrapError('Failed to open bootstrap result file [%s]: %s' % (
            self._bootstrap_result_path, e))
    try:
      return result['return_code']
    except KeyError as e:
      raise BootstrapError('Invalid bootstrap result file [%s]: %s' % (
          self._bootstrap_result_path, e))


def add_arguments(parser):
  parser.add_argument('--logdog-verbose',
      action='count', default=0,
      help='Increase LogDog verbosity. This can be specified multiple times.')
  parser.add_argument('--logdog-butler-path',
      help='Path to the LogDog Butler. If empty, one will be probed/downloaded '
           'from CIPD.')
  parser.add_argument('--logdog-annotee-path',
      help='Path to the LogDog Annotee. If empty, one will be '
           'probed/downloaded from CIPD.')
  parser.add_argument('--logdog-service-account-json',
      help='Path to the service account JSON. If one is not provided, the '
           'local system credentials will be used.')
  parser.add_argument('--logdog-service-host',
      help='Override the LogDog service host, used by Butler for registration.')
  parser.add_argument('--logdog-viewer-host',
      help='Override the LogDog viewer host, used by Annotee to build URLs.')
