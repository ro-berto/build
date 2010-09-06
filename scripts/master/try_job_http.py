#!/usr/bin/python
# Copyright (c) 2008-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.application import strports
from twisted.python import log
from twisted.web import http

from try_job_base import TryJobBase


class TryJobHTTPRequest(http.Request):
  def __init__(self, channel, queued):
    http.Request.__init__(self, channel, queued)

  def process(self):
    try:
      # Support only one URI for now.
      if self.uri != '/send_try_patch':
        log.msg("Received invalid URI: %s" % self.uri)
        self.code = http.NOT_FOUND
        return

      try:
        # The arguments values are embedded in a list.
        tmp_args = {}
        for (key,value) in self.args.items():
          tmp_args[key] = value[0]
        self.code = self.channel.factory.parent.messageReceived(tmp_args)
      except:
        self.code = http.INTERNAL_SERVER_ERROR
        raise
    finally:
      self.code_message = http.RESPONSES[self.code]
      self.write(self.code_message)
      self.finish()


class TryJobHTTP(TryJobBase):
  """Opens a HTTP port to accept patch files and to execute these on the try
  server."""

  def __init__(self, name, pools, port, userpass=None, properties=None,
               last_good_urls=None, code_review_sites=None):
    self.pools = pools
    pools.SetParent(self)
    TryJobBase.__init__(self, name, pools.ListBuilderNames(), properties,
                        last_good_urls, code_review_sites)
    if type(port) is int:
      port = "tcp:%d" % port
    self.port = port
    f = http.HTTPFactory()
    f.protocol.requestFactory = TryJobHTTPRequest
    f.parent = self
    s = strports.service(port, f)
    s.setServiceParent(self)

  def getPort(self):
    # utility method for tests: figure out which TCP port we just opened.
    return self.services[0]._port.getHost().port

  def messageReceived(self, socket):
    return self.SubmitJob(socket)
