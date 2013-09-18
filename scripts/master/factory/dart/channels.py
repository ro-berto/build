# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class Channel(object):
  def __init__(self, name, branch, position, category_postfix):
    self.branch = branch
    self.builder_postfix = '-' + name
    self.category_postfix = category_postfix
    self.name = name
    self.position = position
    self.all_deps_path = '/' + branch + '/deps/all.deps'
    self.dartium_deps_path = '/' + branch + '/deps/dartium.deps'

CHANNELS = [
  Channel('be', 'branches/bleeding_edge', 0, ''),
  Channel('dev', 'trunk', 1, '-dev'),
  Channel('stable', 'branches/0.6', 2, '-stable'),
]

CHANNELS_BY_NAME = {}
for c in CHANNELS:
  CHANNELS_BY_NAME[c.name] = c

def duplicate_builders_in_slaves(slaves):
  """Traverses a list of slaves and duplicates the builders associated with each
  slave for every channel. The channels have specified the postfix."""
  for slave in slaves:
    all_builders = []
    for builder in slave.get('builder', ()):
      if 'trunk' not in builder and 'v8' not in builder:
        for channel in CHANNELS:
          all_builders.append('%s%s' % (builder, channel.builder_postfix))
      else:
        all_builders.append(builder)
    slave['builder'] = all_builders
  return slaves
