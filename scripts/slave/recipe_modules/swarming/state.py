# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class State(object):
  """Represents the current task state.

  Copied from:
  https://cs.chromium.org/chromium/infra/luci/appengine/swarming/swarming_rpcs.py?q=TaskState\(

  KEEP IN SYNC.

  Used to parse the 'state' value in task result.
  """
  RUNNING = 0x10    # 16
  PENDING = 0x20    # 32
  EXPIRED = 0x30    # 48
  TIMED_OUT = 0x40  # 64
  BOT_DIED = 0x50   # 80
  CANCELED = 0x60   # 96
  COMPLETED = 0x70  # 112
  KILLED = 0x80
  NO_RESOURCE = 0x100

  _NAMES = {
    RUNNING: 'Running',
    PENDING: 'Pending',
    EXPIRED: 'Expired',
    TIMED_OUT: 'Execution timed out',
    BOT_DIED: 'Bot died',
    CANCELED: 'User canceled',
    COMPLETED: 'Completed',
    KILLED: 'Killed',
    NO_RESOURCE: 'No resource',
  }

  @classmethod
  def to_string(cls, state):
    """Returns a user-readable string representing a State."""
    return cls._NAMES[state]
