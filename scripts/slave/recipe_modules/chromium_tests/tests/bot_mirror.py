# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # Test creation of a mirror without tester
  mirror = bot_spec.BotMirror.create('fake-master', 'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # Test creation of a mirror with tester
  mirror = bot_spec.BotMirror.create('fake-master', 'fake-builder',
                                     'fake-tester', 'fake-tester-master')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_master('fake-tester-master', 'fake-tester'))

  # Test creation of a mirror with tester without tester mastername
  mirror = bot_spec.BotMirror.create('fake-master', 'fake-builder',
                                     'fake-tester')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-tester'))

  # Test creation of a mirror with builder for tester
  mirror = bot_spec.BotMirror.create('fake-master', 'fake-builder',
                                     'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # Test normalization *********************************************************

  # Normalization of a BotMirror
  mirror = bot_spec.BotMirror.create('fake-master', 'fake-builder')
  mirror2 = bot_spec.BotMirror.normalize(mirror)
  api.assertions.assertIs(mirror2, mirror)

  # Normalization of a BuilderId
  bot_id = chromium.BuilderId.create_for_master('fake-master', 'fake-builder')
  mirror = bot_spec.BotMirror.normalize(bot_id)
  api.assertions.assertEqual(mirror.builder_id, bot_id)
  api.assertions.assertIsNone(mirror.tester_id)

  # Normalization of a dictionary
  d = {
      'mastername': 'fake-master',
      'buildername': 'fake-builder',
      'tester': 'fake-tester',
      'tester_mastername': 'fake-tester-master',
  }
  mirror = bot_spec.BotMirror.normalize(d)
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_master('fake-tester-master', 'fake-tester'))


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
