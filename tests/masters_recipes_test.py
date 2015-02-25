#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import subprocess
import sys
import tempfile


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts', 'slave', 'recipes'))
sys.path.insert(
    0, os.path.join(BASE_DIR, 'scripts', 'slave', 'recipe_modules'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party'))

import chromium_trybot
from chromium.builders import BUILDERS


MAIN_WATERFALL_MASTERS = [
    'master.chromium.chrome',
    'master.chromium.chromiumos',
    'master.chromium.gpu',
    'master.chromium.linux',
    'master.chromium.mac',
    'master.chromium.memory',
    'master.chromium.win',
]


TRYSERVER_MASTERS = [
    'master.tryserver.chromium.linux',
    'master.tryserver.chromium.mac',
    'master.tryserver.chromium.win',
]


SUPPRESSIONS = {
    'master.chromium.chrome': [
        'Google Chrome ChromeOS',
        'Google Chrome Linux',
        'Google Chrome Linux x64',
        'Google Chrome Mac',
        'Google Chrome Win',
    ],
    'master.chromium.chromiumos': [
        'Linux ChromiumOS Full',
        'Linux ChromiumOS GN',
    ],
    'master.chromium.gpu': [
        'Android Debug (Nexus 7)',
        'GPU Linux Builder (dbg)',
        'GPU Linux Builder',
        'GPU Mac Builder (dbg)',
        'GPU Mac Builder',
        'GPU Win Builder (dbg)',
        'GPU Win Builder',
        'Linux Debug (NVIDIA)',
        'Linux Release (NVIDIA)',
        'Mac 10.8 Debug (Intel)',
        'Mac 10.8 Release (ATI)',
        'Mac 10.8 Release (Intel)',
        'Mac Debug (Intel)',
        'Mac Release (ATI)',
        'Mac Release (Intel)',
        'Mac Retina Debug',
        'Mac Retina Release',
        'Win7 Debug (NVIDIA)',
        'Win7 Release (NVIDIA)',
        'Win8 Debug (NVIDIA)',
        'Win8 Release (NVIDIA)',
    ],
    'master.chromium.linux': [
        'Android GN',
        'Android Webview AOSP Builder',
        'Linux GN',
        'Linux GN (dbg)',
    ],
    'master.chromium.mac': [
        'Mac GN',
        'Mac GN (dbg)',
        'Mac10.9 Tests',
    ],
    'master.chromium.memory': [
        'Linux ASan Tests (sandboxed)',
    ],
    'master.chromium.win': [
        'Win x64 Builder (dbg)',
        'Win8 GN',
        'Win8 GN (dbg)',
    ],
}

UNUSED_MAIN_WATERFALL_BUILDERS = {
    'master.chromium.linux': [
        'Android x86 Builder (dbg)',
    ],
}


def getMasterConfig(master):
  with tempfile.NamedTemporaryFile() as f:
    subprocess.check_call([
        os.path.join(BASE_DIR, 'scripts', 'tools', 'runit.py'),
        os.path.join(BASE_DIR, 'scripts', 'tools', 'dump_master_cfg.py'),
        os.path.join(BASE_DIR, 'masters/%s' % master),
        f.name])
    return json.load(f)


def getBuildersAndRecipes(master):
  return {
      builder['name'] : builder['factory']['properties'].get(
          'recipe', [None])[0]
      for builder in getMasterConfig(master)['builders']
  }


def mutualDifference(a, b):
  return a - b, b - a


def main(argv):
  chromium_recipe_builders = {}
  covered_builders = set()
  all_builders = set()

  exit_code = 0

  for master in MAIN_WATERFALL_MASTERS:
    builders = getBuildersAndRecipes(master)
    # iOS bots are excluded, because they enforce that there is a try bot
    # version of each main waterfall bot in a different way.
    all_builders.update((master, b) for b in builders if 'iOS' not in b)

    # We only have a standardized way to mirror builders using the chromium
    # recipe on the tryserver.
    chromium_recipe_builders[master] = [b for b in builders
                                        if builders[b] == 'chromium']

    # TODO(phajdan.jr): Also consider it an error if configured builders
    # are not using chromium recipe. This might make it harder to experiment
    # with switching bots over to chromium recipe though, so it may be better
    # to just wait until the switch is done.
    recipe_side_builders = BUILDERS.get(
        master.replace('master.', ''), {}).get('builders')
    if recipe_side_builders is not None:
      bogus_builders = set(recipe_side_builders.keys()).difference(
          set(builders.keys()))
      bogus_builders, unused = mutualDifference(
          bogus_builders,
          set(UNUSED_MAIN_WATERFALL_BUILDERS.get(master, [])))
      # TODO(phajdan.jr): Clean up bogus chromiumos builders.
      if bogus_builders and master != 'master.chromium.chromiumos':
        exit_code = 1
        print 'The following builders from chromium recipe'
        print 'do not exist in master config for %s:' % master
        print '\n'.join('\t%s' % b for b in sorted(bogus_builders))
      if unused:
        exit_code = 1
        print 'The following unused declarations are superfluous '
        print 'on %s' % master
        print '\n'.join('\t%s' % b for b in sorted(unused))


  for master in TRYSERVER_MASTERS:
    builders = getBuildersAndRecipes(master)
    recipe_side_builders = chromium_trybot.BUILDERS[
        master.replace('master.', '')]['builders']

    bogus_builders = set(recipe_side_builders.keys()).difference(
        set(builders.keys()))
    if bogus_builders:
      exit_code = 1
      print 'The following builders from chromium_trybot recipe'
      print 'do not exist in master config for %s:' % master
      print '\n'.join('\t%s' % b for b in sorted(bogus_builders))

    for builder, recipe in builders.iteritems():
      # Only the chromium_trybot recipe knows how to mirror a main waterfall
      # builder.
      if recipe != 'chromium_trybot':
        continue

      bot_config = recipe_side_builders.get(builder)
      if not bot_config:
        continue

      # TODO(phajdan.jr): Make it an error if any builders referenced here
      # are not using chromium recipe.
      main_waterfall_master = 'master.' + bot_config['mastername']
      bots = [bot_config['buildername']]
      if bot_config.get('tester'):
        bots.append(bot_config['tester'])
      for mw_builder in bots:
        if mw_builder in chromium_recipe_builders.get(
            main_waterfall_master, []):
          covered_builders.add((main_waterfall_master, mw_builder))

  # TODO(phajdan.jr): Add a way to only count trybots launched by CQ by default.
  print 'Main waterfall ng-trybot coverage: %.2f' % (
      100.0 * len(covered_builders) / len(all_builders))

  not_covered_builders = all_builders.difference(covered_builders)
  suppressed_builders = set()
  for master, builders in SUPPRESSIONS.iteritems():
    suppressed_builders.update((master, b) for b in builders)

  regressed_builders = not_covered_builders.difference(suppressed_builders)
  if regressed_builders:
    exit_code = 1
    print 'Regression, the following builders lack in-sync tryserver coverage:'
    print '\n'.join(sorted(
        '\t%s:%s' % (b[0], b[1]) for b in regressed_builders))

  unused_suppressions = suppressed_builders.difference(not_covered_builders)
  if unused_suppressions:
    exit_code = 1
    print 'Unused suppressions:'
    print '\n'.join(sorted(
        '\t%s:%s' % (b[0], b[1]) for b in unused_suppressions))

  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
