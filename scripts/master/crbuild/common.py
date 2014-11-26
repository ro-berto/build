# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from twisted.python import log as twistedLog

LOG_PREFIX = '[crbuild] '


class CrbuildError(Exception):
  """crbuild-specific error."""


def log(message, level=logging.INFO):
  twistedLog.msg('%s%s' % (LOG_PREFIX, message), loglevel=level)
