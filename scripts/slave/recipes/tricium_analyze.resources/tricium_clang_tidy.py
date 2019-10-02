#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper for running clang-tidy on various files via recipes.

This will build all dependencies of the cc/c++ files you specify, then run
clang-tidy on all of them in parallel. Results are dumped as JSON to the given
findings file. For more information on what to expect in the findings file,
please see the nicely commented blob near the end of the script. :)
"""

# [VPYTHON:BEGIN]
# wheel: <
#    name: "infra/python/wheels/pyyaml/${vpython_platform}"
#    version: "version:3.12"
# >
# [VPYTHON:END]

import argparse
import bisect
import collections
import contextlib
import errno
import json
import logging
import multiprocessing
import multiprocessing.pool
import os
import os.path
import pipes
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

import yaml


@contextlib.contextmanager
def _temp_file():
  fd, path = tempfile.mkstemp(prefix='tricium_tidy')
  try:
    os.close(fd)
    yield path
  finally:
    os.unlink(path)


def _generate_compile_commands(out_dir):
  compile_commands = os.path.join(out_dir, 'compile_commands.json')
  # Regenerate compile_commands every time, since the user might've patched
  # files (etc.) since our previous run.
  with open(os.path.join(out_dir, 'args.gn')) as f:
    args_gn = f.read()

  logging.info('Generating gn\'s compile_commands')
  subprocess.check_call(
      cwd=out_dir,
      args=[
          'gn',
          'gen',
          '--export-compile-commands',
          '--args=' + args_gn,
          '.',
      ])

  assert os.path.isfile(compile_commands)
  return compile_commands


def _try_build_targets(out_dir, targets, jobs):
  # I demand the sum of... one MILLION targets.
  ninja_cmd = ['ninja', '-k', '1000000']
  if jobs is not None:
    ninja_cmd.append('-j%d' % jobs)
  ninja_cmd.append('--')
  ninja_cmd += targets

  if subprocess.call(ninja_cmd, cwd=out_dir):
    logging.warning('Build of all targets failed; falling back to individual '
                    'builds to figure out the failing targets')

  # Assume that all targets are actual object files, so we don't have to
  # iteratively `ninja` things to figure out what failed to build.
  return [x for x in targets if not os.path.isfile(os.path.join(out_dir, x))]


# Note that we shove these in a set for cheap deduplication, and we sort based
# on the natural element order here. Sorting is mostly just for
# deterministic/pretty output.
#
# FIXME(gbiv): Tidy also emits replacements and notes. Probably want to parse
# those out and surface them at some point.
_TidyDiagnostic = collections.namedtuple(
    '_TidyDiagnostic', ['file_path', 'line_number', 'diag_name', 'message'])


class _ParseError(Exception):

  def __init__(self, err_msg):
    Exception.__init__(self, err_msg)
    self.err_msg = err_msg


class _LineOffsetMap(object):
  """Convenient API to turn offsets in a file into line numbers."""

  def __init__(self, newline_locations):
    self._newline_locations = sorted(newline_locations)

  def get_line_number(self, char_number):
    return bisect.bisect_left(self._newline_locations, char_number) + 1

  @staticmethod
  def for_text(data):
    return _LineOffsetMap([m.start() for m in re.finditer(r'\n', data)])


def _parse_tidy_fixes_file(line_offsets, stream):
  try:
    findings = yaml.load(stream)
  except yaml.parser.ParserError as v:
    raise _ParseError('Broken yaml: %s' % v)

  if findings is None:
    return

  try:
    for diag in findings['Diagnostics']:
      message = diag['DiagnosticMessage']
      line_number = line_offsets.get_line_number(message['FileOffset'])

      yield _TidyDiagnostic(
          diag_name=diag['DiagnosticName'],
          message=message['Message'],
          file_path=message['FilePath'],
          line_number=line_number,
      )
  except KeyError as k:
    key_name = k.args[0]
    raise _ParseError('Broken yaml: missing key %r' % key_name)


def _run_clang_tidy(clang_tidy_binary, checks, in_dir, cc_file,
                    compile_command):
  with _temp_file() as findings_file:
    command = [clang_tidy_binary]

    if checks is not None:
      command.append('-checks=%s' % ','.join(checks))

    command += [
        cc_file,
        '--export-fixes=%s' % findings_file,
        '--',
    ]
    command.extend(shlex.split(compile_command))

    logging.debug('In %r, running %s', in_dir, ' '.join(
        pipes.quote(c) for c in command))

    try:
      tidy = subprocess.Popen(
          command, cwd=in_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as e:
      if e.errno == errno.ENOENT:
        logging.error('Failed to spawn clang-tidy -- is it installed?')
      raise

    clang_tidy_is_finished = threading.Event()

    def timeout_tidy():
      # When run on everything built for an Android out/ directory,
      # clang-tidy takes 27s on average per TU with
      # checks='*,-clang-analyzer*'. The worst 3 times were 251s, 264s,
      # and 1220s (~20 mins). The last time was clang-tidy running over a
      # 57KLOC cc file that boils down to a few massive arrays.
      #
      # In any case, 30mins seems like plenty.
      if not clang_tidy_is_finished.wait(timeout=30 * 60):
        os.kill(tidy.pid, signal.SIGTERM)
        if not clang_tidy_is_finished.wait(timeout=5):
          os.kill(tidy.pid, signal.SIGKILL)
        return True
      return False

    # FIXME(gbiv): When we're fully on py3 (locally, vpython3 still invokes
    # py2 for me), make timeouts not require an entire thread.
    timeout_thread = threading.Thread(target=timeout_tidy)
    timeout_thread.setDaemon(True)
    timeout_thread.start()
    try:
      stdout, _ = tidy.communicate()
    except:
      tidy.kill()
      raise
    finally:
      # We really _shouldn't_ see an exception from here unless it's
      # something like KeyboardInterrupt. Ensure clang-tidy dies anyway.
      clang_tidy_is_finished.set()
      was_killed = timeout_thread.join()

    return_code = tidy.wait()
    if was_killed:
      return_code = None

    with open(cc_file) as f:
      line_offsets = _LineOffsetMap.for_text(f.read())

    tidy_exited_regularly = return_code == 0
    try:
      with open(findings_file) as f:
        findings = list(_parse_tidy_fixes_file(line_offsets, f))
    except IOError as e:
      # If tidy died (crashed), it might not have created a file for us.
      if e.errno != errno.ENOENT or tidy_exited_regularly:
        raise
      findings = []
    except _ParseError:
      if tidy_exited_regularly:
        raise
      findings = []

    return return_code, stdout, findings


_TidyAction = collections.namedtuple('_TidyAction',
                                     ['in_dir', 'cc_file', 'flags', 'target'])


def _run_tidy_action(tidy_binary, action):
  # FIXME(gbiv): kick this out when we have a top-level .clang-tidy in
  # Chromium's tree.
  checks = [
      '*',
      '-clang-analyzer*',
  ]

  try:
    logging.info('Running clang_tidy for %r', action.target)

    start_time = time.time()
    exit_code, stdout, findings = _run_clang_tidy(
        tidy_binary, checks, action.in_dir, action.cc_file, action.flags)
    elapsed_time = time.time() - start_time

    if exit_code is None:
      logging.error('Running clang_tidy for %r timed out after %.2fs',
                    action.target, elapsed_time)
    else:
      logging.info('Running clang_tidy for %r completed after %.2fs',
                   action.target, elapsed_time)

    return exit_code, stdout, findings
  except Exception:
    # Exceptions raised in Pools have ~meaningless tracebacks after they're
    # sent to the main process.
    logging.exception('Running clang-tidy on %r', action.cc_file)
    raise


_CompileCommand = collections.namedtuple(
    '_CompileCommand',
    ['target_name', 'file_abspath', 'file', 'directory', 'command'])


def _parse_compile_commands(stream):
  compile_commands = json.load(stream)

  output_re = re.compile(r'-o\s+(\S+)')
  for action in compile_commands:
    command = action['command']
    m = output_re.search(command)
    if not m:
      raise ValueError('compile_commands action %r lacks an output' % command)

    yield _CompileCommand(
        target_name=m.group(1),
        file_abspath=os.path.abspath(
            os.path.join(action['directory'], action['file'])),
        file=action['file'],
        directory=action['directory'],
        command=command,
    )


def _chunk_iterable(iterable, chunk_size):
  this_chunk = []
  for i, e in enumerate(iterable, 1):
    this_chunk.append(e)

    if i % chunk_size == 0:
      yield this_chunk
      this_chunk = []

  if this_chunk:
    yield this_chunk


def _generate_tidy_actions(out_dir,
                           only_cc_files,
                           build_targets,
                           compile_commands,
                           build_chunk_size=500):
  """Figures out hot to lint `only_cc_files` and builds their dependencies.

  Args:
    - out_dir: the out/ directory for us to interrogate
    - only_cc_files: a set of C++ files to look at. If None, we return
      information for all of Chrome
    - build_targets: a function that takes a list of build targets, builds
      them, and returns a list of ones that failed to build.
    - compile_commands: a list of `_CompileCommand`s
    - build_chunk_size: how many targets to build at once. 500 is likely to not
      overflow argv limits.

  Returns:
    A list of `_TidyAction`s, and a list of the CC files we failed to build
    objects for.
  """
  if only_cc_files is None:
    all_cc_files = set(x.file_abspath for x in compile_commands)
    # Tricium can't display comments about generated files; ignore them.
    only_cc_files = sorted(x for x in all_cc_files if not x.startswith(out_dir))

  cc_to_target_map = collections.defaultdict(list)
  for action in compile_commands:
    cc_to_target_map[action.file_abspath].append(action.target_name)

  target_to_command_map = {}
  for action in compile_commands:
    assert action.target_name not in target_to_command_map, \
        'Multiple actions for %s in compile_commands?' % action.target_name
    target_to_command_map[action.target_name] = action

  actions = []
  for cc_file in only_cc_files:
    targets = cc_to_target_map[cc_file]
    if not targets:
      logging.error('No targets found for %r', cc_file)
      continue

    for target in targets:
      command = target_to_command_map[target]
      actions.append(
          _TidyAction(
              cc_file=cc_file,
              target=target,
              in_dir=command.directory,
              flags=command.command,
          ))

  logging.info('Loaded %d targets', len(actions))

  failing_targets = set()
  targets_built = 0
  # 500 is arbitrary. If too high, we'll start getting into argv size limits.
  for targets in _chunk_iterable((x.target for x in actions), build_chunk_size):
    logging.info('Building target(s) %d-%d / %d', targets_built,
                 targets_built + len(targets), len(actions))
    failing_targets |= set(build_targets(targets))
    targets_built += len(targets)

  if failing_targets:
    logging.error('Some targets failed: %r; soldiering on anyway...',
                  sorted(failing_targets))

  failing_cc_files = []
  for cc_file in only_cc_files:
    targets = cc_to_target_map[cc_file]
    if any(target in failing_targets for target in targets):
      failing_cc_files.append(cc_file)

  return actions, failing_cc_files


def _run_all_tidy_actions(tidy_actions, run_tidy_action, tidy_jobs,
                          clang_tidy_binary, use_threads):
  """Runs a series of tidy actions, returning the status of all of that.

  Args:
    tidy_actions: a list of clang-tidy actions to perform
    run_tidy_action: the function to call when running a tidy action. Takes a
      clang-tidy binary and a _TidyAction; returns a tuple of (exit_code,
      stdout, findings)
        - exit_code is the exit code of tidy. None if it timed out.
        - stdout is tidy's raw stdout
        - findings is a list of _TidyDiagnostic from the invocation
    tidy_jobs: how many jobs should be run in parallel
    clang_tidy_binary: the clang-tidy binary to pass into run_tidy_action
    use_threads: if True, we'll use a threadpool. Opts for a process pool
      otherwise.

  Returns:
    - A set of CC files tidy died with a non-zero exit code on
    - A set of CC files tidy timed out on
    - A set of all diags emitted by tidy throughout the run.
  """
  # Threads make sharing for testing _way_ easier. Unfortunately, YAML parsing
  # is apparently expensive, and the GIL makes it so we genuinely can't spawn
  # processes fast enough above a parallelism level of ~25.
  if use_threads:
    pool_kind = multiprocessing.pool.ThreadPool
  else:
    pool_kind = multiprocessing.Pool

  pool = pool_kind(processes=tidy_jobs)

  # Can't use pool.imap variants here due to the timeout workaround below.
  results = []
  for action in tidy_actions:
    results.append((action,
                    pool.apply_async(run_tidy_action,
                                     (clang_tidy_binary, action))))
  pool.close()

  all_findings = set()
  timed_out_cc_files = set()
  failed_cc_files = set()
  for action, result in results:
    cc_file, flags = action.cc_file, action.flags

    # Without a timeout here, signals like KeyboardInterrupt won't be
    # promptly raised. Doesn't matter what the timeout is.
    # https://bugs.python.org/issue21913
    exit_code, stdout, findings = result.get(2**30)
    if exit_code is None:
      logging.error('Clang-tidy timed out on %r with flags %r', cc_file, flags)
      timed_out_cc_files.add(cc_file)
      continue

    if exit_code:
      logging.error(
          'Clang-tidy on %r with flags %r exited with '
          'code %d; stdout/stderr: %r', cc_file, flags, exit_code, stdout)
      failed_cc_files.add(cc_file)

    # (If memory use becomes important, there's _a ton_ of duplicated
    # strings in these. Would probably be pretty trivial to intern them.)
    all_findings |= set(findings)

  pool.join()

  return failed_cc_files, timed_out_cc_files, all_findings


def _filter_invalid_findings(diags):
  """Filters findings that Tricium can do nothing with.

  Takes any iterable over _TidyDiagnostics; returns a list of the ones that
  Tricium can actually display.
  """
  good = []
  bad = []
  for diag in diags:
    if diag.file_path:
      good.append(diag)
    else:
      bad.append(diag)

  if bad:
    logging.warning('Dropping %d diagnostic(s) for tricium', len(bad))
    logging.info('They were: %s', sorted(bad))

  return good


def _normalize_path_to_base(path, base):
  assert os.path.isabs(path), '%s should be absolute' % path

  if base is None:
    return path

  if path == base:
    return '.'

  if base.endswith(os.path.sep):
    sep_base = base
  else:
    sep_base = base + os.path.sep

  if path.startswith(sep_base):
    return os.path.relpath(path, base)
  return None


def _normalize_paths_to_base(paths, base):
  normalized = (_normalize_path_to_base(p, base) for p in paths)
  return (x for x in normalized if x is not None)


def _normalize_diags_to_base(diags, base):
  normalized = (_normalize_path_to_base(d.file_path, base) for d in diags)
  return (diag._replace(file_path=n)
          for diag, n in zip(diags, normalized)
          if n is not None)


def main():
  parser = argparse.ArgumentParser(
      description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('--debug', action='store_true')
  parser.add_argument(
      '--tidy_jobs',
      type=int,
      help='Number of concurrent `clang_tidy` jobs to run')
  parser.add_argument(
      '--base_path',
      help='Base path for all files to output. Any paths that aren\'t '
      'subdirectories of this will be ignored.')
  parser.add_argument(
      '--ninja_jobs', type=int, help='Number of jobs to run `ninja` with')
  parser.add_argument(
      '--out_dir', required=True, help='Chromium out/ directory')
  parser.add_argument(
      '--findings_file', required=True, help='Where to dump findings as JSON')
  parser.add_argument('cc_file', nargs='*', help='C/C++ files to lint')
  parser.add_argument(
      '--all',
      action='store_true',
      help='Run across all C/C++ files known to ninja.')
  # FIXME: This should be removed once we decide on and productionize a
  # packaging strategy for clang-tidy. See
  # https://chromium-review.googlesource.com/c/chromium/src/+/1749646
  parser.add_argument(
      '--clang_tidy_binary', required=True, help='Path to clang-tidy')
  args = parser.parse_args()

  base_path = os.path.abspath(args.base_path)

  # Mututally exclusive arg groups apparently don't like positional args, so
  # emulate that here.
  if bool(args.cc_file) == args.all:
    parser.error('Please either specify files to lint, or pass --all')

  if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
  elif args.verbose:
    logging.getLogger().setLevel(logging.INFO)

  out_dir = os.path.abspath(args.out_dir)
  findings_file = os.path.abspath(args.findings_file)

  clang_tidy_binary = args.clang_tidy_binary

  if args.all:
    only_cc_files = None
  else:
    only_cc_files = [os.path.abspath(f) for f in args.cc_file]

    if len(set(only_cc_files)) != len(only_cc_files):
      sys.exit('Multiple identical cc_files given. This is unsupported.')

    for cc_file in only_cc_files:
      if not os.path.isfile(cc_file):
        sys.exit('Provided cc_file at %r does not exist' % cc_file)

  compile_commands_location = _generate_compile_commands(out_dir)
  with open(compile_commands_location) as f:
    tidy_actions, failed_cc_files = _generate_tidy_actions(
        out_dir,
        only_cc_files,
        build_targets=
        lambda targets: _try_build_targets(out_dir, targets, args.ninja_jobs),
        compile_commands=list(_parse_compile_commands(f)))

  if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug('Plan to tidy %s.', [x.target for x in tidy_actions])
  else:
    logging.info('Plan to tidy %d targets.', len(tidy_actions))

  # FIXME(gbiv): We might want to do something with failed_tidy_cc_files some
  # day. The issue is that a clang-tidy death can indicate all sorts of things:
  # it could be as simple as a clang -Werror diag being tripped, or clang-tidy
  # crashing on the given file outright. Teasing things like these apart so
  # they can be surfaced to the user is likely valuable.
  failed_tidy_cc_files, timed_out_cc_files, findings = _run_all_tidy_actions(
      tidy_actions,
      _run_tidy_action,
      args.tidy_jobs,
      clang_tidy_binary,
      use_threads=False)

  if failed_tidy_cc_files:
    logging.warning(
        'clang-tidy failed for some reason on the following file(s): %s',
        failed_tidy_cc_files)

  findings = _filter_invalid_findings(findings)

  # This is the object that we ship to Tricium. Comments are overdescriptive
  # so that people don't have to reason about code above in order to
  # understand what each piece of this is.
  #
  # Since the recipe is expected to normalize stuff for us, all paths returned
  # here should be absolute.
  results = {
      # A list of .cc files that we failed to build one or more targets for.
      # This could indicate that we're going to provide incomplete or incorrect
      # diagnostics, since e.g. generated headers may be missing.
      'failed_cc_files':
          sorted(_normalize_paths_to_base(failed_cc_files, base_path)),

      # A list of .cc files that we failed to tidy due to internal timeouts.
      # This should hopefully never happen, but it's *probably* good to know
      # when it's the case.
      'timed_out_cc_files':
          sorted(_normalize_paths_to_base(timed_out_cc_files, base_path)),

      # A list of all of the diagnostics we've seen in this run. They're
      # instances of `_TidyDiagnostic`.
      'diagnostics': [
          x._asdict()
          for x in sorted(_normalize_diags_to_base(findings, base_path))
      ],
  }

  # Do a two-step write, so the user can't see partial results.
  tempfile_name = findings_file + '.new'
  with open(tempfile_name, 'w') as f:
    json.dump(results, f)
  os.rename(tempfile_name, findings_file)


if __name__ == '__main__':
  sys.exit(main())
