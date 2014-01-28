# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


try:
  from config_private import PrivateBase as Base  # pylint: disable=F0401
except ImportError:
  from config_public import PublicBase as Base    # pylint: disable=W0403


class Master(Base):
  """This class is a simple compatibility layer for everyone who calls
     > import config; config.Master.foo
     Hopefully it will be able to go away soon, when all those call sites
     are refactored to correctly get the current ActiveMaster instead.
  """
  pass
