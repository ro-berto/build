#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import argparse
import os
import re
import sys
import traceback

TOOLS_DIR = os.path.abspath(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.dirname(TOOLS_DIR)

# This adjusts sys.path, so must be done before we import other modules.
if not SCRIPTS_DIR in sys.path:  # pragma: no cover
  sys.path.append(SCRIPTS_DIR)

from common import chromium_utils
from common import env
from common import filesystem


class Tool(object):
  def __init__(self):
    self.fs = filesystem.Filesystem()
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.build_dir = env.Build
    self.build_internal_dir = env.BuildInternal

  def print_(self, *args, **kwargs):
    kwargs.setdefault('file', self.stdout)
    print(*args, **kwargs)

  def main(self, argv):
    args = self.parse_args(argv)
    return args.func(args)

  def parse_args(self, argv):
    parser = argparse.ArgumentParser()
    subps = parser.add_subparsers()

    def add_common_args(subp):
      subp.add_argument('master_dirname', nargs='*',
                        help='Path to master config directory (must contain '
                             'a builders.pyl file).')
      subp.add_argument('--external-only', action='store_true')
      subp.add_argument('--internal-only', action='store_true')

    subp = subps.add_parser('gen', help=self.run_gen.__doc__)
    add_common_args(subp)
    subp.set_defaults(func=self.run_gen)

    subp = subps.add_parser('check', help=self.run_check.__doc__)
    add_common_args(subp)
    subp.set_defaults(func=self.run_check)

    subp = subps.add_parser('help', help=self.run_help.__doc__)
    subp.add_argument(nargs='?', action='store', dest='subcommand',
                      help='The command to get help for.')
    subp.set_defaults(func=self.run_help)
    return parser.parse_args(argv)

  def run_check(self, args):
    """Checks that the master configs are up-to-date."""
    files_to_write, ret = self._generate(args)
    for path in sorted(files_to_write):
      self.print_('%s is out-of-date.' % self.fs.relpath(path))
    return 1 if files_to_write else ret

  def run_gen(self, args):
    """Generates and updates master configs."""
    files_to_write, ret = self._generate(args)
    for path in sorted(files_to_write):
      if self.fs.exists(self.fs.join(self.build_dir, self.fs.dirname(path))):
        d = self.build_dir
      else:
        d = self.build_internal_dir
      self.fs.write_text_file(self.fs.join(d, path), files_to_write[path])
      self.print_('Wrote %s.' % self.fs.relpath(path, d))
    return ret

  def run_help(self, args):
    """Get help on a subcommand."""
    if args.subcommand:
      return self.main([args.subcommand, '--help'])
    return self.main(['--help'])

  def _generate(self, args):
    files_to_write = {}
    paths = self._builders_paths(args)
    failed = False
    for path in paths:
      try:
        self._process_one_builders_file(path, files_to_write)
      except SyntaxError as e:
        msg = ''.join(traceback.format_exception_only(type(e), e))
        self.print_(msg)
        failed = True
      except chromium_utils.BuildersFileError as e:
        self.print_(e)
        failed = True

    if failed or not paths:
      return {}, 1
    return files_to_write, 0

  def _builders_paths(self, args):
    builders_paths = []
    failed = False
    fs = self.fs
    if args.master_dirname:
      for d in args.master_dirname:
        builders_path = fs.join(d, 'builders.pyl')
        if not fs.exists(builders_path):
          self.print_('%s not found' % builders_path, file=self.stderr)
          failed = True
        else:
          builders_paths.append(builders_path)
    else:
      masters_dirs = []
      if not args.internal_only:
        masters_dirs.append(fs.join(self.build_dir, 'masters'))
      if not args.external_only and self.build_internal_dir:
        masters_dirs.append(fs.join(self.build_internal_dir, 'masters'))

      for masters_dir in masters_dirs:
        for master_dir in fs.listdirs(masters_dir):
          builders_path = fs.join(masters_dir, master_dir, 'builders.pyl')
          if fs.exists(builders_path):
            builders_paths.append(builders_path)

    if failed:
      return []
    if not builders_paths:
      self.print_('No builders.pyl files found.', file=self.stderr)
      return []
    return builders_paths

  def _process_one_builders_file(self, builders_path, files_to_write):
    fs = self.fs
    out_dir = fs.dirname(builders_path)
    builders_contents = fs.read_text_file(builders_path)
    values = chromium_utils.ParseBuildersFileContents(builders_path,
                                                      builders_contents)

    template_subpath = fs.join('scripts', 'tools', 'buildbot_tool_templates')
    template_dir = fs.join(self.build_dir, template_subpath)
    for filename in fs.listfiles(template_dir):
      template = fs.read_text_file(fs.join(template_dir, filename))
      new_contents = self._expand(template, values,
                                  '%s/%s' % (template_subpath, filename))
      path = fs.join(out_dir, filename)
      if fs.exists(path) and fs.read_text_file(path) == new_contents:
        continue
      files_to_write[path] = new_contents

  def _expand(self, template, values, path):
    try:
      contents = template % values
    except:
      self.print_("Error populating template %s" % path, file=self.stderr)
      raise
    contents = self._update_generated_file_disclaimer(contents, path)
    return contents.strip() + '\n'

  def _update_generated_file_disclaimer(self, contents, path):
    pattern = '# This file is used by scripts/tools/buildbot-tool.*'
    replacement = ('# This file was generated from\n'
                   '# %s\n'
                   '# by "../../build/scripts/tools/buildbot-tool gen .".\n'
                   '# DO NOT EDIT BY HAND!\n' % path)
    return re.sub(pattern, replacement, contents)


if __name__ == '__main__':  # pragma: no cover
  tool = Tool()
  sys.exit(tool.main(sys.argv[1:]))
