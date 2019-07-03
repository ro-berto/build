# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A script to retrieve the last changed revision of files in the checkout.

It parses the DEPS file to look for dependency repositories, and runs "git log"
to get the last changed revision of files.
"""

import collections
import logging
import multiprocessing
import os
import subprocess
import time


class _VarImpl(object):

  def __init__(self, local_scope):
    self._local_scope = local_scope

  def Lookup(self, var_name):
    if var_name not in self._local_scope.get('vars', {}):
      raise KeyError('Var is not defined: %s' % var_name)
    return self._local_scope['vars'][var_name]


class _Timer(object):

  def __init__(self):
    self._time = None

  def Start(self):
    self._time = time.time()

  def End(self, msg):
    new_time = time.time()
    elapsed_time = new_time - self._time
    logging.info('%s took %.0f seconds', msg, elapsed_time)


def _GetOrderedCheckoutDirOfDependenciesFromDEPS(deps_content):
  """Returns the paths to the checkouts of all dependencies in the given DEPS.

  By default, '//' is added as the root checkout of the given DEPS.

  Args:
    deps_content (str): the content of a DEPS file. It is assumed to be trusted
        and will be evaluated as python code.

  Returns:
    A list of file paths in descending order of the length of file paths.
    A path starts with '//' as the root, and ends with '/'.
  """
  local_scope = {
      'vars': {},
      'allowed_hosts': [],
      'deps': {},
      'deps_os': {},
      'include_rules': [],
      'skip_child_includes': [],
      'hooks': [],
  }
  var = _VarImpl(local_scope)
  global_scope = {
      'Var': var.Lookup,
      'vars': {},
      'allowed_hosts': [],
      'deps': {},
      'deps_os': {},
      'include_rules': [],
      'skip_child_includes': [],
      'hooks': [],
  }
  exec deps_content in global_scope, local_scope

  checkout_dirs = local_scope['deps'].keys()
  for _, deps_os_checkout_dirs in local_scope['deps_os'].iteritems():
    checkout_dirs.extend(deps_os_checkout_dirs)

  src_checkout_paths = ['//']

  root_dir = 'src/'
  for path in checkout_dirs:
    if path.startswith(root_dir):
      path = path[len(root_dir):]
    path = '//' + path
    if not path.endswith('/'):
      path += '/'
    src_checkout_paths.append(path)
  # pylint: disable=unnecessary-lambda
  src_checkout_paths.sort(key=lambda x: len(x), reverse=True)

  return src_checkout_paths


def _RetrieveRevisionFromGit(args):
  """Returns the path, git hash, and last changed timestamp of the given file.

  Args:
    args (tuple): A tuple <root_dir, checkout_dir, path> where
      * root_dir (str): System absolute path to the root checkout.
      * checkout_dir (str): Source absolute path to the root of a dependency
                            checkout.
      * path (str): Source absolute path to the file to retrieve the revision.

  Returns:
    A tuple of three elements:
      1. Source absolute path to the file.
      2. Git hash of the commit when the file was most recently updated.
      3. Time stamp of the commit when the file was most recently updated.
  """
  assert len(args) == 3, 'Got %d args, but expected 3' % (len(args))
  root_dir, checkout_dir, path = args

  assert checkout_dir.startswith('//'), (
      '%s is expected to start with //' % checkout_dir)
  cwd = os.path.join(root_dir, checkout_dir[2:])

  assert path.starts_with('//'), '%s is expected to start with //' % path
  path_in_dep_repo = path[len(checkout_dir):]
  try:
    git_output = subprocess.check_output(
        ['git', 'log', '-n', '1', '--pretty=format:%H:%ct', path_in_dep_repo],
        cwd=cwd)

    lines = git_output.splitlines()
    assert len(lines) == 1, 'More than one line output.'

    parts = lines[0].split(':')
    assert len(parts) == 2, 'not in format "git_hash:timestamp"'

    return path, parts[0], int(parts[1])
  except (subprocess.CalledProcessError, AssertionError):
    print 'Failed to retrieve revision for %s: %r' % (checkout_dir, path)
    return None


def _GetCommitedFilesForEachCheckout(root_dir, checkouts):
  """Returns source absolute paths to all committed files in each checkout.

  Args:
    root_dir (str): Absolute path to the directory of the root checkout.
    checkouts (list): A list of source absolute paths to checkout directories.

  Returns:
    A dict mapping from a checkout (in source absolute path) to the list of
    committed files (in source absolute path).
  """
  all_files = collections.defaultdict(set)
  for checkout in checkouts:
    assert checkout.startswith('//')
    checkout_dir = os.path.join(root_dir, checkout[2:])
    if not os.path.isdir(checkout_dir):
      continue
    git_output = subprocess.check_output(['git', 'ls-files'], cwd=checkout_dir)
    for path in git_output.splitlines():
      all_files[checkout].add(os.path.join(checkout, path))
  return all_files


def GetFileRevisions(root_dir, deps_file_path, file_paths):
  """Returns a dict mapping from the path to its git revision for given files.

  Args:
    root_dir (str): System absolute path to the directory of the root checkout.
    deps_file_path (str): Relative path to the DEPS file in the root checkout.
    file_paths (list): The list of source absolute file paths to retrieve git
                       revisions for.

  Returns:
    A dict that maps from file source absolute paths to tuples of two elements:
      1. Git hash of the commit when the file was most recently updated.
      2. Time stamp of the commit when the file was most recently updated.
  """
  file_data = []
  timer = _Timer()
  timer.Start()
  with open(os.path.join(root_dir, deps_file_path), 'r') as f:
    deps_file_content = f.read()
  timer.End('Reading deps file')

  timer.Start()
  checkouts = _GetOrderedCheckoutDirOfDependenciesFromDEPS(deps_file_content)
  timer.End('_GetOrderedCheckoutDirOfDependenciesFromDEPS')

  timer.Start()
  all_files = _GetCommitedFilesForEachCheckout(root_dir, checkouts)
  timer.End('_GetCommitedFilesForEachCheckout')

  timer.Start()
  for path in file_paths:
    assert path.startswith('//'), '%s is expected to start with //' % path
    for checkout in checkouts:
      if path.startswith(checkout) and path in all_files.get(checkout, []):
        file_data.append((root_dir, checkout, path))
        break
  timer.End('Finding correct checkout')

  timer.Start()
  # Leave 5 cpus for other system or infra processes.
  pool = multiprocessing.Pool(processes=max(5, multiprocessing.cpu_count() - 5))
  future_results = pool.map(_RetrieveRevisionFromGit, file_data, 100)
  pool.close()
  pool.join()
  timer.End('Multiprocess _RetrieveRevisionFromGit')

  all_result = {}
  for result in future_results:
    if not result:
      continue
    path, git_hash, timestamp = result
    all_result[path] = (git_hash, timestamp)
  return all_result


def AddGitRevisionsToCoverageFilesMetadata(files_coverage_data, src_path,
                                           deps_file_path):
  """Add git revisions to a list File in coverage metadata format.

  Coverage metadata format:
  https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto

  Args:
    files_coverage_data (list): A list of File in coverage metadata format, and
                                it is going to be mutated by this function.
    src_path (str): Absolute path to the source root.
    deps_file_path (str): Relative path to the DEPS file that manages
                          dependencies.
  """
  logging.info('Retrieving file git metadata...')
  start_time = time.time()

  all_files = [file_record['path'] for file_record in files_coverage_data]
  file_git_metadata = GetFileRevisions(src_path, deps_file_path, all_files)
  for file_record in files_coverage_data:
    git_metadata = file_git_metadata.get(file_record['path'])
    if not git_metadata:
      logging.warn('Failed to retrive git metadata for %s', file_record['path'])
      continue

    file_record['revision'], file_record['timestamp'] = git_metadata

  minutes = (time.time() - start_time) / 60
  logging.info(
      'Retrieving and filling in git metadata for %d files took %.0f '
      'minutes', len(all_files), minutes)
