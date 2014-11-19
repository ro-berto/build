#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

r"""Tool for viewing masters, their hosts and their ports.

Has three modes:
  a) In normal mode, simply prints the list of all known masters, sorted by
     hostname, along with their associated ports, for the perusal of the user.
  b) In --audit mode, tests to make sure that no masters conflict/overlap on
     ports (even on different masters) and that no masters have unexpected
     ports (i.e. differences of more than 100 between master, slave, and alt).
     Audit mode returns non-zero error code if conflicts are found. In audit
     mode, --verbose causes it to print human-readable output as well.
  c) In --find mode, prints a set of available ports for the given master.

Ports are well-formed if they follow this spec:
XYYZZ
|| \__The last two digits identify the master, e.g. master.chromium
|\____The second and third digits identify the master host, e.g. master1.golo
\_____The first digit identifies the port type, e.g. master_port

In particular,
X==3: master_port (Web display)
X==4: slave_port (for slave TCP/RCP connections)
X==5: master_port_alt (Alt web display, with "force build" disabled)
The values X==1,2, and 6 are not used due to too few free ports in those ranges.

In all modes, --csv causes the output (if any) to be formatted as
comma-separated values.
"""

import json
import optparse
import os
import sys

# Should be <snip>/build/scripts/tools
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'site_config'))

import config_bootstrap
from slave import bootstrap


# These are ports which are likely to be used by another service, or which have
# been officially reserved by IANA.
PORT_BLACKLIST = set([
    # We don't care about reserved ports below 30000, the lowest port we use.
    31457,  # TetriNET
    31620,  # LM-MON
    33434,  # traceroute
    34567,  # EDI service
    35357,  # OpenStack ID Service
    40000,  # SafetyNET p Real-time Industrial Ethernet protocol
    41794,  # Crestron Control Port
    41795,  # Crestron Control Port
    45824,  # Server for the DAI family of client-server products
    47001,  # WinRM
    47808,  # BACnet Building Automation and Control Networks
    48653,  # Robot Raconteur transport
    49151,  # Reserved
    # There are no reserved ports in the 50000-65535 range.
])


PORT_TYPE_MAP = {
  'port': '3',
  'slave_port': '4',
  'alt_port': '5',
}


HOST_MACHINE_MAP = {
  'master1.golo': '01',
  'master2.golo': '02',
  'master3.golo': '03',
  'master4.golo': '04',
  'master4a.golo': '14',
  'master5.golo': '05',
  'master6.golo': '06',
  'master7.golo': '07',
  'master.chrome': '10'
}


def get_args():
  """Process command-line arguments."""
  parser = optparse.OptionParser(
      description='Tool to list all masters along with their hosts and ports.')

  parser.add_option('-l', '--list', action='store_true', default=False,
                    help='Output a list of all ports in use by all masters. '
                         'Default behavior if no other options are given.')
  parser.add_option('--sort-by', action='store',
                    help='Define the primary key by which rows are sorted. '
                    'Possible values are: "port", "alt_port", "slave_port", '
                    '"host", and "name". Only one value is allowed (for now).')
  parser.add_option('--find', action='store', metavar='NAME',
                    help='Outputs three available ports for the given master.')
  parser.add_option('--audit', action='store_true', default=False,
                    help='Output conflict diagnostics and return an error '
                         'code if misconfigurations are found.')
  parser.add_option('--presubmit', action='store_true', default=False,
                    help='The same as --audit, but prints no output. '
                         'Overrides all other options.')

  parser.add_option('--csv', action='store_true', default=False,
                    help='Print output in comma-separated values format.')
  parser.add_option('--json', action='store_true', default=False,
                    help='Print output in JSON format. Overrides --csv.')
  parser.add_option('--full-host-names', action='store_true', default=False,
                    help='Refrain from truncating the master host names')

  opts, _ = parser.parse_args()

  opts.verbose = True

  if not (opts.find or opts.audit or opts.presubmit):
    opts.list = True

  if opts.presubmit:
    opts.list = False
    opts.audit = True
    opts.find = False
    opts.verbose = False

  return opts


def getint(string):
  """Try to parse an int (port number) from a string."""
  try:
    ret = int(string)
  except ValueError:
    ret = 0
  return ret


def human_print(lines, verbose):
  """Given a list of lists of tokens, pretty prints them in columns.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  num_cols = len(lines[0])
  format_string = ''
  for col in xrange(num_cols - 1):
    col_width = max(len(str(line[col])) for line in lines) + 1
    format_string += '%-' + str(col_width) + 's '
  format_string += '%s'

  if verbose:
    for line in lines:
      print format_string % tuple(line)


def csv_print(lines, verbose):
  """Given a list of lists of tokens, prints them as comma-separated values.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  if verbose:
    for line in lines:
      print ','.join(str(t) for t in line)
    print '\n'


def master_map(masters, output, opts):
  """Display a list of masters and their associated hosts and ports."""

  lines = [['Master', 'Config Dir', 'Host', 'Web port', 'Slave port',
            'Alt port', 'URL']]
  for master in masters:
    lines.append([
        master['name'], master['dirname'], master['host'], master['port'],
        master['slave_port'], master['alt_port'], master['buildbot_url']])

  output(lines, opts.verbose)


def master_audit(masters, output, opts):
  """Check for port conflicts and misconfigurations on masters.

  Outputs lists of masters whose ports conflict and who have misconfigured
  ports. If any misconfigurations are found, returns a non-zero error code.
  """
  # Return value. Will be set to 1 the first time we see an error.
  ret = 0

  # Look for masters using the wrong ports for their port types.
  lines = [['Masters with misconfigured ports based on port type:']]
  for master in masters:
    for port_type, port_digit in PORT_TYPE_MAP.iteritems():
      if not str(master[port_type]).startswith(port_digit):
        ret = 1
        lines.append([master['name']])
        break
  output(lines, opts.verbose)
  print

  # Look for masters using the wrong ports for their port types.
  lines = [['Masters with misconfigured ports based on hostname:']]
  for master in masters:
    host = format_host_name(master['host'])
    digits = HOST_MACHINE_MAP.get(host)
    if digits:
      for port in PORT_TYPE_MAP.iterkeys():
        if str(master[port])[1:3] != digits:
          ret = 1
          lines.append([master['name']])
          break
  output(lines, opts.verbose)
  print

  # Look for masters configured to use the same ports.
  web_ports = {}
  slave_ports = {}
  alt_ports = {}
  all_ports = {}
  for master in masters:
    web_ports.setdefault(master['port'], []).append(master)
    slave_ports.setdefault(master['slave_port'], []).append(master)
    alt_ports.setdefault(master['alt_port'], []).append(master)

    for port_type in ('port', 'slave_port', 'alt_port'):
      all_ports.setdefault(master[port_type], []).append(master)

  # Check for blacklisted ports.
  lines = [['Blacklisted port', 'Master', 'Host']]
  for port, lst in all_ports.iteritems():
    if port in PORT_BLACKLIST:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)
  print

  # Check for conflicting web ports.
  lines = [['Web port', 'Master', 'Host']]
  for port, lst in web_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)
  print

  # Check for conflicting slave ports.
  lines = [['Slave port', 'Master', 'Host']]
  for port, lst in slave_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)
  print

  # Check for conflicting alt ports.
  lines = [['Alt port', 'Master', 'Host']]
  for port, lst in alt_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)
  print

  # Look for masters whose port, slave_port, alt_port aren't separated by 10000.
  lines = [['Master', 'Host', 'Web port', 'Slave port', 'Alt port']]
  for master in masters:
    if (getint(master['slave_port']) - getint(master['port']) != 10000 or
        getint(master['alt_port']) - getint(master['slave_port']) != 10000):
      ret = 1
      lines.append([master['name'], master['host'],
                   master['port'], master['slave_port'], master['alt_port']])
  output(lines, opts.verbose)

  return ret


def find_port(mastername, masters, output, opts):
  """Finds a triplet of free ports appropriate for the given master."""
  master = None
  for m in masters:
    if m['name'] != mastername:
      continue
    master = m
  if not master:
    lines = [['master %s not found' % mastername],
             ['use the list function to see all masters.']]
    output(lines, opts.verbose)
    return 1

  master_digits = HOST_MACHINE_MAP[master['host']]

  used_ports = set()
  for master in masters:
    for port in ('port', 'slave_port', 'alt_port'):
      used_ports.add(master.get(port, 0))
  used_ports = used_ports | PORT_BLACKLIST

  def _inner_loop():
    for digits in xrange(0, 100):
      port = '3%s%02d' % (master_digits, digits)
      slave_port = '4%s%02d' % (master_digits, digits)
      alt_port = '5%s%02d' % (master_digits, digits)
      if all([
          int(port) not in used_ports,
          int(slave_port) not in used_ports,
          int(alt_port) not in used_ports]):
        return port, slave_port, alt_port
    return None, None, None
  port, slave_port, alt_port = _inner_loop()

  if not all([port, slave_port, alt_port]):
    lines = [['unable to find available ports on host %s' % master['host']]]
    output(lines, opts.verbose)
    return 1

  lines = [['Web port', 'Slave port', 'Alt port']]
  lines.append([port, slave_port, alt_port])
  output(lines, opts.verbose)


def format_host_name(host):
  for suffix in ('.chromium.org', '.corp.google.com'):
    if host.endswith(suffix):
      return host[:-len(suffix)]
  return host


def extract_masters(masters):
  """Extracts the data we want from a collection of possibly-masters."""
  good_masters = []
  for master_name, master in masters.iteritems():
    if not hasattr(master, 'master_port'):
      # Not actually a master
      continue
    host = getattr(master, 'master_host', '')
    good_masters.append({
        'name': master_name,
        'host': host,
        'port': getattr(master, 'master_port', 0),
        'slave_port': getattr(master, 'slave_port', 0),
        'alt_port': getattr(master, 'master_port_alt', 0),
        'buildbot_url': getattr(master, 'buildbot_url', ''),
        'dirname': os.path.basename(getattr(master, 'local_config_path', ''))
    })
  return good_masters


def real_main(include_internal=False):
  opts = get_args()

  bootstrap.ImportMasterConfigs(include_internal=include_internal)

  masters = extract_masters(config_bootstrap.Master.__dict__)

  # Define sorting order
  sort_keys = ['host', 'port', 'alt_port', 'slave_port', 'name']
  # Move key specified on command-line to the front of the list
  if opts.sort_by is not None:
    try:
      index = sort_keys.index(opts.sort_by)
    except ValueError:
      pass
    else:
      sort_keys.insert(0, sort_keys.pop(index))

  for key in reversed(sort_keys):
    masters.sort(key=lambda m: m[key]) # pylint: disable=cell-var-from-loop

  if not opts.full_host_names:
    for master in masters:
      master['host'] = format_host_name(master['host'])

  if opts.csv:
    printer = csv_print
  else:
    printer = human_print

  if opts.list:
    if opts.json:
      print json.dumps(masters,
                       sort_keys=True, indent=2, separators=(',', ': '))
    else:
      master_map(masters, printer, opts)

  ret = 0
  if opts.audit or opts.presubmit:
    ret = master_audit(masters, printer, opts)

  if opts.find:
    find_port(opts.find, masters, printer, opts)

  return ret


def main():
  return real_main(include_internal=False)


if __name__ == '__main__':
  sys.exit(main())
