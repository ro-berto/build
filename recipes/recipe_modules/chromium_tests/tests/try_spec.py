# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import try_spec as try_spec_module

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  api.assertions.maxDiff = None

  # TryMirror creation *********************************************************

  # Creation of a TryMirror without tester
  mirror = try_spec_module.TryMirror.create('fake-group', 'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_group('fake-group', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # Creation of a TryMirror with tester
  mirror = try_spec_module.TryMirror.create('fake-group', 'fake-builder',
                                            'fake-tester', 'fake-tester-group')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_group('fake-group', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_group('fake-tester-group', 'fake-tester'))

  # Creation of a TryMirror with tester without tester group
  mirror = try_spec_module.TryMirror.create('fake-group', 'fake-builder',
                                            'fake-tester')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_group('fake-group', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_group('fake-group', 'fake-tester'))

  # Creation of a TryMirror with builder for tester
  mirror = try_spec_module.TryMirror.create('fake-group', 'fake-builder',
                                            'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_group('fake-group', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # TryMirror normalization ****************************************************

  # Normalization of a TryMirror
  mirror = try_spec_module.TryMirror.create('fake-group', 'fake-builder')
  mirror2 = try_spec_module.TryMirror.normalize(mirror)
  api.assertions.assertIs(mirror2, mirror)

  # Normalization of a BuilderId
  bot_id = chromium.BuilderId.create_for_group('fake-group', 'fake-builder')
  mirror = try_spec_module.TryMirror.normalize(bot_id)
  api.assertions.assertEqual(
      mirror, try_spec_module.TryMirror.create('fake-group', 'fake-builder'))

  # Normalization of a dictionary
  d = {
      'builder_group': 'fake-group',
      'buildername': 'fake-builder',
      'tester': 'fake-tester',
      'tester_group': 'fake-tester-group',
  }
  mirror = try_spec_module.TryMirror.normalize(d)
  api.assertions.assertEqual(
      mirror,
      try_spec_module.TryMirror.create('fake-group', 'fake-builder',
                                       'fake-tester', 'fake-tester-group'))

  # TrySpec normalization ******************************************************

  # Normalization of a TrySpec
  try_spec = try_spec_module.TrySpec.create(mirrors=[{
      'builder_group': 'fake-group',
      'buildername': 'fake-builder',
  }])
  try_spec2 = try_spec_module.TrySpec.normalize(try_spec)
  api.assertions.assertIs(try_spec2, try_spec)

  # Normalization of a dictionary
  d = {
      'mirrors': [{
          'builder_group': 'fake-group',
          'buildername': 'fake-builder',
      }],
  }
  try_spec = try_spec_module.TrySpec.normalize(d)
  api.assertions.assertEqual(
      try_spec,
      try_spec_module.TrySpec.create(mirrors=[{
          'builder_group': 'fake-group',
          'buildername': 'fake-builder',
      }]))

  # TryDatabase validation *****************************************************
  d = {
      'fake-try-group': {
          'fake-try-builder': {
              'mirrors': [{
                  'builder_group': 'fake-group',
                  'buildername': 'fake-builder',
              },],
              'foo': 'bar'
          },
      },
  }
  builder_id = chromium.BuilderId.create_for_group('fake-try-group',
                                                   'fake-try-builder')
  with api.assertions.assertRaises(TypeError) as caught:
    try_spec_module.TryDatabase.create(d)
  api.assertions.assertEqual(
      caught.exception.message,
      "__init__() got an unexpected keyword argument 'foo'"
      ' while creating try spec for builder {!r}'.format(builder_id))

  # TryDatabase mapping interface **********************************************
  db = try_spec_module.TryDatabase.create({
      'fake-try-group-1': {
          'fake-try-builder-1': {
              'mirrors': [{
                  'builder_group': 'group-1',
                  'buildername': 'builder-1',
              }],
          },
      },
      'fake-try-group-2': {
          'fake-try-builder-2': {
              'mirrors': [{
                  'builder_group': 'group-2',
                  'buildername': 'builder-2',
              }],
          },
      },
  })

  try_key_1 = chromium.BuilderId.create_for_group('fake-try-group-1',
                                                  'fake-try-builder-1')
  try_key_2 = chromium.BuilderId.create_for_group('fake-try-group-2',
                                                  'fake-try-builder-2')

  api.assertions.assertEqual(set(db.keys()), {try_key_1, try_key_2})
  api.assertions.assertEqual(
      db[try_key_1],
      try_spec_module.TrySpec.create(mirrors=[
          try_spec_module.TryMirror.create(
              builder_group='group-1', buildername='builder-1')
      ]))
  api.assertions.assertEqual(
      db[try_key_2],
      try_spec_module.TrySpec.create(mirrors=[
          try_spec_module.TryMirror.create(
              builder_group='group-2', buildername='builder-2')
      ]))

  # TryDatabase normalization **************************************************

  # Normalization of a TryDatabase
  try_db = try_spec_module.TryDatabase.create({
      'fake-try-group': {
          'fake-try-builder': {
              'mirrors': [{
                  'builder_group': 'group',
                  'buildername': 'builder',
              }],
          },
      },
  })
  try_db2 = try_spec_module.TryDatabase.normalize(try_db)
  api.assertions.assertIs(try_db2, try_db)

  # Normalization of a dictionary
  d = {
      'fake-try-group': {
          'fake-try-builder': {
              'mirrors': [{
                  'builder_group': 'group',
                  'buildername': 'builder',
              }],
          },
      },
  }
  try_db = try_spec_module.TryDatabase.normalize(d)
  api.assertions.assertEqual(try_db, try_spec_module.TryDatabase.create(d))


def GenTests(api):
  yield api.test(
      'full',
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
