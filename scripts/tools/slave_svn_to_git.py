#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import datetime
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
import urllib2


SLAVE_GCLIENT_CONFIG = """solutions = [
  {
    "name"      : "slave.DEPS",
    "url"       : "https://chrome-internal.googlesource.com/chrome/tools/build/slave.DEPS.git",
    "deps_file" : ".DEPS.git",
    "managed"   : True,
  },
]"""

INTERNAL_GCLIENT_CONFIG = """solutions = [
  {
    "name"      : "internal.DEPS",
    "url"       : "https://chrome-internal.googlesource.com/chrome/tools/build/internal.DEPS.git",
    "deps_file" : ".DEPS.git",
    "managed"   : True,
  },
]"""

GCLIENT_CONFIGS = {
  'slave.DEPS': SLAVE_GCLIENT_CONFIG,
  'internal.DEPS': INTERNAL_GCLIENT_CONFIG,
}

PREVENT_REBOOT_FILE_CONTENT = 'slave_svn_to_git'

WHITELISTED_HOSTS = [
  # Initial slaves to test script on.
  'slave101-c4', 'slave102-c4', 'slave103-c4', 'slave104-c4', 'slave105-c4',
  'slave106-c4', 'slave107-c4', 'slave108-c4', 'slave109-c4', 'slave110-c4',

  # All slaves on chromium.fyi.
  'build1-m1', 'build4-m1', 'build5-a1', 'build27-m1', 'build28-m1',
  'build29-m1', 'build38-a1', 'build58-m1', 'build60-m1', 'build61-m1',
  'build63-a1', 'build70-m1', 'build84-a1', 'build85-a1', 'build85-m1',
  'build87-a95', 'build97-m1', 'build98-m1', 'build99-m1', 'build127-m1',
  'build128-m1', 'build129-m1', 'build130-m1', 'build154-m1', 'chromeperf80',
  'chromeperf87', 'panda8', 'slave3-c1', 'slave4-c1', 'slave5-c1', 'slave20-c1',
  'vm9-m1', 'vm12-m1', 'vm17-m1', 'vm49-m1', 'vm52-m1', 'vm190-m1', 'vm191-m1',
  'vm310-m1', 'vm311-m1', 'vm312-m1', 'vm313-m1', 'vm448-m1', 'vm452-m1',
  'vm455-m1', 'vm471-m1', 'vm480-m1', 'vm481-m1', 'vm482-m1', 'vm498-m1',
  'vm634-m1', 'vm641-m1', 'vm646-m1', 'vm649-m1', 'vm650-m1', 'vm657-m1',
  'vm658-m1', 'vm678-m1', 'vm683-m1', 'vm687-m1', 'vm693-m1', 'vm800-m1',
  'vm803-m1', 'vm820-m1', 'vm821-m1', 'vm823-m1', 'vm832-m1', 'vm835-m1',
  'vm845-m1', 'vm847-m1', 'vm848-m1', 'vm859-m1', 'vm866-m1', 'vm877-m1',
  'vm879-m1', 'vm889-m1', 'vm899-m1', 'vm909-m1', 'vm912-m1', 'vm928-m1',
  'vm929-m1', 'vm933-m1', 'vm939-m1', 'vm943-m1', 'vm950-m1', 'vm951-m1',
  'vm954-m1', 'vm961-m1', 'vm962-m1', 'vm970-m1', 'vm973-m1', 'vm974-m1',
  'vm976-m1', 'vm977-m1', 'vm978-m1', 'vm992-m1', 'vm993-m1', 'vm994-m1',
  'vm999-m1',

  # All slaves on chromium.memory.fyi.
  'build25-m1', 'build26-m1', 'build45-m1', 'build54-m1', 'build62-m1',
  'build124-a1', 'mini9-m1', 'mini17-m1', 'vm13-m1', 'vm14-m1', 'vm47-m1',
  'vm48-m1', 'vm192-m1', 'vm400-m1', 'vm401-m1', 'vm469-m1', 'vm483-m1',
  'vm496-m1', 'vm833-m1', 'vm839-m1', 'vm841-m1', 'vm857-m1', 'vm860-m1',
  'vm861-m1', 'vm862-m1', 'vm863-m1', 'vm864-m1', 'vm900-m1', 'vm908-m1',
  'vm924-m1', 'vm925-m1', 'vm926-m1', 'vm927-m1', 'vm953-m1', 'vm955-m1',
  'vm956-m1', 'vm957-m1', 'vm958-m1', 'vm963-m1', 'vm964-m1', 'vm965-m1',
  'vm966-m1', 'vm967-m1', 'vm985-m1', 'vm986-m1', 'vm987-m1', 'vm988-m1',
  'vm989-m1', 'vm995-m1',

  # All slaves on tryserver.chromium.linux.
  'build1-b4', 'build2-b4', 'build3-b4', 'build4-b4', 'build5-b4', 'build6-b4',
  'build7-b4', 'build8-b4', 'build9-a4', 'build9-b4', 'build10-b4',
  'build11-b4', 'build12-b4', 'build13-b4', 'build14-b4', 'build15-b4',
  'build16-b4', 'build17-b4', 'build18-b4', 'build19-b4', 'build20-b4',
  'build21-b4', 'build22-b4', 'build23-b4', 'build24-b4', 'build25-a4',
  'build25-b4', 'build26-a4', 'build100-a4', 'build101-a4', 'build102-a4',
  'build103-a4', 'build104-a4', 'build105-a4', 'build106-a4', 'build107-a4',
  'build108-a4', 'build109-a4', 'build110-a4', 'build111-a4', 'build112-a4',
  'build113-a4', 'build114-a4', 'build115-a4', 'build116-a4', 'build117-a4',
  'build118-a4', 'build119-a4', 'build120-a4', 'build121-a4', 'build122-a4',
  'build123-a4', 'build124-a4', 'build125-a4', 'build126-a4', 'build127-a4',
  'build128-a4', 'build129-a4', 'build130-a4', 'build131-a4', 'build132-a4',
  'build133-a4', 'build134-a4', 'build135-a4', 'build136-a4', 'build137-a4',
  'build138-a4', 'build139-a4', 'build225-a4', 'build226-a4', 'build227-a4',
  'build228-a4', 'slave101-c4', 'slave102-c4', 'slave103-c4', 'slave104-c4',
  'slave105-c4', 'slave106-c4', 'slave107-c4', 'slave108-c4', 'slave109-c4',
  'slave110-c4', 'slave111-c4', 'slave112-c4', 'slave113-c4', 'slave114-c4',
  'slave115-c4', 'slave116-c4', 'slave117-c4', 'slave118-c4', 'slave119-c4',
  'slave120-c4', 'slave121-c4', 'slave122-c4', 'slave123-c4', 'slave124-c4',
  'slave125-c4', 'slave126-c4', 'slave127-c4', 'slave128-c4', 'slave129-c4',
  'slave130-c4', 'slave162-c4', 'slave163-c4', 'slave164-c4', 'slave165-c4',
  'slave166-c4', 'slave167-c4', 'slave168-c4', 'slave169-c4', 'slave170-c4',
  'slave171-c4', 'slave172-c4', 'slave173-c4', 'slave174-c4', 'slave175-c4',
  'slave176-c4', 'slave177-c4', 'slave178-c4', 'slave179-c4', 'slave180-c4',
  'slave181-c4', 'slave182-c4', 'slave183-c4', 'slave184-c4', 'slave185-c4',
  'slave186-c4', 'slave187-c4', 'slave188-c4', 'slave189-c4', 'slave190-c4',
  'slave191-c4', 'slave192-c4', 'slave193-c4', 'slave194-c4', 'slave195-c4',
  'slave196-c4', 'slave197-c4', 'slave198-c4', 'slave199-c4', 'slave200-c4',
  'slave201-c4', 'slave202-c4', 'slave203-c4', 'slave204-c4', 'slave205-c4',
  'slave206-c4', 'slave207-c4', 'slave208-c4', 'slave209-c4', 'slave210-c4',
  'slave211-c4', 'slave212-c4', 'slave213-c4', 'slave214-c4', 'slave215-c4',
  'slave216-c4', 'slave217-c4', 'slave218-c4', 'slave219-c4', 'slave220-c4',
  'slave221-c4', 'slave222-c4', 'slave223-c4', 'slave224-c4', 'slave225-c4',
  'slave226-c4', 'slave227-c4', 'slave228-c4', 'slave229-c4', 'slave230-c4',
  'slave231-c4', 'slave232-c4', 'slave233-c4', 'slave234-c4', 'slave235-c4',
  'slave236-c4', 'slave237-c4', 'slave238-c4', 'slave239-c4', 'slave240-c4',
  'slave241-c4', 'slave242-c4', 'slave243-c4', 'slave244-c4', 'slave245-c4',
  'slave246-c4', 'slave247-c4', 'slave248-c4', 'slave249-c4', 'slave250-c4',
  'slave251-c4', 'slave252-c4', 'slave253-c4', 'slave254-c4', 'slave255-c4',
  'slave256-c4', 'slave257-c4', 'slave258-c4', 'slave259-c4', 'slave260-c4',
  'slave261-c4', 'slave262-c4', 'slave263-c4', 'slave264-c4', 'slave265-c4',
  'slave266-c4', 'slave267-c4', 'slave268-c4', 'slave269-c4', 'slave270-c4',
  'slave271-c4', 'slave272-c4', 'slave273-c4', 'slave274-c4', 'slave275-c4',
  'slave276-c4', 'slave277-c4', 'slave278-c4', 'slave279-c4', 'slave280-c4',
  'slave281-c4', 'slave282-c4', 'slave283-c4', 'slave284-c4', 'slave285-c4',
  'slave286-c4', 'slave287-c4', 'slave288-c4', 'slave289-c4', 'slave290-c4',
  'slave291-c4', 'slave292-c4', 'slave293-c4', 'slave294-c4', 'slave295-c4',
  'slave296-c4', 'slave297-c4', 'slave298-c4', 'slave299-c4', 'slave300-c4',
  'slave301-c4', 'slave302-c4', 'slave303-c4', 'slave304-c4', 'slave305-c4',
  'slave306-c4', 'slave307-c4', 'slave308-c4', 'slave309-c4', 'slave310-c4',
  'slave311-c4', 'slave312-c4', 'slave313-c4', 'slave314-c4', 'slave315-c4',
  'slave316-c4', 'slave317-c4', 'slave318-c4', 'slave319-c4', 'slave320-c4',
  'slave321-c4', 'slave322-c4', 'slave323-c4', 'slave324-c4', 'slave325-c4',
  'slave326-c4', 'slave327-c4', 'slave328-c4', 'slave329-c4', 'slave330-c4',
  'slave331-c4', 'slave332-c4', 'slave333-c4', 'slave334-c4', 'slave335-c4',
  'slave336-c4', 'slave337-c4', 'slave338-c4', 'slave339-c4', 'slave340-c4',
  'slave341-c4', 'slave342-c4', 'slave343-c4', 'slave344-c4', 'slave345-c4',
  'slave346-c4', 'slave347-c4', 'slave348-c4', 'slave349-c4', 'slave350-c4',
  'slave351-c4', 'slave352-c4', 'slave353-c4', 'slave354-c4', 'slave355-c4',
  'slave356-c4', 'slave357-c4', 'slave358-c4', 'slave359-c4', 'slave360-c4',
  'slave361-c4', 'slave362-c4', 'slave363-c4', 'slave364-c4', 'slave365-c4',
  'slave366-c4', 'slave367-c4', 'slave368-c4', 'slave369-c4', 'slave370-c4',
  'slave371-c4', 'slave372-c4', 'slave373-c4', 'slave374-c4', 'slave375-c4',
  'slave376-c4', 'slave377-c4', 'slave378-c4', 'slave379-c4', 'slave380-c4',
  'slave381-c4', 'slave382-c4', 'slave383-c4', 'slave384-c4', 'slave385-c4',
  'slave386-c4', 'slave387-c4', 'slave388-c4', 'slave389-c4', 'slave390-c4',
  'slave391-c4', 'slave392-c4', 'slave393-c4', 'slave394-c4', 'slave395-c4',
  'slave396-c4', 'slave397-c4', 'slave398-c4', 'slave426-c4', 'slave427-c4',
  'slave428-c4', 'slave429-c4', 'slave430-c4', 'slave431-c4', 'slave432-c4',
  'slave433-c4', 'slave434-c4', 'slave435-c4', 'slave436-c4', 'slave437-c4',
  'slave438-c4', 'slave439-c4', 'slave440-c4', 'slave441-c4', 'slave442-c4',
  'slave443-c4', 'slave444-c4', 'slave445-c4', 'slave446-c4', 'slave447-c4',
  'slave448-c4', 'slave449-c4', 'slave450-c4', 'slave451-c4', 'slave452-c4',
  'slave453-c4', 'slave454-c4', 'slave455-c4', 'slave456-c4', 'slave457-c4',
  'slave458-c4', 'slave459-c4', 'slave460-c4', 'slave461-c4', 'slave462-c4',
  'slave463-c4', 'slave464-c4', 'slave465-c4', 'slave466-c4', 'slave467-c4',
  'slave468-c4', 'slave469-c4', 'slave470-c4', 'slave471-c4', 'slave472-c4',
  'slave473-c4', 'slave474-c4', 'slave475-c4', 'slave476-c4', 'slave477-c4',
  'slave478-c4', 'slave479-c4', 'slave480-c4', 'slave481-c4', 'slave482-c4',
  'slave483-c4', 'slave484-c4', 'slave485-c4', 'slave486-c4', 'slave487-c4',
  'slave488-c4', 'slave489-c4', 'slave490-c4', 'slave491-c4', 'slave493-c4',
  'slave494-c4', 'slave495-c4', 'slave496-c4', 'slave506-c4', 'slave507-c4',
  'slave508-c4', 'slave509-c4', 'slave510-c4', 'slave511-c4', 'slave512-c4',
  'slave513-c4', 'slave514-c4', 'slave515-c4', 'slave516-c4', 'slave517-c4',
  'slave518-c4', 'slave519-c4', 'slave520-c4', 'slave521-c4', 'slave522-c4',
  'slave523-c4', 'slave524-c4', 'slave525-c4', 'slave526-c4', 'slave527-c4',
  'slave528-c4', 'slave529-c4', 'slave530-c4', 'slave531-c4', 'slave532-c4',
  'slave533-c4', 'slave534-c4', 'slave535-c4', 'slave536-c4', 'slave537-c4',
  'slave538-c4', 'slave539-c4', 'slave568-c4', 'slave590-c4', 'slave591-c4',
  'slave592-c4', 'slave593-c4', 'slave594-c4', 'slave595-c4', 'slave596-c4',
  'slave597-c4', 'slave598-c4', 'slave599-c4', 'slave621-c4', 'slave622-c4',
  'slave623-c4', 'slave624-c4', 'slave625-c4', 'slave626-c4', 'slave627-c4',
  'slave628-c4', 'slave629-c4', 'slave630-c4', 'slave631-c4', 'slave632-c4',
  'slave633-c4', 'slave634-c4', 'slave635-c4', 'slave636-c4', 'slave637-c4',
  'slave638-c4', 'slave639-c4', 'slave640-c4', 'slave641-c4', 'slave642-c4',
  'slave643-c4', 'slave644-c4', 'slave645-c4', 'slave646-c4', 'slave647-c4',
  'slave648-c4', 'slave649-c4', 'slave650-c4', 'slave714-c4', 'slave715-c4',
  'slave716-c4', 'slave717-c4', 'slave718-c4', 'slave747-c4', 'slave748-c4',
  'slave749-c4', 'slave750-c4', 'slave751-c4', 'slave752-c4', 'slave753-c4',
  'slave754-c4', 'slave755-c4', 'slave756-c4', 'slave757-c4', 'slave758-c4',
  'slave759-c4', 'slave760-c4', 'slave761-c4', 'slave762-c4', 'slave763-c4',
  'slave764-c4', 'slave765-c4', 'slave766-c4', 'slave779-c4', 'slave780-c4',
  'slave781-c4', 'slave782-c4', 'slave783-c4', 'slave784-c4', 'slave785-c4',
  'slave786-c4', 'slave787-c4', 'slave788-c4', 'slave789-c4', 'slave790-c4',
  'slave791-c4', 'slave792-c4', 'slave793-c4', 'slave794-c4', 'slave795-c4',
  'slave796-c4', 'slave797-c4', 'slave798-c4', 'slave841-c4', 'slave842-c4',
  'slave843-c4', 'slave844-c4', 'slave845-c4', 'slave846-c4', 'slave847-c4',
  'slave848-c4', 'slave849-c4', 'slave850-c4', 'slave851-c4', 'slave852-c4',
  'slave853-c4', 'slave854-c4', 'slave855-c4', 'slave856-c4', 'slave857-c4',
  'slave858-c4', 'slave859-c4', 'slave860-c4', 'slave861-c4', 'slave862-c4',
  'slave863-c4', 'slave866-c4', 'slave867-c4', 'vm117-m4', 'vm162-m4',
  'vm163-m4', 'vm188-m4', 'vm193-m4', 'vm196-m4', 'vm198-m4', 'vm201-m4',
  'vm203-m4', 'vm211-m4', 'vm227-m4', 'vm260-m4', 'vm338-m4', 'vm786-m4',
  'vm787-m4', 'vm788-m4', 'vm804-m4', 'vm822-m4', 'vm824-m4', 'vm825-m4',
  'vm826-m4', 'vm827-m4', 'vm828-m4', 'vm897-m4',

  # Some slaves on tryserver.chromium.win.
  'build44-m4', 'slave0-c4', 'slave1-c4', 'slave2-c4', 'slave3-c4', 'slave4-c4',
  'slave5-c4', 'slave6-c4', 'slave7-c4', 'slave8-c4', 'slave9-c4', 'slave10-c4',
  'vm158-m4', 'vm159-m4', 'vm160-m4', 'vm161-m4', 'vm168-m4', 'vm177-m4',
  'vm182-m4', 'vm183-m4', 'vm187-m4', 'vm192-m4', 'vm197-m4', 'vm202-m4',

  # Some slaves on tryserver.chromium.mac.
  'build21-m4', 'build73-m4', 'build79-a4', 'build80-a4', 'build81-a4',
  'build83-a4', 'build84-a4', 'build85-a4', 'build86-a4', 'build87-a4',
  'vm257-m4', 'vm258-m4', 'vm277-m4', 'vm278-m4', 'vm279-m4', 'vm280-m4',
  'vm982-m4', 'vm983-m4', 'vm984-m4', 'vm985-m4', 'vm986-m4', 'vm1000-m4',
]

is_win = sys.platform.startswith('win')


def check_call(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  subprocess.check_call(cmd, cwd=cwd, shell=is_win, env=env)


def check_output(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  return subprocess.check_output(cmd, cwd=cwd, shell=is_win, env=env)


def report_host_state(b_dir, cur_host):
  """Report host state to the tracking app."""
  if os.path.isdir(os.path.join(b_dir, 'build', '.svn')):
    state = 'SVN'
  elif os.path.isdir(os.path.join(b_dir, 'build', '.git')):
    state = 'GIT'
  else:
    state = 'UNKNOWN'

  try:
    url = ('https://svn-to-git-tracking.appspot.com/api/reportState?host=%s&'
           'state=%s' % (urllib2.quote(cur_host), urllib2.quote(state)))
    urllib2.urlopen(url)
  except Exception:
    pass


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--manual', action='store_true', default=False,
                      help='Run in manual mode')
  parser.add_argument('--leak-tmp-dir', action='store_true', default=False,
                      help='Leaves temporary checkout dir on disk')
  options = parser.parse_args()

  # Find b directory.
  b_dir = None
  if is_win:
    if os.path.exists('E:\\b'):
      b_dir = 'E:\\b'
    elif os.path.exists('C:\\b'):
      b_dir = 'C:\\b'
  elif os.path.exists('/b'):
    b_dir = '/b'
  assert b_dir is not None and os.path.isdir(b_dir), 'Did not find b dir'

  # Report state before doing anything else, so we can keep track of the state
  # of this host even if something later in this script fails.
  cur_host = socket.gethostname()
  report_host_state(b_dir, cur_host)

  # Check if host is whitelisted.
  if not options.manual:
    if not any(host.lower() in cur_host.lower() for host in WHITELISTED_HOSTS):
      print 'Host %s is not whitelisted for SVN-to-Git conversion' % cur_host
      return 0

  # Set up credentials for the download_from_google_storage hook.
  env = os.environ.copy()
  boto_file = os.path.join(b_dir, 'build', 'site_config', '.boto')
  if os.path.isfile(boto_file):
    env['AWS_CREDENTIAL_FILE'] = boto_file

  # Add depot_tools to PATH, so that gclient can be found.
  env_path_sep = ';' if is_win else ':'
  env['PATH'] = '%s%s%s' % (env['PATH'], env_path_sep,
                            os.path.join(b_dir, 'depot_tools'))

  # Find old .gclient config.
  gclient_path = os.path.join(b_dir, '.gclient')
  assert os.path.isfile(gclient_path), 'Did not find old .gclient config'

  # Detect type of checkout.
  with open(gclient_path) as gclient_file:
    exec_env = {}
    exec gclient_file in exec_env
    solutions = exec_env['solutions']
  assert len(solutions) == 1, 'Number of solutions in .gclient is not 1'
  if not solutions[0]['url'].startswith('svn:'):
    print 'Non-SVN URL in .gclient: %s' % solutions[0]['url']
    return 0
  sol_name = solutions[0]['name']
  assert sol_name in GCLIENT_CONFIGS, 'Unknown type of checkout: ' % sol_name
  gclient_config = GCLIENT_CONFIGS[sol_name]

  prevent_reboot_path = os.path.join(os.path.expanduser('~'), 'no_reboot')
  tmpdir = tempfile.mkdtemp(dir=os.path.realpath(b_dir),
                            prefix='slave_svn_to_git')
  try:
    # Create new temp Git checkout.
    with open(os.path.join(tmpdir, '.gclient'), 'w') as gclient_file:
      gclient_file.write(gclient_config)

    # Sync both repos (SVN first since mirroring happens from SVN to Git).
    try:
      check_call(['gclient', 'sync'], cwd=b_dir, env=env)
    except subprocess.CalledProcessError:
      # On Windows, gclient sync occasionally reports 'checksum mismatch' error
      # for build/scripts/slave/recipes/deterministic_build.expected/
      # full_chromium_swarm_linux_deterministic.json when calling 'svn update'
      # on 'build' directory. As a workaround, we delete parent dir containing
      # invalid .svn files and try again. The missing directory should be
      # re-created with the correct checksum by repeated call to 'svn update'.
      if is_win:
        shutil.rmtree(os.path.join(b_dir, 'build', 'scripts', 'slave',
                                   'recipes', 'deterministic_build.expected'))
        check_call(['gclient', 'sync'], cwd=b_dir, env=env)
      else:
        raise

    check_call(['gclient', 'sync'], cwd=tmpdir, env=env)

    # Find repositories handled by gclient.
    revinfo = check_output(['gclient', 'revinfo'], cwd=tmpdir, env=env)
    repos = {}
    for line in revinfo.splitlines():
      relpath, repospec = line.split(':', 1)
      repos[relpath.strip()] = repospec.strip()

    # Sanity checks.
    for relpath in sorted(repos):
      # Only process directories that have .svn dir in them.
      if not os.path.isdir(os.path.join(b_dir, relpath, '.svn')):
        print '%s subdir does not have .svn directory' % relpath
        del repos[relpath]
        continue
      # Make sure Git directory exists.
      assert os.path.isdir(os.path.join(tmpdir, relpath, '.git'))

    # Prevent slave from rebooting unless no_reboot already exists.
    if not os.path.exists(prevent_reboot_path):
      with open(prevent_reboot_path, 'w') as prevent_reboot_file:
        prevent_reboot_file.write(PREVENT_REBOOT_FILE_CONTENT)

    # Move SVN .gclient away so that no one can run gclient sync while
    # conversion is in progress.
    print 'Moving .gclient to .gclient.svn in %s' % b_dir
    shutil.move(gclient_path, '%s.svn' % gclient_path)

    # Rename all .svn directories into .svn.backup.
    svn_dirs = []
    count = 0
    print 'Searching for .svn folders'
    for root, dirs, _files in os.walk(b_dir):
      count += 1
      if count % 100 == 0:
        print 'Processed %d directories' % count
      if '.svn' in dirs:
        svn_dirs.append(os.path.join(root, '.svn'))
        dirs.remove('.svn')
    for rel_svn_dir in svn_dirs:
      svn_dir = os.path.join(b_dir, rel_svn_dir)
      print 'Moving %s to %s.backup' % (svn_dir, svn_dir)
      shutil.move(svn_dir, '%s.backup' % svn_dir)

    # Move Git directories from temp dir to the checkout.
    for relpath, repospec in sorted(repos.iteritems()):
      src_git = os.path.join(tmpdir, relpath, '.git')
      dest_git = os.path.join(b_dir, relpath, '.git')
      print 'Moving %s to %s' % (src_git, dest_git)
      shutil.move(src_git, dest_git)

    # Revert any local modifications after the conversion to Git.
    home_dir = os.path.realpath(os.path.expanduser('~'))
    for relpath in sorted(repos):
      abspath = os.path.join(b_dir, relpath)
      diff = check_output(['git', 'diff'], cwd=abspath)
      if diff:
        diff_name = '%s.diff' % re.sub('[^a-zA-Z0-9]', '_', relpath)
        with open(os.path.join(home_dir, diff_name), 'w') as diff_file:
          diff_file.write(diff)
        check_call(['git', 'reset', '--hard'], cwd=abspath)

    # Update .gclient file to reference Git DEPS.
    with open(os.path.join(b_dir, '.gclient'), 'w') as gclient_file:
      gclient_file.write(gclient_config)
  finally:
    # Remove the temporary directory.
    if not options.leak_tmp_dir:
      shutil.rmtree(tmpdir)

    # Remove no_reboot file if it was created by this script.
    if os.path.isfile(prevent_reboot_path):
      with open(prevent_reboot_path, 'r') as prevent_reboot_file:
        prevent_reboot_content = prevent_reboot_file.read()
      if prevent_reboot_content == PREVENT_REBOOT_FILE_CONTENT:
        os.unlink(prevent_reboot_path)

  # Run gclient sync again.
  check_call(['gclient', 'sync'], cwd=b_dir, env=env)

  # Report state again, since we've converted to Git.
  report_host_state(b_dir, cur_host)

  return 0


if __name__ == '__main__':
  print 'Running slave_svn_to_git on %s UTC' % datetime.datetime.utcnow()
  try:
    retcode = main()
  except Exception as e:
    traceback.print_exc(e)
    retcode = 1
  print 'Return code: %d' % retcode
  sys.exit(retcode)
