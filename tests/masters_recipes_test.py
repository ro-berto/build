#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MAIN_WATERFALL_MASTERS = [
    'master.chromium',
]


TRYSERVER_MASTERS = [
    'master.tryserver.chromium.mac',
]


SUPPRESSIONS = {
}


# TODO(hinoka): Remove this after LUCI migration.
FAKE_BUILDERS = {
    'master.chromium': [
      # These have been migrated to LUCI.
      'Android',
      'Linux x64',
      'Mac',
      'Win',
      'Win x64',
      'android-archive-dbg',
      'android-dbg',
      'android-archive-rel',
      'android-rel',
      'linux-archive-dbg',
      'linux-dbg',
      'linux-archive-rel',
      'linux-rel',
      'mac-archive-dbg',
      'mac-dbg',
      'mac-archive-rel',
      'mac-rel',
      'win32-archive-dbg',
      'win32-dbg',
      'win32-archive-rel',
      'win32-rel',
      'win-archive-dbg',
      'win-dbg',
      'win-archive-rel',
      'win-rel',
    ],
    'master.chromium.fyi': [
        # These are on LUCI.
        'linux-chromium-tests-staging-builder',
        'linux-chromium-tests-staging-tests',
        'linux-tcmalloc-rel',
        'Android Builder (dbg)',
        'Android ChromeDriver Tests (dbg)',
        'Android Find Annotated Test',
        'Android Remoting Tests',
        'Android VR Tests',
    ],
    'master.chromium.gpu': [
        # These have been migrated to LUCI.
        'Android Release (Nexus 5X)',
        'GPU Linux Builder (dbg)',
        'GPU Linux Builder',
        'GPU Mac Builder (dbg)',
        'GPU Mac Builder',
        'GPU Win Builder (dbg)',
        'Linux Debug (NVIDIA)',
        'Linux Release (NVIDIA)',
        'Mac Debug (Intel)',
        'Mac Release (Intel)',
        'Mac Retina Debug (AMD)',
        'Mac Retina Release (AMD)',
        'Win10 Debug (NVIDIA)',
    ],
    'master.chromium.memory': [
        # These have been migrated to LUCI.
        'Linux ASan LSan Builder',
        'Linux ASan LSan Tests (1)',
        'Linux ASan Tests (sandboxed)',
        'Linux TSan Builder',
        'Linux TSan Tests',
        'Mac ASan 64 Builder',
        'Mac ASan 64 Tests (1)',
        # These are pure LUCI bots, no equivalent buildbot bot.
        'WebKit Linux Trusty ASAN',
        'WebKit Linux Trusty MSAN',
        'WebKit Linux Trusty Leak',
        'win-asan',
    ],
    'master.chromium.win': [
        # These have been migrated to LUCI.
        'Win Builder',
        'Win x64 Builder',
        'Win Builder (dbg)',
        'Win7 (32) Tests',
        'Win7 Tests (1)',
        'Win7 Tests (dbg)(1)',
        'Win 7 Tests x64 (1)',
        'Win10 Tests x64',
        'Win10 Tests x64 (dbg)',
        # These are pure LUCI bots, no equivalent buildbot bot.
        'win-jumbo-rel',
        'WebKit Win10',  # copied from master.chromium.webkit
    ],
    'master.tryserver.chromium.win' : [
        # FIXME(tansell): Remove fake when BlinkTests are removed.
        'old_chromium_rel_ng',
        # These have been migrated to LUCI.
        'win_chromium_compile_dbg_ng',
        'win_chromium_compile_rel_ng',
        'win_chromium_dbg_ng',
        'win_optional_gpu_tests_rel',
        'win_chromium_x64_rel_ng',
        'win10_chromium_x64_rel_ng',
        'win7_chromium_rel_loc_exp',
        'win_archive',
        'win_mojo',
        'win_x64_archive',
        # These are pure LUCI bots, no equivalent buildbot bot.
        'gpu-manual-try-win7-amd-dbg',
        'gpu-manual-try-win7-amd-dqp',
        'gpu-manual-try-win7-amd-rel',
        'gpu-manual-try-win7-nvidia-dqp-64',
        'gpu-manual-try-win7-nvidia-rel',
        'gpu-manual-try-win7-nvidia-rel-64',
        'gpu-manual-try-win10-intel-dqp',
        'gpu-manual-try-win10-intel-exp',
        'gpu-manual-try-win10-intel-rel',
        'gpu-manual-try-win10-nvidia-dbg',
        'gpu-manual-try-win10-nvidia-dqp',
        'gpu-manual-try-win10-nvidia-exp',
        'gpu-manual-try-win10-nvidia-rel',
        'win10_chromium_x64_dbg_ng',
        'win7-rel',
        'win-annotator-rel',
        'win-asan',
        'win-jumbo-rel',
    ],
    'master.tryserver.chromium.linux': [
        # These have been migrated to LUCI.
        'cast_shell_audio_linux',
        'cast_shell_linux',
        'fuchsia_arm64',
        'fuchsia_arm64_cast_audio',
        'fuchsia-fyi-x64-dbg',
        'fuchsia_x64',
        'fuchsia_x64_cast_audio',
        'leak_detection_linux',
        'linux-blink-gen-property-trees',
        'linux-blink-heap-verification-try',
        'linux-goma-rbe-staging-rel',
        'linux-gcc-rel',
        'linux-rel',
        'linux-ozone-rel',
        'linux-xenial-rel',
        'linux_chromium_asan_rel_ng',
        'linux_chromium_cfi_rel_ng',
        'linux_chromium_compile_dbg_ng',
        'linux_chromium_compile_rel_ng',
        'linux_chromium_dbg_ng',
        'linux_chromium_tsan_rel_ng',
        'linux_optional_gpu_tests_rel',
        'layout_test_leak_detection',
        'linux-annotator-rel',
        'linux_arm',
        'linux_chromium_archive_rel_ng',
        'linux_chromium_chromeos_asan_rel_ng',
        'linux_chromium_chromeos_msan_rel_ng',
        'linux_chromium_clobber_rel_ng',
        'linux_chromium_compile_dbg_32_ng',
        'linux_chromium_dbg_32_ng',
        'linux_chromium_msan_rel_ng',
        'linux_layout_tests_layout_ng',
        'linux_layout_tests_slimming_paint_v2',
        'linux_mojo',
        'linux_mojo_chromeos',
        'linux_upload_clang',
        'linux_vr',
        # These are pure LUCI bots, no equivalent buildbot bot.
        'gpu-manual-try-linux-amd-rel',
        'gpu-manual-try-linux-intel-dqp',
        'gpu-manual-try-linux-intel-exp',
        'gpu-manual-try-linux-intel-ozn',
        'gpu-manual-try-linux-intel-rel',
        'gpu-manual-try-linux-nvidia-dbg',
        'gpu-manual-try-linux-nvidia-dqp',
        'gpu-manual-try-linux-nvidia-exp',
        'gpu-manual-try-linux-nvidia-rel',
        'gpu-manual-try-linux-nvidia-tsn',
        'linux-dcheck-off-rel',
        'linux-jumbo-rel',
    ],
    'master.tryserver.chromium.mac': [
        # These have been migrated to LUCI.
        'mac_chromium_10.10',
        'mac_chromium_10.12_rel_ng',
        'mac_chromium_10.13_rel_ng',
        'mac_chromium_archive_rel_ng',
        'mac_chromium_asan_rel_ng',
        'mac_chromium_compile_dbg_ng',
        'mac_chromium_compile_rel_ng',
        'mac_chromium_dbg_ng',
        'mac_optional_gpu_tests_rel',
        'ios-simulator-cronet',
        'mac-views-rel',
        # These are pure LUCI bots, no equivalent buildbot bot.
        'gpu-fyi-try-mac-amd-10.14',
        'gpu-fyi-try-mac-amd-dqp',
        'gpu-fyi-try-mac-amd-pro-rel',
        'gpu-fyi-try-mac-amd-retina-dbg',
        'gpu-fyi-try-mac-amd-retina-exp',
        'gpu-fyi-try-mac-amd-retina-rel',
        'gpu-fyi-try-mac-asan',
        'gpu-fyi-try-mac-intel-10.14',
        'gpu-fyi-try-mac-intel-dbg',
        'gpu-fyi-try-mac-intel-dqp',
        'gpu-fyi-try-mac-intel-exp',
        'gpu-fyi-try-mac-intel-rel',
        'gpu-fyi-try-mac-nvidia-10.14',
        'gpu-fyi-try-mac-nvidia-retina-dbg',
        'gpu-fyi-try-mac-nvidia-retina-exp',
        'gpu-fyi-try-mac-nvidia-retina-rel',
        'gpu-try-mac-amd-retina-dbg',
        'gpu-try-mac-intel-dbg',
        'mac-jumbo-rel',
        'mac-rel',
        'WebKit Mac10.13 (retina)',  # copied from master.chromium.webkit
    ],
    'master.tryserver.blink': [
        # These have been migrated to LUCI.
        'linux-blink-rel',
        'mac10.10-blink-rel',
        'mac10.11-blink-rel',
        'mac10.12-blink-rel',
        'mac10.13-blink-rel',
        'mac10.13_retina-blink-rel',
        'win10-blink-rel',
        'win7-blink-rel',
    ],

    'master.client.nacl.toolchain': [
        # These have been migrated to LUCI.
        'linux-pnacl-x86_32',
        'linux-pnacl-x86_32-tests-mips',
        'linux-pnacl-x86_64',
        'linux64-toolchain_arm',
        'linux64-glibc',
        'win-pnacl-x86_32',
        'win7-glibc',
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


def copyAndFlattenSettings(waterfalls):
  # The "settings" dictionary per waterfall applies to all bots.
  # src_side_runtest_py in particular is flattened by the Chromium recipe into
  # all bots' definitions. This flattening must be done here as well in order to
  # catch all the same errors that the recipe does. It's possible that other
  # fields must be flattened in as well, but some are deliberately not required
  # to be the same among bots that a given trybot mirrors, like build_gs_bucket.
  waterfalls = copy.deepcopy(waterfalls)
  # Only insert this key if it's actually in the spec, to allow 'None', 'False',
  # and 'True' to show up in the destination bots' configurations.
  for waterfall in waterfalls.itervalues():
    if 'src_side_runtest_py' in waterfall.get('settings', {}):
      val = waterfall['settings']['src_side_runtest_py']
      for builder in waterfall['builders'].itervalues():
        builder['src_side_runtest_py'] = val
  return waterfalls


def getBotFromWaterfall(builders, mastername, botname):
  return builders.get(mastername, {}).get('builders', {}).get(botname)


def botExists(builders, waterfallname, trybotname, mastername, botname,
              undefined_bots):
  if getBotFromWaterfall(builders, mastername, botname):
    return True
  undefined_bots.add('%s on %s: %s on %s' % (trybotname, waterfallname, botname,
                                             mastername))
  return False


def checkConsistentGet(builders, trybot, key):
  # This logic must be kept in sync with _consistent_get in
  # recipe_modules/chromium_tests/bot_config_and_test_db.py. It's not feasible
  # to otherwise write a unit test for that code against all of the bots in
  # trybots.py.
  result = True
  first_bot = trybot['bot_ids'][0]
  val = getBotFromWaterfall(
    builders, first_bot['mastername'], first_bot['buildername']).get(key)
  for ii in xrange(1, len(trybot['bot_ids'])):
    bot = trybot['bot_ids'][ii]
    other_val = getBotFromWaterfall(
      builders, bot['mastername'], bot['buildername']).get(key)
    if val != other_val:
      print 'key "%s" differs in specification between %s:%s and %s:%s' % (
        key, first_bot['mastername'], first_bot['buildername'],
        bot['mastername'], bot['buildername'])
      print '  %s != %s' % (str(val), str(other_val))
      result = False
  return result


def checkTrybotConsistency(builders, trybot):
  result = True
  keys_to_query = set()
  # Look at all of the builders' keys, in order to ensure as best as possible
  # that they're all equal, without prior knowledge of which keys
  # recipe_modules/chromium_tests/api.py might look at.
  for bot in trybot['bot_ids']:
    # We only need to ensure consistency among the builders, not the testers.
    bot = getBotFromWaterfall(builders, bot['mastername'],
                              bot['buildername'])
    keys_to_query.update(bot.keys())
  for key in keys_to_query:
    if not checkConsistentGet(builders, trybot, key):
      result = False
  return result


def verifyTrybotConfigsAreConsistent(builders, trybots):
  # In chromium_tests/bot_config_and_test_db.py, BotConfig._consistent_get
  # asserts at runtime that when fetching any property from multiple mirrored
  # bots, the property must be identical for all of them.
  #
  # It's difficult to write a unit test for this code, because it's all within
  # the recipe boundary, and that essentially only executes at runtime. This
  # test acts as an integration test for this same logic, so that presubmit
  # checks can catch errors in trybots' specifications before they land and
  # break the trybot.
  return_value = True
  undefined_bots = set()

  builders = copyAndFlattenSettings(builders)

  # To keep things simple, first check for undefined bots, and then afterward
  # check all bots for consistency.
  for waterfall_name, waterfall in trybots.iteritems():
    for trybot_name, trybot in waterfall['builders'].iteritems():
      for trybot_id in trybot['bot_ids']:
        if not botExists(builders, waterfall_name, trybot_name,
                         trybot_id['mastername'], trybot_id['buildername'],
                         undefined_bots):
          return_value = False
        if 'tester' in trybot_id:
          if not botExists(builders, waterfall_name, trybot_name,
                           trybot_id['mastername'], trybot_id['tester'],
                           undefined_bots):
            return_value = False

  if undefined_bots:
    print 'The following bots referenced by trybots.py are not defined:'
    for bb in undefined_bots:
      print '  %s' % bb

  # If trybots reference nonexistent builders, the consistency checks will raise
  # an exception internally, but the misconfigured bots' names will be printed
  # first in order to give a hint about what needs to be fixed.
  for waterfall_name, waterfall in trybots.iteritems():
    for trybot_name, trybot in waterfall['builders'].iteritems():
      if not checkTrybotConsistency(builders, trybot):
        return_value = False

  return return_value


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
      other_recipe_builders = set(recipe_side_builders.keys()).difference(
          set(chromium_recipe_builders[master]))

      for fake in FAKE_BUILDERS.get(master, []):
        if fake in bogus_builders:
          bogus_builders.remove(fake)
          other_recipe_builders.remove(fake)

      if bogus_builders:
        exit_code = 1
        print 'The following builders from chromium recipe'
        print 'do not exist in master config for %s:' % master
        print '\n'.join('\t%s' % b for b in sorted(bogus_builders))

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

  if not verifyTrybotConfigsAreConsistent(chromium_BUILDERS,
                                          chromium_trybot_BUILDERS):
    # The function above prints out its own errors.
    exit_code = 1

  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
