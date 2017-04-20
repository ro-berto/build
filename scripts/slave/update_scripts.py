# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import os
import re
import subprocess
import sys
import tempfile


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import annotator
from common import env


LOGGER = logging.getLogger('update_scripts')


def _run_command(cmd, **kwargs):
  LOGGER.debug('Executing command: %s', cmd)
  kwargs.setdefault('stderr', subprocess.STDOUT)

  proc = subprocess.Popen(cmd, **kwargs)
  stdout, _ = proc.communicate()

  LOGGER.debug('Process [%s] returned [%d] with output:\n%s',
               cmd, proc.returncode, stdout)
  return proc.returncode, stdout


def ensure_managed(dot_gclient_filename):
  """Rewrites a .gclient file to set "managed": True.

  Returns:
    True if the .gclient file was modified.
  """

  with open(dot_gclient_filename) as fh:
    contents = fh.read()

  new_contents = re.sub(r'("managed"\s*:\s*)False', r'\1True', contents)

  if contents != new_contents:
    with open(dot_gclient_filename, 'w') as fh:
      fh.write(new_contents)
    return True
  return False


def update_scripts():
  if os.environ.get('RUN_SLAVE_UPDATED_SCRIPTS'):
    os.environ.pop('RUN_SLAVE_UPDATED_SCRIPTS')
    return False

  # For testing, we don't actually want to run "gclient sync" against its native
  # root. However, we don't want to mock/disable it either, since we want to
  # exercise this code path.
  build_dir = os.environ.get(
      'RUN_SLAVE_UPDATED_SCRIPTS_TEST_BUILD_DIR', env.Build)

  stream = annotator.StructuredAnnotationStream()

  with stream.step('update_scripts') as s:
    if ensure_managed(os.path.join(build_dir, os.pardir, '.gclient')):
      s.step_text('Top-level gclient solution was unmanaged, '
                  'changed to managed')

    # Get our "gclient" file. We will use the "gclient" relative to this
    # script's checkout, regardless of "build_dir".
    gclient_name = 'gclient'
    if sys.platform.startswith('win'):
      gclient_name += '.bat'
    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                gclient_name)
    gclient_cmd = [gclient_path, 'sync',
                   # these two need to both be here to actually get
                   # `git checkout --force` to happen.
                   '--force', '--delete_unversioned_trees',
                   '--break_repo_locks', '--verbose', '--jobs=2']
    try:
      fd, output_json = tempfile.mkstemp()
      os.close(fd)
      gclient_cmd += ['--output-json', output_json]
    except Exception:
      # Super paranoia try block.
      output_json = None
    cmd_dict = {
        'name': 'update_scripts',
        'cmd': gclient_cmd,
        'cwd': build_dir,
    }
    annotator.print_step(cmd_dict, os.environ, stream)
    rv, _ = _run_command(gclient_cmd, cwd=build_dir)
    if rv != 0:
      s.step_text('gclient sync failed!')
      s.step_exception()
    elif output_json:
      try:
        with open(output_json, 'r') as f:
          gclient_json = json.load(f)
        for line in json.dumps(
            gclient_json, sort_keys=True,
            indent=4, separators=(',', ': ')).splitlines():
          s.step_log_line('gclient_json', line)
        s.step_log_end('gclient_json')

        build_checkout = gclient_json['solutions'].get('build/')
        if build_checkout:
          s.step_text('%(scm)s - %(revision)s' % build_checkout)
          s.set_build_property('build_scm', json.dumps(build_checkout['scm']))
          s.set_build_property('build_revision',
                               json.dumps(build_checkout['revision']))
      except Exception as e:
        s.step_text('Unable to process gclient JSON %s' % repr(e))
        s.step_exception()
      finally:
        try:
          os.remove(output_json)
        except Exception as e:
          LOGGER.warning("LEAKED: %s", output_json, exc_info=True)
    else:
      s.step_text('Unable to get SCM data')
      s.step_exception()

    os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'

    # After running update scripts, set PYTHONIOENCODING=UTF-8 for the real
    # annotated_run.
    os.environ['PYTHONIOENCODING'] = 'UTF-8'

    return True
