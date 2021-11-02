#!/usr/bin/env vpython3
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
#    name: "infra/python/wheels/pyyaml-py3"
#    version: "version:5.3.1"
# >
# [VPYTHON:END]

import argparse
import bisect
import collections
import contextlib
import io
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
import time
from typing import (IO, Any, Callable, Dict, Generator, Iterable, List,
                    Optional, Set, Tuple, TypeVar)

import yaml

_CC_FILE_EXTENSIONS = ('.cc', '.cpp', '.c', '.cxx')
_HEADER_FILE_EXTENSIONS = ('.h', '.hpp')

_T = TypeVar('_T')


@contextlib.contextmanager
def _temp_file() -> Generator[str, None, None]:
  """Creates an unconditionally deleted temp file, yielding its path."""
  fd, path = tempfile.mkstemp(prefix='tricium_tidy')
  try:
    os.close(fd)
    yield path
  finally:
    os.unlink(path)


def _generate_compile_commands(out_dir: str) -> str:
  """Generates a compile_commands.json file, returning the path to it."""
  compile_commands = os.path.join(out_dir, 'compile_commands.json')
  # Regenerate compile_commands every time, since the user might've patched
  # files (etc.) since our previous run.
  with open(os.path.join(out_dir, 'args.gn'), encoding='utf-8') as f:
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


def _run_ninja(out_dir: str,
               phony_targets: List[str],
               object_targets: List[str],
               jobs: Optional[int] = None,
               max_targets_per_invocation: int = 500,
               force_clean: bool = True):
  """Runs ninja, returning the object_targets that failed to build.

  Args:
    out_dir: The directory to perform the build in.
    phony_targets: 'phonies' to pass into ninja. Errors in building these will
      not be reported to the caller.
    object_targets: Object files to build. Errors in building these will be
      reported to the caller.
    jobs: How many jobs to use. If None, lets `ninja` pick a value.
    max_targets_per_invocation: How many targets to build per ninja invocation.
    force_clean: If true, we'll remove all existing `object_targets` before
      building.

  Returns:
    A list of elements in `object_targets` that failed to build.
  """
  # We ideally don't want to always do clean rebuilds (crbug.com/1060168),
  # but we also use the existence of an object to determine if it successfully
  # built. Remove everything we're going to be checking ahead-of-time.
  #
  # FIXME(gbiv): We may be able to do better than this (interrogate ninja to
  # see which objects are _actually_ out-of-date?)
  if force_clean:
    for target in object_targets:
      target = os.path.join(out_dir, target)
      try:
        os.unlink(target)
      except FileNotFoundError:
        logging.info('Removed existing target at %s', target)

  # 500 targets per invocation is arbitrary, but we start hitting OS argv size
  # limits around 1K in my experience.
  #
  # In builds where both are specified, phony_targets are meant to be redundant
  # with the given object_targets. Essentially, the goal is to get ninja to
  # build more things per command, since more build actions per command lets us
  # better saturate our ninja job limit. In practice, on pathological cases
  # (e.g., base/ header changes where the file isn't built on Linux, but
  # there's no way to tell), this cuts our total wall-time by over 30% when
  # goma's cache is hot; more otherwise.

  def make_ninja_command(targets):
    ninja_cmd = ['ninja', '-k', '1000000']
    if jobs is not None:
      ninja_cmd.append('-j%d' % jobs)

    ninja_cmd.append('--')
    ninja_cmd += targets
    return ninja_cmd

  phonies_built = 0
  for phonies in _chunk_iterable(phony_targets, max_targets_per_invocation):
    logging.info("Building phonies %d-%d/%d...", phonies_built,
                 phonies_built + len(phonies), len(phony_targets))
    subprocess.call(make_ninja_command(phonies), cwd=out_dir)
    phonies_built += len(phonies)

  objects_built = 0
  objects_implicitly_built = 0

  remaining_objects = object_targets[::-1]
  while 1:
    to_build: List[str] = []
    while len(to_build) < max_targets_per_invocation and remaining_objects:
      obj = remaining_objects.pop()
      if os.path.exists(os.path.join(out_dir, obj)):
        objects_implicitly_built += 1
      else:
        to_build.append(obj)

    if not to_build:
      break

    logging.info('Building objects %d-%d/%d', objects_built,
                 objects_built + len(to_build),
                 len(object_targets) - objects_implicitly_built)
    subprocess.call(make_ninja_command(to_build), cwd=out_dir)
    objects_built += len(to_build)

  logging.info('%d/%d objects were successfully implicitly built',
               objects_implicitly_built, len(object_targets))
  return [
      x for x in object_targets if not os.path.isfile(os.path.join(out_dir, x))
  ]


# File path is omitted, since these are intended to be associated with
# _TidyDiagnostics with identical paths.
_TidyReplacement = collections.namedtuple(
    '_TidyReplacement',
    ['new_text', 'start_line', 'end_line', 'start_char', 'end_char'])

# Notes which specifically reference macro expansion.
_ExpandedFrom = collections.namedtuple('_ExpandedFrom',
                                       ['file_path', 'line_number'])


class _TidyNote(
    collections.namedtuple('_TidyNote', [
        'file_path',
        'line_number',
        'message',
        'expansion_locs',
    ])):
  """A note emitted by clang-tidy."""

  def to_dict(self) -> Dict[str, Any]:
    my_dict = self._asdict()
    my_dict['expansion_locs'] = [x._asdict() for x in my_dict['expansion_locs']]
    return my_dict


# Note that we shove these in a set for cheap deduplication, and we sort based
# on the natural element order here. Sorting is mostly just for
# deterministic/pretty output.
class _TidyDiagnostic(
    collections.namedtuple('_TidyDiagnostic', [
        'file_path',
        'line_number',
        'diag_name',
        'message',
        'replacements',
        'expansion_locs',
        'notes',
    ])):
  """A diagnostic emitted by clang-tidy"""

  def to_dict(self) -> Dict[str, Any]:
    my_dict = self._asdict()
    my_dict['replacements'] = [x._asdict() for x in my_dict['replacements']]
    my_dict['expansion_locs'] = [x._asdict() for x in my_dict['expansion_locs']]
    my_dict['notes'] = [x.to_dict() for x in my_dict['notes']]
    return my_dict


class _ParseError(Exception):

  def __init__(self, err_msg: str):
    Exception.__init__(self, err_msg)
    self.err_msg = err_msg


class _LineOffsetMap:
  """Convenient API to turn offsets in a file into line numbers."""

  def __init__(self, newline_locations: Iterable[int]):
    line_starts = sorted(x + 1 for x in newline_locations)

    if line_starts:
      assert line_starts[0] > 0, line_starts[0]
      assert line_starts[-1] < sys.maxsize, line_starts[-1]

    # Add boundaries so we don't need to worry about off-by-ones below.
    line_starts.insert(0, 0)
    line_starts.append(sys.maxsize)

    self._line_starts = line_starts

  def get_line_number(self, char_number: int) -> int:
    assert 0 <= char_number < sys.maxsize, char_number
    return bisect.bisect_right(self._line_starts, char_number)

  def get_line_offset(self, char_number: int) -> int:
    assert 0 <= char_number < sys.maxsize, char_number
    line_start_index = bisect.bisect_right(self._line_starts, char_number) - 1
    return char_number - self._line_starts[line_start_index]

  @staticmethod
  def for_text(data: str) -> '_LineOffsetMap':
    return _LineOffsetMap([m.start() for m in re.finditer(r'\n', data)])


class _DiagnosticNoteBuilder:
  """Converts a flat series of notes from YAML into a 'tree' of notes.

  Each note can have "expanded from" notes associated with it. There may also
  be "expanded from" entries associated with the top-level diagnostic.
  """

  def __init__(self):
    self._top_level_expansion_locs = []
    self._notes = []

  def push_expansion_loc(self, expanded_from: _ExpandedFrom):
    if self._notes:
      self._notes[-1].expansion_locs.append(expanded_from)
    else:
      self._top_level_expansion_locs.append(expanded_from)

  def push_tidy_note(self, file_path: str, line_number: int, message: str):
    self._notes.append(
        _TidyNote(
            file_path=file_path,
            line_number=line_number,
            message=message,
            expansion_locs=[],
        ))

  def build_top_level_expansions(self) -> Iterable[_ExpandedFrom]:
    return tuple(self._top_level_expansion_locs)

  def build_notes(self) -> Iterable[_TidyNote]:
    return tuple(
        x._replace(expansion_locs=tuple(x.expansion_locs)) for x in self._notes)


def _parse_tidy_fixes_file(read_line_offsets: Callable[[str], _LineOffsetMap],
                           stream: Any, tidy_invocation_dir: str
                          ) -> Generator[_TidyDiagnostic, None, None]:
  """Parses a clang-tidy YAML file.

  Args:
    read_line_offsets: A function that, given a file name, returns a
      _LineOffsetMap for the file.
    stream: A file containing the clang-tidy nits we want to parse.
    tidy_invocation_dir: The directory clang-tidy was run in.

  Returns:
    A generator of `_TidyDiagnostic`s.
  """
  assert os.path.isabs(tidy_invocation_dir)

  try:
    findings = yaml.load(stream)
  except (yaml.parser.ParserError, yaml.reader.ReaderError) as v:
    raise _ParseError('Broken yaml: %s' % v) from v

  if findings is None:
    return

  cached_line_offsets: Dict[str, _LineOffsetMap] = {}

  def get_line_offsets(file_path):
    assert not file_path or os.path.isabs(file_path), file_path

    if file_path in cached_line_offsets:
      return cached_line_offsets[file_path]

    # Sometimes tidy will give us empty file names; they don't map to any file,
    # and are generally issues it has with CFLAGS, etc. File offsets don't
    # matter in those, so use an empty map.
    if file_path:
      offsets = read_line_offsets(file_path)
    else:
      offsets = _LineOffsetMap([])
    cached_line_offsets[file_path] = offsets
    return offsets

  # Rarely (e.g., in the case of missing `#include`s, clang will emit relative
  # file paths for diagnostics. This fixes those.
  def makeabs(file_path):
    if not file_path or os.path.isabs(file_path):
      return file_path
    return os.path.abspath(os.path.join(tidy_invocation_dir, file_path))

  try:
    for diag in findings['Diagnostics']:
      message = diag['DiagnosticMessage']
      file_path = message['FilePath']

      absolute_file_path = makeabs(file_path)
      line_offsets = get_line_offsets(absolute_file_path)
      line_offsets = cached_line_offsets[absolute_file_path]

      replacements = []
      for replacement in message.get('Replacements', ()):
        replacement_file_path = replacement['FilePath']

        # Some checkers like modernize-use-default-member-init like to emit
        # fixits at a distance. This is also possible with files meant to be
        # `#include`d at strange places, like:
        # ```
        # #define FOO(a) case keys(a): return values(a)
        # #include "all_items.inc"
        # #undef FOO
        # ```
        if replacement_file_path != file_path:
          logging.warning(
              'Dropping replacement at %r, since it wasn\'t in the file with '
              'the original diagnostic (%r)', replacement_file_path, file_path)
          continue

        start_offset = replacement['Offset']
        end_offset = start_offset + replacement['Length']
        replacements.append(
            _TidyReplacement(
                new_text=replacement['ReplacementText'],
                start_line=line_offsets.get_line_number(start_offset),
                end_line=line_offsets.get_line_number(end_offset),
                start_char=line_offsets.get_line_offset(start_offset),
                end_char=line_offsets.get_line_offset(end_offset),
            ))

      notes_builder = _DiagnosticNoteBuilder()
      for note in diag.get('Notes', ()):
        absolute_note_path = makeabs(note['FilePath'])
        note_offsets = get_line_offsets(absolute_note_path)
        line_number = note_offsets.get_line_number(note['FileOffset'])
        note_message = note['Message']
        if note_message.startswith('expanded from macro '):
          notes_builder.push_expansion_loc(
              _ExpandedFrom(
                  file_path=absolute_note_path,
                  line_number=line_number,
              ))
        else:
          notes_builder.push_tidy_note(
              file_path=absolute_note_path,
              line_number=line_number,
              message=note_message,
          )

      yield _TidyDiagnostic(
          diag_name=diag['DiagnosticName'],
          message=message['Message'],
          file_path=absolute_file_path,
          line_number=line_offsets.get_line_number(message['FileOffset']),
          replacements=tuple(replacements),
          expansion_locs=notes_builder.build_top_level_expansions(),
          notes=notes_builder.build_notes(),
      )
  except KeyError as k:
    key_name = k.args[0]
    raise _ParseError('Broken yaml: missing key %r' % key_name) from k


def _run_clang_tidy(clang_tidy_binary: str, checks: Optional[str], in_dir: str,
                    cc_file: str, compile_command: str
                   ) -> Tuple[Optional[int], str, List[_TidyDiagnostic]]:
  with _temp_file() as findings_file:
    command = [clang_tidy_binary]

    if checks is not None:
      command.append('-checks=' + checks)

    command += [
        cc_file,
        '--export-fixes=%s' % findings_file,
        '--header-filter=.*',
        '--',
    ]
    command.extend(shlex.split(compile_command))

    logging.debug('In %r, running %s', in_dir,
                  ' '.join(pipes.quote(c) for c in command))

    try:
      tidy = subprocess.run(
          command,
          check=False,
          cwd=in_dir,
          stdin=subprocess.DEVNULL,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          encoding='utf-8',
          errors='replace',
          # When run on everything built for an Android out/ directory,
          # clang-tidy takes 27s on average per TU with
          # checks='*,-clang-analyzer*'. The worst 3 times were 251s, 264s,
          # and 1220s (~20 mins). The last time was clang-tidy running over a
          # 57KLOC cc file that boils down to a few massive arrays.
          #
          # In any case, 30mins seems like plenty.
          timeout=30 * 60,
      )

      return_code: Optional[int] = tidy.returncode
      stdout = tidy.stdout
    except FileNotFoundError:
      logging.error('Failed to spawn clang-tidy -- is it installed?')
      raise
    except subprocess.TimeoutExpired as e:
      return_code = None
      stdout = e.stdout

    def read_line_offsets(file_path):
      with open(file_path, encoding='utf-8') as f:
        return _LineOffsetMap.for_text(f.read())

    tidy_exited_regularly = return_code == 0
    try:
      with open(findings_file, encoding='utf-8', errors='replace') as f:
        findings = list(_parse_tidy_fixes_file(read_line_offsets, f, in_dir))
    except FileNotFoundError:
      # If tidy died (crashed), it might not have created a file for us.
      if tidy_exited_regularly:
        raise
      findings = []
    except _ParseError:
      if tidy_exited_regularly:
        raise
      findings = []

    return return_code, stdout, findings


_TidyAction = collections.namedtuple('_TidyAction',
                                     ['in_dir', 'cc_file', 'flags', 'target'])


def _run_tidy_action(
    tidy_binary: str, checks: Optional[str], action: _TidyAction
) -> Optional[Tuple[Optional[int], str, List[_TidyDiagnostic]]]:
  """Runs clang-tidy, given a _TidyAction.

  The return value here is a bit complicated:
    - None: an unexpected Exception happened, and was logged.
    - (exit_code, stdout, findings):
      - if exit_code is None, clang-tidy timed out; stdout has contents, but
        findings is probably senseless.
      - if exit_code is not None, clang-tidy terminated with the returned
        exit-code.
  """
  try:
    logging.info('Running clang_tidy for %r', action.target)

    start_time = time.time()
    exit_code, stdout, findings = _run_clang_tidy(
        clang_tidy_binary=tidy_binary,
        checks=checks,
        in_dir=action.in_dir,
        cc_file=action.cc_file,
        compile_command=action.flags)
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
    # A `None` exit-code is a timeout; return `None` instead of a tuple to
    # indicate that things blew up spectacularly. Don't `raise`, since that
    # can apparently cause great confusion for `multiprocessing`
    # (crbug.com/1034646).
    return None


_CompileCommand = collections.namedtuple(
    '_CompileCommand',
    ['target_name', 'file_abspath', 'file', 'directory', 'command'])


def _parse_compile_commands(stream: io.TextIOWrapper
                           ) -> Generator[_CompileCommand, None, None]:
  """Parses compile commands from the given input stream."""
  compile_commands = json.load(stream)

  for action in compile_commands:
    command = action['command']

    # Skip all pnacl compile commands: crbug.com/1041079
    pnacl = 'pnacl-'
    if pnacl in command:
      pieces = shlex.split(command)
      if pieces:
        first_piece = os.path.basename(pieces[0])
        if pnacl in first_piece:
          continue

        if (len(pieces) > 1 and 'goma' in first_piece and
            pnacl in os.path.basename(pieces[1])):
          continue

    m = re.search(r'-o\s+(\S+)', command)
    if not m:
      raise ValueError('compile_commands action %r lacks an output file' %
                       command)

    yield _CompileCommand(
        target_name=m.group(1),
        file_abspath=os.path.abspath(
            os.path.join(action['directory'], action['file'])),
        file=action['file'],
        directory=action['directory'],
        command=command,
    )


def _chunk_iterable(iterable: Iterable[_T],
                    chunk_size: int) -> Generator[List[_T], None, None]:
  this_chunk = []
  for i, e in enumerate(iterable, 1):
    this_chunk.append(e)

    if i % chunk_size == 0:
      yield this_chunk
      this_chunk = []

  if this_chunk:
    yield this_chunk


def _parse_ninja_deps_output(input_stream: IO[str], cwd: str
                            ) -> Generator[Tuple[str, List[str]], None, None]:
  """Parses the output of `ninja -t deps`.

  Yields successive tuples of (object_file, [file_it_depends_on]). Ignores any
  stale deps entries, since they might have incorrect information.

  `object_file`s are all relative to out_dir; all `file_it_depends_on`s are
  absolute.
  """
  # If current_target is None, the target we're parsing is either nonexistent
  # or stale. `current_target is not None` also implies that `all_deps` is a
  # valid List object.
  current_target: Optional[str] = None
  all_deps: Optional[List[str]] = None
  for line in input_stream:
    line = line.rstrip()
    if not line:
      continue

    # ninja's deplog format looks like:
    # obj/foo.o: #deps 43, deps mtime 123456 (STALE)
    #   ../../file/foo/depends/on/one.h
    #   ../../file/foo/depends/on/two.h
    #
    # As one might infer, '(STALE)' is only printed if the deps are potentially
    # stale, and the files that `foo.o` depends on are printed with an indent
    # under the first line.
    if not line[0].isspace():
      if current_target is not None:
        assert all_deps is not None
        yield current_target, all_deps

      if line.endswith('(STALE)'):
        current_target = None
        all_deps = None
      else:
        current_target = line.rsplit(':', 1)[0]
        all_deps = []
      continue

    if all_deps is not None:
      all_deps.append(os.path.join(cwd, line.lstrip()))

  if current_target is not None:
    assert all_deps is not None
    yield current_target, all_deps


def _parse_ninja_deps(out_dir: str
                     ) -> Generator[Tuple[str, List[str]], None, None]:
  """Runs and parses the output of `ninja -t deps`.

  Yields successive tuples of (object_file, [file_it_depends_on]). Ignores any
  stale deps entries, since they might have incorrect information.

  `object_file`s are all relative to out_dir; all `file_it_depends_on`s are
  absolute.
  """
  command = ['ninja', '-t', 'deps']
  ninja = subprocess.Popen(
      command, cwd=out_dir, stdout=subprocess.PIPE, encoding='utf-8')
  try:
    assert ninja.stdout is not None
    for val in _parse_ninja_deps_output(ninja.stdout, out_dir):
      yield val
  except:
    ninja.kill()
    raise
  finally:
    if ninja.poll() is None:
      # If ninja is in the process of exiting, let it.
      time.sleep(1)
      if ninja.poll() is None:
        ninja.kill()
        ninja.wait()

  if ninja.returncode:
    raise subprocess.CalledProcessError(ninja.returncode, command)


# `gn desc` dumps a ton of information about the structure of Chromium's build
# targets. The bits we're most interested in are build targets, and the source
# files that said build targets contain. This lets us make accurate guesses
# about relationships between source files (for example, which cc_files are
# likely to include a particular header file).
class _GnDesc:
  """Represents the output of `gn desc` in an efficiently-usable manner."""

  def __init__(self, per_target_srcs: Dict[str, List[str]]):
    self._per_target_srcs = per_target_srcs

    targets_containing = collections.defaultdict(list)
    for target, srcs in per_target_srcs.items():
      for src in srcs:
        targets_containing[src].append(target)
    self._targets_containing = targets_containing

  def targets_containing(self, src_file: str) -> Iterable[str]:
    return self._targets_containing.get(src_file, ())

  def source_files_for_target(self, target: str) -> Iterable[str]:
    return self._per_target_srcs.get(target, ())


def _parse_gn_desc_output(full_desc: Dict[str, Any],
                          chromium_root: str) -> _GnDesc:
  """Given the full, parsed output of `gn desc`, generates a _GnDesc object."""
  per_target_srcs = {}
  for target, val in full_desc.items():
    all_srcs = val.get('sources')
    if not all_srcs:
      continue

    srcs = []
    for src in all_srcs:
      assert src.startswith('//'), src
      srcs.append(os.path.join(chromium_root, src[2:]))
    per_target_srcs[target] = srcs

  return _GnDesc(per_target_srcs)


def _parse_gn_desc(out_dir: str, chromium_root: str) -> _GnDesc:
  logging.info('Parsing gn desc...')

  command = ['gn', 'desc', '.', '//*:*', '--format=json']
  gn_desc = subprocess.Popen(
      command, stdout=subprocess.PIPE, cwd=out_dir, encoding='utf-8')
  assert gn_desc.stdout is not None
  full_desc = json.load(gn_desc.stdout)
  return_code = gn_desc.wait()
  if return_code:
    raise subprocess.CalledProcessError(return_code, command)
  return _parse_gn_desc_output(full_desc, chromium_root)


def _buildable_src_files_for(src_file: str,
                             cc_to_target_map: Dict[str, List[str]],
                             gn_desc: _GnDesc) -> List[str]:
  """Returns cc_files that might depend on the given src_file.

  Args:
    src_file: the path to the source file we care about.
    cc_to_target_map: a map of {src_file_abs_path: [target_name]} from
      compile_commands.json.
    gn_desc: a _GnDesc describing our build tree.

  Returns:
    All results are source files that might depend on src_file, in the order of
    more => less likely to contain src_file. This is presented as a list of
    lists; the intent is that the first sublist should be explored entirely
    before the second, etc.
  """
  if src_file in cc_to_target_map:
    return [src_file]

  no_suffix, suffix = os.path.splitext(src_file)
  if suffix not in _HEADER_FILE_EXTENSIONS:
    return []

  renames = [no_suffix + x for x in _CC_FILE_EXTENSIONS]
  targets = gn_desc.targets_containing(src_file)
  same_target_srcs: List[str] = []
  for targ in targets:
    same_target_srcs += gn_desc.source_files_for_target(targ)

  seen = set()
  result = []
  for path in renames + same_target_srcs:
    if path in seen:
      continue

    seen.add(path)
    if path in cc_to_target_map:
      result.append(path)

  return result


def _perform_build(out_dir: str, run_ninja: Any, parse_ninja_deps: Callable[
    [str], Generator[Tuple[str, List[str]], None, None]],
                   cc_to_target_map: Dict[str, List[str]], gn_desc: _GnDesc,
                   potential_src_cc_file_deps: Dict[str, List[str]]
                  ) -> Tuple[Dict[str, List[str]], List[str]]:
  """Performs a build, collecting info pertinent to clang-tidy's interests.

  Args:
    out_dir: the out/ directory for us to target with the build.
    run_ninja: a function that runs `ninja` on the given targets. Takes three
      kwargs:
        out_dir: the out dir mentioned above.
        phony_targets: a list of phony ninja targets to build.
        object_targets: a list of file-backed ninja targets to build.
      Builds them all, returns a best-effort subset of `object_targets` that
      failed.
    parse_ninja_deps: given an out_dir, yields non-stale ninja deps.
    cc_to_target_map: a mapping of cc_files -> [targets_built_by_it].
    potential_src_cc_file_deps: A mapping of
      {src_files_to_generate_build_artifacts_for:
        [buildable_srcs_that_may_include_the_key]}.
      See-also _buildable_src_files_for.

  Returns a tuple of:
    - Reverse-dependency information (i.e., a mapping of src_files -> targets
      that included them, as reported by ninja). This reverse-dependency
      information may not be complete if the build partially failed, or if
      src_files_to_cc_files_map didn't mention a cc_file that actually
      #includes a given src_file.
    - A list of targets that failed to build.
  """

  def parse_deps(only_targets, interesting_src_files):
    logging.info('Parsing deps...')
    src_file_to_target_map = collections.defaultdict(set)
    for target, src_files in parse_ninja_deps(out_dir):
      if only_targets is not None and target not in only_targets:
        continue

      for src_file in src_files:
        src_file = os.path.abspath(src_file)
        if src_file in interesting_src_files:
          src_file_to_target_map[src_file].add(target)

    logging.info('Dep parsing complete')
    return src_file_to_target_map

  cc_files_to_build = {
      cc_file for cc_files in potential_src_cc_file_deps.values()
      for cc_file in cc_files
  }

  all_targets = {
      x for cc_file in cc_files_to_build for x in cc_to_target_map[cc_file]
  }

  # NOTE: a single target can force the build of a lot of dependencies. Picking
  # a good heuristic here for which targets to build is difficult. In practice,
  # the reduced parallelism here isn't a huge problem as long as
  # len(object_targets) is, say, <1.5K files, which should be the
  # overwhelmingly common case.
  failed_targets = run_ninja(
      out_dir=out_dir, phony_targets=[], object_targets=sorted(all_targets))

  src_file_to_target_map = parse_deps(
      only_targets=all_targets,
      interesting_src_files=potential_src_cc_file_deps)

  # As a special case, we know that files depend on themselves. This lets us
  # more reliably report broken source files (since a failed compilation
  # might not produce dependency info).
  for src_file, cc_files in potential_src_cc_file_deps.items():
    if src_file in cc_files:
      src_file_to_target_map[src_file].update(cc_to_target_map[src_file])

  still_missing = {
      src_file for src_file in potential_src_cc_file_deps
      if src_file not in src_file_to_target_map
  }

  def likely_found_by_all_build(src_file: str) -> bool:
    # It's possible for .cc files to be in `still_missing` if they're only
    # built for certain OSes. It's highly unlikely that an `all` build will
    # reveal users of them, so we skip this if .cc files are all that we're
    # missing dependency info for.
    if os.path.splitext(src_file)[1] in _CC_FILE_EXTENSIONS:
      return False

    # Otherwise, if we found nothing that _might_ depend on the file, just
    # assume that it's not built on this target and move on.
    return bool(potential_src_cc_file_deps[src_file])

  likely_found = sorted(
      x for x in still_missing if likely_found_by_all_build(x))

  logging.info(
      'Still missing deps for %r, of which, %r may be used if we build `all`.',
      sorted(still_missing), likely_found)

  # Heuristics failed, so some header files don't have a cc_file that depends
  # on them. Build the world in a last-ditch effort to see if we can find
  # candidates.
  if likely_found:
    logging.info('Falling back to a full build')
    # It's not super easy (and probably not very valuable?) to pick out all of
    # the failures here. If any source files fail, let them fail silently.
    run_ninja(out_dir=out_dir, phony_targets=['all'], object_targets=[])

    missing_deps = parse_deps(
        only_targets=None, interesting_src_files=still_missing)

    shared = set(src_file_to_target_map.keys()) & set(missing_deps.keys())
    assert len(shared) == 0, shared
    src_file_to_target_map.update(missing_deps)

  return src_file_to_target_map, failed_targets


def _generate_tidy_actions(
    out_dir: str,
    only_src_files: Optional[List[str]],
    run_ninja: Any,
    parse_ninja_deps: Callable[[str],
                               Generator[Tuple[str, List[str]], None, None]],
    gn_desc: _GnDesc,
    compile_commands: List[_CompileCommand],
    max_tidy_actions_per_file: int = 16) -> Any:
  """Figures out how to lint `only_src_files` and builds their dependencies.

  Args:
    out_dir: the out/ directory for us to interrogate.
    only_src_files: a list of C++ files to look at. If None, we pretend you
      passed in every C/C++ file in compile_commands, ignoring generated
      targets.
    run_ninja: forwarded to _perform_build; please see comments there.
    parse_ninja_deps: a function that, given an out_dir, yields non-stale ninja
      deps.
    gn_desc: a _GnDesc object describing our world.
    compile_commands: a list of `_CompileCommand`s.
    max_tidy_actions_per_file: the maximum number of `_TidyAction`s to emit
      per src_file.

  Returns:
    A tuple of:
      - A map of _TidyActions to the list of the file(s) in `only_src_files`
        that the given _TidyAction lints.
      - A list of _TidyActions that we failed to build the corresponding
        `cc_file` for.
  """
  if only_src_files is None:
    all_src_files = set(x.file_abspath for x in compile_commands)
    # Tricium can't display comments about generated files; ignore them.
    only_src_files = sorted(
        x for x in all_src_files if not x.startswith(out_dir))

  cc_to_target_map = collections.defaultdict(list)
  target_to_cc_map = {}
  for action in compile_commands:
    cc_to_target_map[action.file_abspath].append(action.target_name)
    target_to_cc_map[action.target_name] = action.file_abspath

  target_to_command_map = {}
  for action in compile_commands:
    assert action.target_name not in target_to_command_map, \
        'Multiple actions for %s in compile_commands?' % action.target_name
    target_to_command_map[action.target_name] = action

  potential_src_cc_file_deps = {
      src_file: _buildable_src_files_for(src_file, cc_to_target_map, gn_desc)
      for src_file in only_src_files
  }

  src_file_to_target_map, failed_targets = _perform_build(
      out_dir, run_ninja, parse_ninja_deps, cc_to_target_map, gn_desc,
      potential_src_cc_file_deps)

  actions = collections.defaultdict(list)
  for src_file in only_src_files:
    dependent_cc_files = list({
        target_to_cc_map[x]
        for x in src_file_to_target_map[src_file]
        # Since we filter out some build actions (e.g., pnacl), things that we
        # don't know about may get built.
        if x in target_to_cc_map
    })
    if not dependent_cc_files:
      logging.error('No targets found for %r', src_file)
      continue

    priorities = {
        x: i for i, x in enumerate(potential_src_cc_file_deps[src_file])
    }

    # Sort by priority; in the case of unexpected dependencies, just use the
    # file name.
    dependent_cc_files.sort(
        key=lambda x: (priorities.get(x, len(priorities)), x))

    tidy_targets = []
    for cc_file in dependent_cc_files:
      for target in cc_to_target_map[cc_file]:
        tidy_targets.append((cc_file, target))

    if len(tidy_targets) > max_tidy_actions_per_file:
      tidy_targets = tidy_targets[:max_tidy_actions_per_file]

    for cc_file, target in tidy_targets:
      command = target_to_command_map[target]
      tidy_action = _TidyAction(
          cc_file=cc_file,
          target=target,
          in_dir=command.directory,
          flags=command.command,
      )
      actions[tidy_action].append(src_file)

  return actions, sorted(x for x in actions if x.target in failed_targets)


def _run_one_tidy_action(args):
  """Runs a single tidy action in a thread or process pool."""
  run_tidy_action, clang_tidy_binary, clang_tidy_checks, action = args
  return action, run_tidy_action(clang_tidy_binary, clang_tidy_checks, action)


def _run_all_tidy_actions(
    tidy_actions: List[_TidyAction],
    run_tidy_action: Callable[[str, Optional[str], _TidyAction],
                              Tuple[Optional[int], str, List[_TidyDiagnostic]]],
    tidy_jobs: int, clang_tidy_binary: str, clang_tidy_checks: Optional[str],
    use_threads: bool
) -> Tuple[Set[_TidyAction], Set[_TidyAction], Set[_TidyDiagnostic]]:
  """Runs a series of tidy actions, returning the status of all of that.

  Args:
    tidy_actions: a list of clang-tidy actions to perform.
    run_tidy_action: the function to call when running a tidy action. Takes a
      clang-tidy binary, a list of clang-tidy checks, and a _TidyAction;
      returns a tuple of (exit_code, stdout, findings):
        - exit_code is the exit code of tidy. None if it timed out.
        - stdout is tidy's raw stdout.
        - findings is a list of _TidyDiagnostic from the invocation.
    tidy_jobs: how many jobs should be run in parallel.
    clang_tidy_binary: the clang-tidy binary to pass into run_tidy_action.
    clang_tidy_checks: the set of checks to pass to clang-tidy. If None, no
      explicit check list will be passed.
    use_threads: if True, we'll use a threadpool. Opts for a process pool
      otherwise.

  Returns:
    - A set of _TidyActions where tidy died with a non-zero exit code.
    - A set of _TidyActions that tidy timed out on.
    - A set of all diags emitted by tidy throughout the run.
  """
  # Threads make sharing for testing _way_ easier. Unfortunately, YAML parsing
  # is expensive, and the GIL starts blocking us from spawning new clang-tidies
  # once parallelism is high enough (-j25-ish).
  if use_threads:
    pool: Any = multiprocessing.pool.ThreadPool(processes=tidy_jobs)
  else:
    pool = multiprocessing.Pool(processes=tidy_jobs)

  results = pool.imap_unordered(
      _run_one_tidy_action,
      ((run_tidy_action, clang_tidy_binary, clang_tidy_checks, action)
       for action in tidy_actions))
  pool.close()

  all_findings = set()
  timed_out_actions = set()
  failed_actions = set()
  for action, invocation_result in results:
    src_file, flags = action.cc_file, action.flags
    if not invocation_result:
      # Assume that we logged the exception from another thread.
      logging.error(
          'Clang-tidy on %r with flags %r died with an unexpected exception',
          src_file, flags)
      failed_actions.add(action)
      continue

    exit_code, stdout, findings = invocation_result
    if exit_code is None:
      logging.error('Clang-tidy timed out on %r with flags %r', src_file, flags)
      timed_out_actions.add(action)
      continue

    if exit_code:
      logging.error(
          'Clang-tidy on %r with flags %r exited with '
          'code %d; stdout/stderr: %r', src_file, flags, exit_code, stdout)
      failed_actions.add(action)

    # (If memory use becomes important, there's _a ton_ of duplicated
    # strings in these. Would probably be pretty trivial to intern them.)
    all_findings.update(findings)

  pool.join()

  return failed_actions, timed_out_actions, all_findings


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


def _normalize_path_to_base(path: str, base: str) -> Optional[str]:
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


def _convert_tidy_output_json_obj(base_path: str,
                                  tidy_actions: Dict[_TidyAction, str],
                                  failed_actions: Iterable[_TidyAction],
                                  failed_tidy_actions: Iterable[_TidyAction],
                                  timed_out_actions: Iterable[_TidyAction],
                                  findings: Iterable[_TidyDiagnostic],
                                  only_src_files: Iterable[str]) -> Any:
  """Converts the results of this run into a JSON-serializable object.

  Args:
    base_path: The base path to the Chromium checkout. All output paths will
      be made relative to this. Any paths outside of it will be discarded.
    tidy_actions: The mapping of {_TidyAction: source_files_it_covers}.
    failed_actions: _TidyActions for which we failed to build one or more
      source files that the tidy action covers.
    failed_tidy_actions: _TidyActions for which tidy exited with an error.
    timed_out_actions: _TidyActions that we timed out while executing.
    findings: A collection of all clang-tidy diagnostics we observed.
    only_src_files: A collection of src_files we care about. If not-None, we'll
      drop any diagnostics that aren't in this collection. These paths are
      expected to be absolute.

  Returns:
    A JSON object that represents the entire result of this script.
  """
  if failed_tidy_actions:
    logging.warning(
        'clang-tidy failed for some reason on the following file(s): %s',
        sorted(x.cc_file for x in failed_tidy_actions))

  findings = _filter_invalid_findings(findings)

  def normalized_src_files_for_actions(tidy_actions_subset):
    seen = set()
    for action in tidy_actions_subset:
      for src_file in tidy_actions[action]:
        if src_file in seen:
          continue

        seen.add(src_file)
        normalized_path = _normalize_path_to_base(src_file, base_path)
        yield src_file, normalized_path

  failed_src_files = []
  for src_file, normalized_path in normalized_src_files_for_actions(
      failed_actions):
    if normalized_path is None:
      logging.info('Dropping failed src file %s in normalization', src_file)
    else:
      failed_src_files.append(normalized_path)

  failed_tidy_files = []
  for src_file, normalized_path in normalized_src_files_for_actions(
      failed_tidy_actions):
    if normalized_path is None:
      logging.info('Dropping failed src (tidy) file %s in normalization',
                   src_file)
    else:
      failed_tidy_files.append(normalized_path)

  timed_out_src_files = []
  for src_file, normalized_path in normalized_src_files_for_actions(
      timed_out_actions):
    if normalized_path is None:
      logging.info('Dropping timed out src file %s in normalization', src_file)
    else:
      timed_out_src_files.append(normalized_path)

  def normalize_expansion_locs(expansion_locs):
    results = []
    for loc in expansion_locs:
      n = _normalize_path_to_base(loc.file_path, base_path)
      if n is None:
        logging.warning('Failed to normalize expansion loc path %s',
                        loc.file_path)
        # Dropping `expansion_loc`s, with machine-specific path-y parts to
        # them seems worse than keeping them around. At the moment, they're
        # only ultimately used so we can present better diagnostics to the
        # user, so there's no _hard_ requirement for them all to be relative to
        # a specific place.
        results.append(loc)
      else:
        results.append(loc._replace(file_path=n))
    return tuple(results)

  all_diagnostics = []
  for diag in findings:
    normalized_path = _normalize_path_to_base(diag.file_path, base_path)
    if normalized_path is None:
      logging.info('Dropping out-of-base diagnostic from %s', diag.file_path)
      continue

    normalized_notes = []
    for note in diag.notes:
      # Sometimes, notes won't have an associated file-path. Drop those.
      if not note.file_path:
        logging.info('Dropping note with no file path: %r', note)
        continue

      n = _normalize_path_to_base(note.file_path, base_path)
      if n is None:
        logging.info('Dropping out-of-base note from %s', note.file_path)
        continue
      normalized_notes.append(
          note._replace(
              file_path=n,
              expansion_locs=normalize_expansion_locs(note.expansion_locs),
          ))

    all_diagnostics.append(
        diag._replace(
            file_path=normalized_path,
            expansion_locs=normalize_expansion_locs(diag.expansion_locs),
            notes=tuple(normalized_notes),
        ))

  if only_src_files is not None:
    src_file_filter = set()

    for path in only_src_files:
      normalized_path = _normalize_path_to_base(path, base_path)
      if not normalized_path:
        logging.error("Got only_src_file %r, which isn't relative to base @ %r",
                      path, base_path)
      else:
        src_file_filter.add(normalized_path)

    new_diagnostics = [
        x for x in all_diagnostics if x.file_path in src_file_filter
    ]
    logging.info('Dropping %d/%d diagnostics outside of only_src_files',
                 len(all_diagnostics) - len(new_diagnostics),
                 len(all_diagnostics))
    all_diagnostics = new_diagnostics

  # This is the object that we ship to Tricium. Comments are overdescriptive
  # so that people don't have to reason about code above in order to
  # understand what each piece of this is.
  #
  # Since the recipe is expected to normalize stuff for us, all paths returned
  # here should be absolute.
  return {
      # A list of .cc files that clang-tidy exited with an error on for any
      # reason. There may be substantial overlap between this and
      # 'failed_src_files', since generally a build failure implies a
      # clang-tidy failure.
      'failed_tidy_files': sorted(set(failed_tidy_files)),

      # A list of .cc files that we failed to build one or more targets for.
      # This could indicate that we're going to provide incomplete or incorrect
      # diagnostics, since e.g. generated headers may be missing.
      'failed_src_files': sorted(set(failed_src_files)),

      # A list of .cc files that we failed to tidy due to internal timeouts.
      # This should hopefully never happen, but it's *probably* good to know
      # when it's the case.
      'timed_out_src_files': sorted(set(timed_out_src_files)),

      # A list of all of the diagnostics we've seen in this run. They're
      # instances of `_TidyDiagnostic`.
      'diagnostics': [x.to_dict() for x in all_diagnostics],
  }


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
      required=True,
      help='Base path for all files to output. Any paths that aren\'t '
      'subdirectories of this will be ignored. Also the root of your gn build '
      'tree.')
  parser.add_argument(
      '--ninja_jobs', type=int, help='Number of jobs to run `ninja` with')
  parser.add_argument(
      '--out_dir', required=True, help='Chromium out/ directory')
  parser.add_argument(
      '--findings_file', required=True, help='Where to dump findings as JSON')
  parser.add_argument('src_file', nargs='*', help='C/C++ files to lint')
  parser.add_argument(
      '--all',
      action='store_true',
      help='Run across all C/C++ files known to ninja.')
  parser.add_argument(
      '--clang_tidy_binary', required=True, help='Path to clang-tidy')
  # We rely on `os.path.exists(object_file)` to determine if the object file
  # successfully built at times. This option should only be used if we're 100%
  # sure that everything in the out dir was built perfectly from the precise
  # source tree we're looking at.
  parser.add_argument(
      '--no_clean',
      dest='clean',
      action='store_false',
      help='Keep existing object files around. Handle with care: this might '
      'cause the production of invalid diagnostics.')
  parser.add_argument(
      '--tidy_checks',
      help="An explicit value for clang-tidy's -checks=${foo} argument. If "
      'none is provided, clang-tidy will gather a check list from '
      '.clang-tidy files in the source tree.')
  args = parser.parse_args()

  base_path = os.path.realpath(args.base_path)
  if not os.path.isfile(os.path.join(base_path, 'BUILD.gn')):
    parser.error('base_path should be pointing to a gn build root. Did you '
                 'mean to point to %s/src/?' % base_path)

  # Mututally exclusive arg groups apparently don't like positional args, so
  # emulate that here.
  if bool(args.src_file) == args.all:
    parser.error('Please either specify files to lint, or pass --all')

  logging.basicConfig(
      format='%(asctime)s: %(levelname)s: %(filename)s@%(lineno)d: %(message)s',
      level=logging.DEBUG if args.debug else logging.INFO,
  )

  out_dir = os.path.abspath(args.out_dir)
  findings_file = os.path.abspath(args.findings_file)
  clang_tidy_binary = os.path.abspath(args.clang_tidy_binary)

  if args.all:
    only_src_files = None
  else:
    only_src_files = [os.path.realpath(f) for f in args.src_file]

    if len(set(only_src_files)) != len(only_src_files):
      sys.exit('Multiple identical src_files given. This is unsupported.')

    for src_file in only_src_files:
      if not os.path.isfile(src_file):
        sys.exit('Provided src_file at %r does not exist' % src_file)

  compile_commands_location = _generate_compile_commands(out_dir)

  def run_ninja(out_dir, phony_targets, object_targets):
    return _run_ninja(
        out_dir,
        phony_targets,
        object_targets,
        jobs=args.ninja_jobs,
        force_clean=args.clean)

  with open(compile_commands_location, encoding='utf-8') as f:
    tidy_actions, failed_actions = _generate_tidy_actions(
        out_dir,
        only_src_files,
        run_ninja,
        _parse_ninja_deps,
        gn_desc=_parse_gn_desc(out_dir, base_path),
        compile_commands=list(_parse_compile_commands(f)))

  if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug('Plan to tidy %s.', [x.target for x in tidy_actions])
    logging.debug('File mappings are: %s',
                  {x.target: y for x, y in tidy_actions.items()})
  else:
    logging.info('Plan to tidy %d targets.', len(tidy_actions))

  # FIXME(gbiv): We might want to do something with failed_tidy_src_files some
  # day. The issue is that a clang-tidy death can indicate all sorts of things:
  # it could be as simple as a clang -Werror diag being tripped, or clang-tidy
  # crashing on the given file outright. Teasing things like these apart so
  # they can be surfaced to the user is likely valuable.
  failed_tidy_actions, timed_out_actions, findings = _run_all_tidy_actions(
      tidy_actions,
      _run_tidy_action,
      args.tidy_jobs,
      clang_tidy_binary,
      args.tidy_checks,
      use_threads=False)

  results = _convert_tidy_output_json_obj(base_path, tidy_actions,
                                          failed_actions, failed_tidy_actions,
                                          timed_out_actions, findings,
                                          only_src_files)

  # Do a two-step write, so the user can't see partial results.
  tempfile_name = findings_file + '.new'
  with open(tempfile_name, 'w', encoding='utf-8') as f:
    json.dump(results, f)
  os.rename(tempfile_name, findings_file)


if __name__ == '__main__':
  sys.exit(main())
