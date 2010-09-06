# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.web import client
from buildbot.status import status_push

# Silence twisted a bit.
client.HTTPClientFactory.noisy = False


class HttpStatusPush(status_push.HttpStatusPush):
  pass
