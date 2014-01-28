# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Declares a number of site-dependent variables for use by scripts.

A typical use of this module would be

  import chromium_config as config

  v8_url = config.Master.v8_url
"""

import os

from twisted.spread import banana

from config_bootstrap import config_private # pylint: disable=W0403,W0611
from config_bootstrap import Master # pylint: disable=W0403,W0611

# By default, the banana's string size limit is 640kb, which is unsufficient
# when passing diff's around. Raise it to 100megs. Do this here since the limit
# is enforced on both the server and the client so both need to raise the
# limit.
banana.SIZE_LIMIT = 100 * 1024 * 1024


def DatabaseSetup(buildmaster_config, require_dbconfig=False):
  if os.path.isfile('.dbconfig'):
    values = {}
    execfile('.dbconfig', values)
    if 'password' not in values:
      raise Exception('could not get db password')

    buildmaster_config['db_url'] = 'postgresql://%s:%s@%s/%s' % (
        values['username'], values['password'],
        values.get('hostname', 'localhost'), values['dbname'])
  else:
    assert(not require_dbconfig)
