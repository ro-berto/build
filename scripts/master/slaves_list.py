#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


def _EntryHasValueInField(entry, field, value):
  """Checks whether a slave has a particular value for a field listed."""
  # Trap the event where no entry was found.
  if entry is None:
    return False
  entry_value = entry.get(field)
  if not entry_value:
    return False
  if type(entry_value) in (tuple, list):
    return value.lower() in [i.lower() for i in entry_value]
  else:
    return value.lower() == entry_value.lower()


def EntryToSlaveName(entry):
  """Extracts the buildbot slave name from the slaves list entry.

  The slave list entry is a dict."""
  # Trap the event where no entry was found.
  if entry is None:
    return None
  if entry.get('slavename'):
    return entry.get('slavename')
  if entry.get('hostname'):
    return entry.get('hostname')
  return None


def _FilterValue(slaves, value, name):
  if not value:
    return slaves
  value = value.lower()
  return [s for s in slaves if s.get(name) and s.get(name).lower() == value]


def _FilterField(slaves, value, name):
  if not value:
    return slaves
  return [s for s in slaves if _EntryHasValueInField(s, name, value)]


class SlavesList(object):
  def __init__(self, filename, default_master=None):
    local_vars = {}
    execfile(filename, local_vars)
    self.slaves = local_vars['slaves']
    self.default_master = default_master
    slaves = [EntryToSlaveName(x).lower() for x in self.slaves]
    dupes = set()
    while len(slaves):
      x = slaves.pop()
      if x in slaves:
        dupes.add(x)
    if dupes:
      print 'Found slave dupes!\n  %s' % ', '.join(dupes)
      assert False

  def GetSlaves(self, master=None, builder=None, os=None, tester=None,
                bits=None, version=None):
    """Returns the slaves listed in the private/slaves_list.py file.

    Optionally filter with master, builder, os, tester and bitness type.
    """
    slaves = _FilterValue(self.slaves, master or self.default_master, 'master')
    slaves = _FilterValue(slaves, os, 'os')
    slaves = _FilterValue(slaves, bits, 'bits')
    slaves = _FilterValue(slaves, version, 'version')
    slaves = _FilterField(slaves, builder, 'builder')
    slaves = _FilterField(slaves, tester, 'tester')
    return slaves

  def GetSlave(self, master=None, builder=None, os=None, tester=None, bits=None,
               version=None):
    """Returns one slave or none if none or multiple slaves are found."""
    slaves = self.GetSlaves(master, builder, os, tester, bits, version)
    if len(slaves) != 1:
      return None
    return slaves[0]

  def GetSlavesName(self, master=None, builder=None, os=None, tester=None,
                    bits=None, version=None):
    """Similar to GetSlaves() except that it only returns the slave names."""
    return [EntryToSlaveName(e) for e in self.GetSlaves(master, builder, os,
                                                        tester, bits, version)]

  def GetSlaveName(self, master=None, builder=None, os=None, tester=None,
                   bits=None, version=None):
    """Similar to GetSlave() except that it only returns the slave name."""
    slave_name = EntryToSlaveName(self.GetSlave(master, builder, os, tester,
                                                bits, version))
    return slave_name


def Main(argv=None):
  import optparse
  parser = optparse.OptionParser()
  parser.add_option('-f', '--filename', help='File to parse, REQUIRED')
  parser.add_option('-m', '--master', help='Master to filter')
  parser.add_option('-b', '--builder', help='Builder to filter')
  parser.add_option('-o', '--os', help='OS to filter')
  parser.add_option('-t', '--tester', help='Tester to filter')
  parser.add_option('-v', '--version', help='OS\'s version to filter')
  parser.add_option('--bits', help='OS bitness to filter')
  options, _ = parser.parse_args(argv)
  if not options.filename:
    parser.print_help()
    print('\nYou must specify a file to get the slave list from')
    return 1
  slaves = SlavesList(options.filename)
  for slave in slaves.GetSlavesName(options.master, options.builder,
                                    options.os, options.tester, options.bits,
                                    options.version):
    print slave
  return 0

if __name__ == '__main__':
  import sys
  sys.exit(Main())
