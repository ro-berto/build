# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
from cStringIO import StringIO
import json
import netrc

from twisted.internet import defer, protocol, reactor
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web import iweb

from zope.interface import implements

# pylint: disable=W0105
"""
Class for sending http requests to a gerrit server, and parsing the
json-formatted responses.
"""


DEBUG = False
NETRC = netrc.netrc()


class JsonResponse(protocol.Protocol):
  """Receiver protocol to parse a json response from gerrit."""

  @staticmethod
  def Get(response, url=None):
    """
    Given a Response object returned by GerritAgent.request, parse the json
    body of the response.
    """
    finished = defer.Deferred()
    response.deliverBody(JsonResponse(url, finished))
    return finished

  def __init__(self, url, finished):
    self.url = url
    self.finished = finished
    self.buf = StringIO()
    self.reply = None

  def dataReceived(self, _bytes):
    self.buf.write(_bytes)

  # pylint: disable=W0222
  def connectionLost(self, _):
    body = self.buf.getvalue()
    if not body:
      self.finished.callback(None)
      return
    errmsg = 'Mal-formed json response from %s' % self.url
    if body[0:4] != ")]}'":
      self.finished.errback(errmsg)
      return
    try:
      self.reply = json.loads(body[4:])
      if DEBUG:
        log.msg(json.dumps(self.reply, indent=2))
      self.finished.callback(self.reply)
    except ValueError:
      self.finished.errback(errmsg)

class JsonBodyProducer:

  implements(iweb.IBodyProducer)

  def __init__(self, text):
    self.text = text
    self.length = len(text)

  def startProducing(self, consumer):
    consumer.write(self.text)
    self.text = ''
    self.length = 0
    return defer.succeed(None)

  def stopProducing(self):
    pass

class GerritAgent(Agent):

  gerrit_protocol = 'https'

  def __init__(self, gerrit_host, *args, **kwargs):
    proto, _, host = gerrit_host.partition('://')
    if host:
      self.gerrit_protocol = proto
      self.gerrit_host = host
    else:
      self.gerrit_host = gerrit_host
    auth_entry = NETRC.authenticators(self.gerrit_host.partition(':')[0])
    if auth_entry:
      self.auth_token = 'Basic %s' % (
          base64.b64encode('%s:%s' % (auth_entry[0], auth_entry[2])))
    else:
      self.auth_token = None
    Agent.__init__(self, reactor, *args, **kwargs)

  # pylint: disable=W0221
  def request(self, method, path, headers=None, body=None, expected_code=200):
    """
    Send an http request to the gerrit service for the given path.

    Returns a Deferred which will call back with the parsed json body of the
    gerrit server's response.
    """
    if not path.startswith('/'):
      path = '/' + path
    if not headers:
      headers = Headers()
    if self.auth_token:
      if not path.startswith('/a/'):
        path = '/a' + path
      headers.setRawHeaders('authorization', [self.auth_token])
    url = '%s://%s%s' % (self.gerrit_protocol, self.gerrit_host, path)
    if body:
      body = JsonBodyProducer(json.dumps(body))
      headers.setRawHeaders('Content-Type', ['application/json'])
    if DEBUG:
      log.msg(url)
    d = Agent.request(self, method, str(url), headers, body)
    def _check_code(response):
      if response.code != expected_code:
        msg = 'Failed gerrit request (code %s, expected %s): %s' % (
            response.code, expected_code, url)
        raise RuntimeError(msg)
      return response
    d.addCallback(_check_code)
    d.addCallback(JsonResponse.Get, url=url)
    return d
