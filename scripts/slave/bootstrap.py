# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities to enable slaves to determine their master without importing any
buildbot or twisted code.
"""

import inspect
import os
import sys

from common import chromium_utils


def GetMasterConfigs(master_name=None, include_internal=True):
  """Executes and returns master configs.

  Normally a slave can use chromium_utils.GetActiveMastername() to find
  itself and determine which ActiveMaster to use. In that case, the
  active master name is passed in as an arg, and we only load the
  site_config.py that defines it. When testing, the current "slave"
  won't be found. In that case, we don't know which config to use, so
  load them all. In either case, masters are assigned as attributes
  to the config.Master object.
  """
  masters = {}
  active_master = None
  for master in chromium_utils.ListMasters(include_internal=include_internal):
    path = os.path.join(master, 'master_site_config.py')
    if os.path.exists(path):
      local_vars = {}
      try:
        execfile(path, local_vars)
      # pylint: disable=W0703
      except Exception, e:
        # Naked exceptions are banned by the style guide but we are
        # trying to be resilient here.
        print >> sys.stderr, 'WARNING: cannot exec ' + path
        print >> sys.stderr, e
      for (symbol_name, symbol) in local_vars.iteritems():
        if inspect.isclass(symbol):
          setattr(symbol, 'local_config_path', master)
          masters[symbol_name] = symbol
          if master_name and master_name == symbol_name:
            active_master = symbol
  return (masters, active_master)
