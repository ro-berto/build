#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import os
import subprocess
import sys
import tempfile


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MAIN_WATERFALL_MASTERS = [
    'master.chromium',
    'master.chromium.chrome',
    'master.chromium.chromiumos',
    'master.chromium.gpu',
    'master.chromium.linux',
    'master.chromium.mac',
    'master.chromium.memory',
    'master.chromium.webkit',
    'master.chromium.win',
]


TRYSERVER_MASTERS = [
    'master.tryserver.blink',
    'master.tryserver.chromium.android',
    'master.tryserver.chromium.angle',
    'master.tryserver.chromium.chromiumos',
    'master.tryserver.chromium.linux',
    'master.tryserver.chromium.mac',
    'master.tryserver.chromium.win',
]


SUPPRESSIONS = {
    'master.chromium.chrome': [
        'Google Chrome ChromeOS',
        'Google Chrome Linux x64',
        'Google Chrome Mac',
    ],
    'master.chromium.chromiumos': [
        'Linux ChromiumOS Full',
    ],
    'master.chromium.gpu': [
        'GPU Linux Builder (dbg)',
        'GPU Mac Builder (dbg)',
        'GPU Win Builder (dbg)',
        'Linux Debug (NVIDIA)',
        'Mac Debug (Intel)',
        'Mac Retina Debug (AMD)',
        'Win10 Debug (NVIDIA)',
        # TODO(kbr): remove as soon as this is part of android_n5x_swarming_rel.
        'Android Release (Nexus 5X)',
    ],
    'master.chromium.linux': [
        'Deterministic Linux',
    ],
    'master.chromium.mac': [
        'ios-device', # these are covered, just by the iOS recipes instead.
        'ios-device-xcode-clang',
        'ios-simulator',
        'ios-simulator-full-configs',
        'ios-simulator-xcode-clang',

        'Mac10.11 Tests',
    ],
    'master.chromium.memory': [
        'Linux ASan Tests (sandboxed)',
    ],
    'master.chromium.webkit': [
        # TODO(crbug.com/736257) Spin up 10.12 (dbg) trybots once we've
        # finished shutting down the 10.9 bots.
        'WebKit Mac Builder (dbg)',
        'WebKit Mac10.11 (dbg)',

        'WebKit Linux Trusty ASAN',
        'WebKit Linux Trusty MSAN',
        'WebKit Win x64 Builder',
        'WebKit Win x64 Builder (dbg)',
    ],
    'master.chromium.win': [
        'Win7 (32) Tests',
        'Win x64 Builder (dbg)',
    ],
}


# FIXME(tansell): Remove fake when BlinkTests are removed.
FAKE_BUILDERS = {
    'master.tryserver.chromium.win' : [
        'old_chromium_rel_ng',
    ],
}


def getBuilders(recipe_name):
  """Asks the given recipe to dump its BUILDERS dictionary.

  This must be implemented by the recipe in question.

  packages. This is to avoid git.lock collision.
  """
  (fh, builders_file) = tempfile.mkstemp('.json')
  os.close(fh)
  try:
    subprocess.check_call([
        os.path.join(BASE_DIR, 'scripts', 'slave', 'recipes.py'),
        'run', recipe_name, 'dump_builders=%s' % builders_file])
    with open(builders_file) as fh:
      return json.load(fh)
  finally:
    os.remove(builders_file)


def getCQBuilders(cq_config):
  # This relies on 'commit_queue' tool from depot_tools.
  output = subprocess.check_output(['commit_queue', 'builders', cq_config])
  return json.loads(output)


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
  parser = argparse.ArgumentParser()
  parser.add_argument('--cq-config', help='Path to CQ config')
  parser.add_argument('--verbose', action='store_true')
  args = parser.parse_args()

  chromium_recipe_builders = {}
  covered_builders = set()
  all_builders = set()

  exit_code = 0

  chromium_trybot_BUILDERS = getBuilders('chromium_trybot')
  chromium_BUILDERS = getBuilders('chromium')

  cq_builders = getCQBuilders(args.cq_config) if args.cq_config else None

  for master in MAIN_WATERFALL_MASTERS:
    builders = getBuildersAndRecipes(master)
    all_builders.update((master, b) for b in builders)

    # We only have a standardized way to mirror builders using the chromium
    # recipe on the tryserver.
    chromium_recipe_builders[master] = [b for b in builders
                                        if builders[b] == 'chromium']

    recipe_side_builders = chromium_BUILDERS.get(
        master.replace('master.', ''), {}).get('builders')
    if recipe_side_builders is not None:
      bogus_builders = set(recipe_side_builders.keys()).difference(
          set(builders.keys()))
      if bogus_builders:
        exit_code = 1
        print 'The following builders from chromium recipe'
        print 'do not exist in master config for %s:' % master
        print '\n'.join('\t%s' % b for b in sorted(bogus_builders))

      other_recipe_builders = set(recipe_side_builders.keys()).difference(
          set(chromium_recipe_builders[master]))
      if other_recipe_builders:
        exit_code = 1
        print 'The following builders from chromium recipe'
        print 'are configured to run a different recipe on the master'
        print '(%s):' % master
        print '\n'.join('\t%s' % b for b in sorted(other_recipe_builders))

  for master in TRYSERVER_MASTERS:
    short_master = master.replace('master.', '')
    builders = getBuildersAndRecipes(master)
    recipe_side_builders = chromium_trybot_BUILDERS[
        short_master]['builders']

    bogus_builders = set(recipe_side_builders.keys()).difference(
        set(builders.keys()))

    # FIXME(tansell): Remove fake when BlinkTests are removed.
    for fake in FAKE_BUILDERS.get(master, []):
      if fake in bogus_builders:
        bogus_builders.remove(fake)

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

      if args.cq_config and builder not in cq_builders.get(short_master, {}):
        continue

      # TODO(phajdan.jr): Make it an error if any builders referenced here
      # are not using chromium recipe.
      for bot_id in bot_config['bot_ids']:
        main_waterfall_master = 'master.' + bot_id['mastername']
        bots = [bot_id['buildername']]
        if bot_id.get('tester'):
          bots.append(bot_id['tester'])
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
