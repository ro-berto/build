# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU testers on the
# following waterfalls:
#   chromium.gpu
#   chromium.gpu.fyi
#   chromium.webkit
#   tryserver.chromium
# These testers are triggered by the builders on the same waterfall.

DEPS = [
  'buildbot',
  'gpu',
  'isolate',
  'path',
  'platform',
  'properties',
]

def GenSteps(api):
  api.gpu.setup()
  yield api.buildbot.prep()

  # When the tests are run via isolates -- which is the long-term goal for
  # all of the GPU bots -- a workspace checkout is no longer necessary.
  # Instead, the swarming_client tools are checked out separately. These
  # two modes are different enough that the recipe has to know whether
  # isolates are being used.
  #
  # Once isolates support the component build, the remaining testers will
  # be switched to use them, and this conditional logic will be removed.
  #
  # For local testing, if not using isolates: pass 'skip_checkout=True' to
  # run_recipe to skip the checkout step. A full checkout via the recipe
  # must have been done previously.

  if api.gpu.using_isolates:
    yield api.isolate.checkout_swarming_client()
  else:
    if not api.properties.get('skip_checkout', False):
      yield api.gpu.checkout_steps()
    else:
      api.path.set_dynamic_path('checkout', api.path.slave_build('src'))
    yield api.gpu.download_steps()
  yield api.gpu.test_steps()

def GenTests(api):
  # The majority of the tests are in the build_and_test recipe.

  # Keep the additional properties in sync with the build_and_upload
  # recipe in order to catch regressions.
  for plat in ['win', 'mac', 'linux']:
    for flavor in ['Debug', 'Release']:
      flavor_lower = flavor.lower()
      yield (
        api.test('%s_%s' % (plat, flavor_lower)) +
        api.properties.scheduled(
          build_config=flavor,
          mastername='chromium.gpu.testing',
          buildername='%s %s tester' % (plat, flavor_lower),
          buildnumber=776,
          parent_buildername='%s %s builder' % (plat, flavor_lower),
          parent_buildnumber=571,
          parent_got_revision=160000,
          parent_got_webkit_revision=10000,
          parent_got_swarming_client_revision='feaaabcdef',
          # These would ordinarily be generated by the builder and passed
          # via build properties to the tester.
          swarm_hashes=api.gpu.dummy_swarm_hashes,
        ) +
        api.platform.name(plat)
      )

  # Test one Release and Debug configuration skipping the checkout.
  for flavor in ['Debug', 'Release']:
    flavor_lower = flavor.lower()
    yield (
      api.test('linux_%s_skip_checkout' % flavor_lower) +
      api.properties.scheduled(
        build_config=flavor,
        skip_checkout=True,
        mastername='chromium.gpu.testing',
        buildername='linux %s skip checkout tester' % flavor_lower,
        buildnumber=777,
        parent_buildername='linux %s builder' % flavor_lower,
        parent_buildnumber=572,
        parent_got_revision=160001,
        parent_got_webkit_revision=10001,
        parent_got_swarming_client_revision='feaaabcdef',
        # These would ordinarily be generated by the builder and passed via
        # build properties to the tester.
        swarm_hashes=api.gpu.dummy_swarm_hashes,
      ) +
      api.platform.name('linux')
    )
