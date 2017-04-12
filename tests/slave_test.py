#!/usr/bin/env python
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import SocketServer
import subprocess
import tempfile
import threading
import time
import unittest


CONFIG_PRIVATE_DOT_PY_TEMPLATE = '''
PublicMaster = object()

class Master(object):
  server_url = ''
  repo_root = ''
  webkit_root_url = ''
  git_server_url = ''
  googlecode_url = '%%s'

  bot_password = 'banana'

  class SmokeTest(object):
    master_host = 'localhost'
    slave_port = %(slave_port)d
'''


# Force our copy of config_private.py to be imported before run_slave.py
# prepends another directory to sys.path containing the real config_private.py.
SITE_PY = '''
import config_private
'''


class SlaveShouldSend(str):
  pass


class MasterSends(str):
  pass


# This is a twisted pb handshake between a buildbot slave called
# "test-slave-name" and a buildbot master, using the password "banana".
HANDSHAKE = [
    MasterSends('\x02\x80\x02\x82pb\x04\x82none'),
    SlaveShouldSend('\x02\x82pb\x02\x80\x13\x87\x06\x81\x07\x80\x1a\x87\x01'
                    '\x81\x04\x82root\x14\x87\x01\x81\x02\x80\x0b\x87\x0f'
                    '\x82test-slave-name\x01\x80\x05\x87'),
    MasterSends('\x02\x80\x13\x87\x06\x81\x03\x80\x1b\x87\x01\x81\x03\x80\x0b'
                '\x87\x10\x82?\r5[\xcc\x13\x8a\x15\x80\x983\x19i~D\xa0\x02\x80'
                '\x10\x87\x01\x81'),
    SlaveShouldSend('\x07\x80\x1a\x87\x02\x81\x01\x81\x07\x82respond\x01\x81'
                    '\x03\x80\x0b\x87\x10\x82\x0c\x17L\xc1\xc10\xf0\x08\x05'
                    '\x92\x9b\r\xae\x93O\xef\x02\x80\x10\x87\x01\x81\x01\x80'
                    '\x05\x87\x02\x80\x1d\x87\x01\x81'),
    MasterSends('\x07\x80\x1a\x87\x01\x81\x01\x81\x05\x82print\x01\x81\x02\x80'
                '\x0b\x87\x0d\x82test message!\x01\x80\x05\x87'),
]


class FakeBuildmasterRequestHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    for data in HANDSHAKE:
      if isinstance(data, MasterSends):
        self.request.sendall(data)
      elif isinstance(data, SlaveShouldSend):
        self.server.data_received.append((data, self.request.recv(1024)))

  def finish(self):
    # Give the slave process a chance to output the "test message!", and then
    # kill it.
    time.sleep(0.5)
    self.server.slave_process.kill()


class FakeBuildmasterServer(SocketServer.TCPServer):
  def __init__(self, *args, **kwargs):
    SocketServer.TCPServer.__init__(self, *args, **kwargs)
    self.data_received = []
    self.slave_process = None


class SlaveTest(unittest.TestCase):
  def setUp(self):
    # Start a TCP server that pretends to be a buildmaster.
    self.server = FakeBuildmasterServer(
        ('localhost', 0), FakeBuildmasterRequestHandler)
    _, port = self.server.server_address
    self.server_thread = threading.Thread(target=self.server.serve_forever)
    self.server_thread.setDaemon(True)
    self.server_thread.start()

    # Write a config_private.py file in a temporary directory pointing to the
    # port we're listening on.  The slave process will import this file to
    # figure out what port it should connect to.
    self.temp_dir = tempfile.mkdtemp()
    with open(os.path.join(self.temp_dir, 'config_private.py'), 'w') as fh:
      fh.write(CONFIG_PRIVATE_DOT_PY_TEMPLATE % {'slave_port': port})

    with open(os.path.join(self.temp_dir, 'site.py'), 'w') as fh:
      fh.write(SITE_PY)

    # Get the path to run_slave.py.
    self.run_slave = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'slave', 'run_slave.py'))

  def tearDown(self):
    shutil.rmtree(self.temp_dir)
    self.server.shutdown()

  def test_slave_connects(self):
    env = dict(os.environ)
    env['PYTHONPATH'] = self.temp_dir  # Let it find our config_private.py.
    env['TESTING_MASTER'] = 'SmokeTest'  # Defined in config_private.py.
    env['TESTING_SLAVENAME'] = 'test-slave-name'

    # Start the slave.
    handle = subprocess.Popen([
        self.run_slave,
        '--no-gclient-sync',
        '-y',
        'buildbot.tac',
        '--nodaemon',
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # The HTTP handler will kill the slave after it's finished the handshake.
    self.server.slave_process = handle

    # Kill the slave after 5 seconds if it doesn't connect at all.
    timer = threading.Timer(5, handle.kill)
    timer.start()
    try:
      output, _ = handle.communicate()
    finally:
      timer.cancel()

    self.assertEqual([expected for expected, _ in self.server.data_received],
                     [actual   for _, actual   in self.server.data_received])
    self.assertIn('message from master: test message!', output)


if __name__ == '__main__':
  unittest.main()
