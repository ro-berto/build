# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility and helper functions for 'twisted' library use and integration."""

import httplib
import urlparse

import twisted.web.client
import twisted.web.error as twe

from common.twisted_util.authorizer import IAuthorizer
from common.twisted_util.body_producers import IMIMEBodyProducer, \
                                               IReusableBodyProducer, \
                                               StringBodyProducer
from common.twisted_util.agent_util import CloneHeaders, RelativeURLJoin
from twisted.internet import defer, reactor
from twisted.internet.task import deferLater
from twisted.python import log


__all__ = [
    'Agent',
]


class TimeoutError(Exception):
  """An exception that is raised when a timeout is specified and the timeout
  interval passes without a response.
  """
  def __init__(self, url, timeout):
    super(TimeoutError, self).__init__(
        'Failed to reach [%s] after %s seconds.' % (url, timeout))
    self.url = url
    self.timeout = timeout


class Agent(twisted.web.client.Agent):
  """A specialization of the default Twisted agent with additional features.

  This class adds features to the default Twisted agent, including:
  - Support for Authorizers to add authorization headers to the HTTP request.
  - Support for flakiness-resilience by automatically retrying requests that
    receive 'Server Error' response codes.
  """

  verbose = False

  DEFAULT_RETRY_COUNT = 0
  DEFAULT_RETRY_DELAY = 0.5

  def __init__(self, host, authorizer=None, read_only=False, retry_count=None,
               retry_delay=None, *args, **kwargs):
    """
    Creates a new Agent.

    Args:
      host: (str) The name (and optionally port) of the host to
          connect to. This is passed directly as the 'host' parameter.
      authorizer: (Authorizer) If present, an Authorizer instance to use for
          requests.
      read_only: (bool) If True, then any write-associated REST operations that
          (non-GET) will raise a 'httplib.METHOD_NOT_ALLOWED' error response.
      retry_count: (int) If not 'None', the default number of retries to
          perform with a request. This can be overridden in the request.
      retry_delay: (number) If not 'None', the default retry delay multiplier.
          This can be overridden in the request.
      args, kwargs: Forwarded to 'Agent.__init__'
    """
    if (
        (authorizer is not None) and
        (not IAuthorizer.providedBy(authorizer))):
      raise TypeError("'authorizer' does not implement the Authorizer "
                      "interface")

    url = urlparse.urlparse(host)
    self.protocol = url.scheme
    if self.protocol == '':
      raise ValueError("'host' parameter '%s' must include a protocol" %
                       (host,))
    self.host = url.netloc
    self.base_url = urlparse.urljoin(
        '%s://%s' % (self.protocol, url.netloc),
        url.path)

    self._read_only = bool(read_only)
    self._authorizer = authorizer
    self._retry_count = retry_count or self.DEFAULT_RETRY_COUNT
    self._retry_delay = ((retry_delay) if retry_delay is not None
                         else (self.DEFAULT_RETRY_DELAY))
    twisted.web.client.Agent.__init__(self, reactor, *args, **kwargs)

  def __str__(self):
    return '%s<%s>' % (type(self).__name__, self.base_url)

  @property
  def read_only(self):
    return self._read_only

  def _buildRequest(self, path, headers):
    """Constructs the request parametrs used by 'request'.

    Args:
      path: (str) The path within the Agent's host to query
      headers: (Headers) The current set of HTTP headers. This may be modified
          during this method.

    Returns: (str) The full URL for the request
    """
    assert path is not None
    if not path.startswith('/'):
      path = '/' + path

    # Add authorization
    if self._authorizer is not None:
      added_auth = self._authorizer.addAuthHeadersForURL(
          headers,
          self.base_url)
      if (self.verbose) and (not added_auth):
        log.msg("No authentication for URL %r" % (self.base_url,))
    return RelativeURLJoin(self.base_url, path)

  # Disable argument number difference | pylint: disable=W0221
  @defer.inlineCallbacks
  def request(self, method, path, headers=None, body_producer=None,
              expected_code=httplib.OK, retry=None, delay=None,
              error_protocol=None, timeout=None):
    """
    Constructs and initiates a HTTP request.

    If supplied, 'error_protocol' is a function that will be used to convert
    the Agent response into a string. In the event that an HTTP error is
    encountered, the body of that HTTP response will be loaded through
    'error_protocol'. The resulting 'twisted.web.error.Error' will then have
    its 'response' field populated with the resulting value.

    'error_protocol' is a function that accepts a 'Response' object and
    returns a Deferred whose return value is the loaded body. Some examples of
    such functions are:
      - StringResponse.Get
      - JsonResponse.Get
    (error_protocol) Args:
      response: (twisted.web.client.Response) the Response object to load
    (error_protocol) Returns: (Deferred) A Deferred whose return value will be
        loaded into the 'twisted.web.error.Error' that the error failure wraps.

    Args:
      method: (str) The HTTP request type (GET, PUT, POST, DELETE)
      path: (str) The path within the Agent's host to query
      headers: (Headers) If supplied, the starting HTTP Headers object
      body_producer: (IBodyProducer) If supplied, the 'IBodyProducer' instance
          that will be used to produce HTTP request's body; if None, the body
          will be of length '0'.
      expected_code: (int or tuple of ints) HTTP response code expected in
          reply.
      retry: (int) If non-zero, the number of times to retry when a transient
          error is encountered. If None, the default 'retry' value will be
          used.
      delay: (number) The number of seconds of the initial retry delay;
          subsequent delays will double this value. If 'None', the default delay
          will be used. If no default delay was supplied either, a delay of 0.5
          seconds will be used if retrying.
      error_protocol: (func) The function to use to load the HTTP response when
          an error occurs; if this is 'None', the body will not be read on
          error.
      timeout (number): if not None, the number of seconds to wait before
          terminating the request. If a timeout is encountered, a TimeoutError
          will be raised.

    Returns: (Deferred) A deferred that will be invoked with a
       'twisted.web.client.Response' instance.
    """
    assert method in ('GET', 'PUT', 'POST', 'DELETE')
    if (not isinstance(expected_code, tuple) and
        not isinstance(expected_code, list)):
      expected_code = (expected_code,)
    headers = CloneHeaders(headers) # Handles 'None' case
    url = self._buildRequest(path, headers)

    # Get parameters, falling back on global values
    retry = retry or self._retry_count
    delay = (delay) if delay is not None else (self._retry_delay)

    if body_producer is not None:
      # If 'body_producer' supplies its own MIME type, use that.
      if IMIMEBodyProducer.providedBy(body_producer):
        headers.setRawHeaders('Content-Type', [body_producer.getMIMEType()])

    if self.verbose:
      log.msg('%r %r' % (method, url))
      for key, vlist in headers.getAllRawHeaders():
        for val in vlist:
          if key.lower() == 'authorization':
            val = 'HIDDEN'
          log.msg('(Header) %r: %r' % (key, val))
      # Special case (StringBodyProducer): dump body if we can
      if isinstance(body_producer, StringBodyProducer):
        log.msg(body_producer.body_str)

    if (self.read_only) and (method != 'GET'):
      raise twe.Error(
          httplib.METHOD_NOT_ALLOWED,
          "Refusing to execute '%s' request to read-only Agent: %s" %
              (method, url),
      )

    # Request/Retry Deferred Loop
    while True:
      # Make the request.
      response = yield self._timeout_request(
          timeout,
          method,
          str(url),
          headers,
          body_producer)

      if response.code in expected_code:
        defer.returnValue(response)

      # The operation failed.
      retry -= 1
      error = twe.Error(
          response.code,
          message="Response status (%s) didn't match expected (%s) for '%s'" %
                  (response.code, expected_code, url))
      log.msg(error.message)

      # If we have no more retries, or if this was a non-transient failure,
      # exit immediately with Twisted web error.
      if retry <= 0 or response.code < httplib.INTERNAL_SERVER_ERROR:
        # No more retries, return our error.
        if error_protocol:
          error.response = yield error_protocol(response)
        raise error

      # Retry after an exponentially-increasing delay.
      log.msg("Query '%s' encountered transient error (%d); retrying "
              "(%d remaining) in %s second(s)..." %
                  (url, response.code, retry, delay))

      if (body_producer is not None and
          IReusableBodyProducer.providedBy(body_producer)):
        body_producer.reset()

      yield self._deferred_sleep(delay)
      delay *= 2


  GET = lambda s, *a, **kw: s.request('GET', *a, **kw)
  PUT = lambda s, *a, **kw: s.request('PUT', *a, **kw)
  POST = lambda s, *a, **kw: s.request('POST', *a, **kw)
  DELETE = lambda s, *a, **kw: s.request('DELETE', *a, **kw)

  def _timeout_request(self, timeout_seconds, method, url, headers,
                       body_producer):
    # Call our parent's 'request' function.
    d = twisted.web.client.Agent.request(
        self,
        method,
        str(url),
        headers=headers,
        bodyProducer=body_producer)

    def timeout_expired():
      d.cancel()
      raise TimeoutError(url, timeout_seconds)
    timeout = None
    if timeout_seconds:
      timeout = reactor.callLater(timeout_seconds, timeout_expired)

    def completed(passthrough):
      if timeout and timeout.active():
        timeout.cancel()
      return passthrough
    d.addBoth(completed)
    return d

  @staticmethod
  def _deferred_sleep(seconds):
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, seconds)
    return d
