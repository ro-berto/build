# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Retrieve the list of the current build sheriffs."""

import datetime
import os
import re


class BuildSheriffs(object):
  # File that contains the string containing the build sheriff names.
  # Note: Don't pull from http because if it ever come back to BB, it will
  # hang since BB web server is not reentrant!
  sheriff_file_ = './public_html/sheriff.js'

  # RE to retrieve the sheriff names.
  usernames_matcher_ = re.compile(r'document.write\(\'([\w, ]+)\'\)')

  # The date last time the sheriffs list was updated.
  last_check_ = None
  # Cached Sheriffs list.
  sheriffs_ = None

  @staticmethod
  def GetSheriffs():
    """Returns a list of build sheriffs for the current week."""
    # Update once per hour
    now = datetime.datetime.utcnow()
    if not BuildSheriffs.last_check_ or (BuildSheriffs.last_check_ <
                                         now - datetime.timedelta(hours=1)):
      BuildSheriffs.last_check_ = now
      # Initialize in case nothing is found.
      BuildSheriffs.sheriffs_ = []
      if os.path.isfile(BuildSheriffs.sheriff_file_):
        try:
          f = open(BuildSheriffs.sheriff_file_, 'r')
          line = f.readlines()[0]
          f.close()
          usernames_match = BuildSheriffs.usernames_matcher_.match(line)
          if usernames_match:
            usernames_str = usernames_match.group(1)
            if usernames_str == 'None (channel is sheriff)':
              return BuildSheriffs.sheriffs_

            for sheriff in usernames_str.split(', '):
              if sheriff.count('@') == 0:
                sheriff += '@google.com'
              BuildSheriffs.sheriffs_.append(sheriff)
        except (IOError, ValueError):
          pass

    return BuildSheriffs.sheriffs_
