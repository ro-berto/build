#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import argparse
import ast
import os
import re
import sys


TOOLS_DIR = os.path.abspath(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.dirname(TOOLS_DIR)
BASE_DIR = os.path.dirname(SCRIPTS_DIR)

# This adjusts sys.path, so must be done before we import other modules.
if not SCRIPTS_DIR in sys.path:
  sys.path.append(SCRIPTS_DIR)

from common import filesystem


TEMPLATE_SUBPATH = os.path.join('scripts', 'tools', 'buildbot_tool_templates')
TEMPLATE_DIR = os.path.join(BASE_DIR, TEMPLATE_SUBPATH)

BUILDER_TEMPLATE = """\
c['builders'].append({
  'name': '%(builder_name)s',
  'factory': m_annotator.BaseFactory('%(recipe)s'),
  'slavebuilddir': '%(slavebuilddir)s'})
"""


SLAVE_TEMPLATE = """\
  {
    'master': '%(master_classname)s',
    'hostname': '%(hostname)s',
    'builder': '%(builder_name)s',
    'os': '%(os)s',
    'version': '%(version)s',
    'bits': '%(bits)s',
  },
"""


def main(argv, fs):
  args = parse_args(argv)
  return args.func(args, fs)


def parse_args(argv):
  parser = argparse.ArgumentParser()
  subps = parser.add_subparsers()

  subp = subps.add_parser('gen', help=run_gen.__doc__)
  subp.add_argument('master_dirname', nargs=1,
                    help='Path to master config directory (must contain '
                         'a builders.py file).')
  subp.set_defaults(func=run_gen)

  subp = subps.add_parser('help', help=run_help.__doc__)
  subp.add_argument(nargs='?', action='store', dest='subcommand',
                    help='The command to get help for.')
  subp.set_defaults(func=run_help)

  return parser.parse_args(argv)


def run_gen(args, fs):
  """Generate a new master config."""

  master_dirname = args.master_dirname[0]
  master_subpath = fs.relpath(master_dirname, BASE_DIR)
  builders_path = fs.join(BASE_DIR, master_subpath, 'builders.py')

  if not fs.exists(builders_path):
    print("%s not found" % master_dirname, file=sys.stderr)
    return 1

  values = _values_from_file(fs, builders_path)

  for filename in fs.listfiles(TEMPLATE_DIR):
    template = fs.read_text_file(fs.join(TEMPLATE_DIR, filename))
    contents = _expand(template, values,
                       '%s/%s' % (TEMPLATE_SUBPATH, filename),
                       master_subpath)
    fs.write_text_file(fs.join(BASE_DIR, master_subpath, filename), contents)
    print("Wrote %s." % filename)

  return 0


def run_help(args, fs):
  """Get help on a subcommand."""

  if args.subcommand:
    return main([args.subcommand, '--help'], fs)
  return main(['--help'], fs)


def _values_from_file(fs, builders_path):
  builders = ast.literal_eval(fs.read_text_file(builders_path))
  master_dirname = fs.basename(fs.dirname(builders_path))
  master_name_comps = master_dirname.split('.')[1:]
  master_classname =  ''.join(c[0].upper() + c[1:] for c in master_name_comps)

  builders_block = ""
  slaves_block = "slaves = [\n"

  for builder_name, builder_vals in builders['builders'].items():
    builders_block += BUILDER_TEMPLATE % {
      'builder_name': builder_name,
      'recipe': builder_vals['recipe'],
      'slavebuilddir': builder_vals['slavebuilddir']
    }

    for pool_name in builder_vals['slave_pools']:
      pool = builders['slave_pools'][pool_name]
      slave_data = pool['slave_data']
      slaves = pool['slaves']
      for slave in slaves:
        slaves_block += SLAVE_TEMPLATE % {
            'master_classname': master_classname,
            'hostname': slave,
            'builder_name': builder_name,
            'os': slave_data['os'],
            'version': slave_data['version'],
            'bits': slave_data['bits'],
        }

  slaves_block += "]"

  v = {}
  v['builders_block'] = builders_block
  v['git_repo_url'] = builders['git_repo_url']
  v['master_dirname'] = master_dirname
  v['master_classname'] = master_classname
  v['master_base_class'] = builders['master_base_class']
  v['master_port'] = builders['master_port']
  v['master_port_alt'] = builders['master_port_alt']
  v['slave_port'] = builders['slave_port']
  v['slaves_block'] = slaves_block
  return v


def _expand(template, values, source, master_subpath):
  try:
    contents = template % values
  except:
    print("Error populating template %s" % source, file=sys.stderr)
    raise
  return _update_generated_file_disclaimer(contents, source, master_subpath)


def _update_generated_file_disclaimer(contents, source, master_subpath):
  pattern = '# This file is used by scripts/tools/buildbot-tool.*'
  replacement = ('# This file was generated from\n'
                 '# %s\n'
                 '# by "scripts/tools/buildbot-tool gen %s".\n'
                 '# DO NOT EDIT BY HAND!\n' %
                 (source, master_subpath))
  return re.sub(pattern, replacement, contents)


if __name__ == '__main__':  # pragma: no cover
  sys.exit(main(sys.argv[1:], filesystem.Filesystem()))
