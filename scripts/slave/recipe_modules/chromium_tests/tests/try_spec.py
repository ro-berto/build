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

  # Ccreation of a TryMirror without tester
  mirror = try_spec_module.TryMirror.create('fake-master', 'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # Creation of a TryMirror with tester
  mirror = try_spec_module.TryMirror.create('fake-master', 'fake-builder',
                                            'fake-tester', 'fake-tester-master')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_master('fake-tester-master', 'fake-tester'))

  # Creation of a TryMirror with tester without tester mastername
  mirror = try_spec_module.TryMirror.create('fake-master', 'fake-builder',
                                            'fake-tester')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertEqual(
      mirror.tester_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-tester'))

  # Creation of a TryMirror with builder for tester
  mirror = try_spec_module.TryMirror.create('fake-master', 'fake-builder',
                                            'fake-builder')
  api.assertions.assertEqual(
      mirror.builder_id,
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'))
  api.assertions.assertIsNone(mirror.tester_id)

  # TryMirror normalization ****************************************************

  # Normalization of a TryMirror
  mirror = try_spec_module.TryMirror.create('fake-master', 'fake-builder')
  mirror2 = try_spec_module.TryMirror.normalize(mirror)
  api.assertions.assertIs(mirror2, mirror)

  # Normalization of a BuilderId
  bot_id = chromium.BuilderId.create_for_master('fake-master', 'fake-builder')
  mirror = try_spec_module.TryMirror.normalize(bot_id)
  api.assertions.assertEqual(
      mirror, try_spec_module.TryMirror.create('fake-master', 'fake-builder'))

  # Normalization of a dictionary
  d = {
      'mastername': 'fake-master',
      'buildername': 'fake-builder',
      'tester': 'fake-tester',
      'tester_mastername': 'fake-tester-master',
  }
  mirror = try_spec_module.TryMirror.normalize(d)
  api.assertions.assertEqual(
      mirror,
      try_spec_module.TryMirror.create('fake-master', 'fake-builder',
                                       'fake-tester', 'fake-tester-master'))

  # TrySpec normalization ******************************************************

  # Normalization of a TrySpec
  try_spec = try_spec_module.TrySpec.create(bot_ids=[{
      'mastername': 'fake-master',
      'buildername': 'fake-builder',
  }])
  try_spec2 = try_spec_module.TrySpec.normalize(try_spec)
  api.assertions.assertIs(try_spec2, try_spec)

  # Normalization of a dictionary
  d = {
      'bot_ids': [{
          'mastername': 'fake-master',
          'buildername': 'fake-builder',
      }],
  }
  try_spec = try_spec_module.TrySpec.normalize(d)
  api.assertions.assertEqual(
      try_spec,
      try_spec_module.TrySpec.create(bot_ids=[{
          'mastername': 'fake-master',
          'buildername': 'fake-builder',
      }]))

  # TryMasterSpec creation *****************************************************

  # Creation of a TryMasterSpec with input TrySpecs
  try_master_spec = try_spec_module.TryMasterSpec.create(
      builders={
          'fake-try-builder-1':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-1',
                                                   'fake-builder-1')
              ]),
          'fake-try-builder-2':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-2',
                                                   'fake-builder-2')
              ]),
      })
  api.assertions.assertEqual(
      try_master_spec.builders, {
          'fake-try-builder-1':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-1',
                                                   'fake-builder-1')
              ]),
          'fake-try-builder-2':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-2',
                                                   'fake-builder-2')
              ]),
      })

  # Creation of a TryMasterSpec with input dictionaries
  try_master_spec = try_spec_module.TryMasterSpec.create(
      builders={
          'fake-try-builder-1': {
              'bot_ids': [{
                  'mastername': 'fake-master-1',
                  'buildername': 'fake-builder-1',
              }],
          },
          'fake-try-builder-2': {
              'bot_ids': [{
                  'mastername': 'fake-master-2',
                  'buildername': 'fake-builder-2',
              }],
          },
      })
  api.assertions.assertEqual(
      try_master_spec.builders, {
          'fake-try-builder-1':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-1',
                                                   'fake-builder-1')
              ]),
          'fake-try-builder-2':
              try_spec_module.TrySpec.create(bot_ids=[
                  try_spec_module.TryMirror.create('fake-master-2',
                                                   'fake-builder-2')
              ]),
      })

  # TryMasterSpec normalization ************************************************

  # Normalization of a TryMasterSpec
  try_master_spec = try_spec_module.TryMasterSpec.create(
      builders={
          'fake-try-builder': {
              'bot_ids': [{
                  'mastername': 'fake-master',
                  'buildername': 'fake-builder',
              }],
          },
      })
  try_master_spec_2 = try_spec_module.TryMasterSpec.normalize(try_master_spec)
  api.assertions.assertIs(try_master_spec_2, try_master_spec)

  # TryDatabase validation *****************************************************
  d = {
      'fake-try-master': {
          'fake-try-builder': {},
      },
  }
  with api.assertions.assertRaises(TypeError) as caught:
    try_spec_module.TryDatabase.create(d)
  api.assertions.assertEqual(
      caught.exception.message,
      "create() got an unexpected keyword argument 'fake-try-builder'"
      " while creating try spec for master 'fake-try-master'")

  # TryDatabase mapping interface **********************************************
  db = try_spec_module.TryDatabase.create({
      'fake-try-master-1': {
          'builders': {
              'fake-try-builder-1': {
                  'bot_ids': [{
                      'mastername': 'master-1',
                      'buildername': 'builder-1',
                  }],
              },
          },
      },
      'fake-try-master-2': {
          'builders': {
              'fake-try-builder-2': {
                  'bot_ids': [{
                      'mastername': 'master-2',
                      'buildername': 'builder-2',
                  }],
              },
          },
      },
  })

  try_key_1 = chromium.BuilderId.create_for_master('fake-try-master-1',
                                                   'fake-try-builder-1')
  try_key_2 = chromium.BuilderId.create_for_master('fake-try-master-2',
                                                   'fake-try-builder-2')

  api.assertions.assertEqual(set(db.keys()), {try_key_1, try_key_2})
  api.assertions.assertEqual(
      db[try_key_1],
      try_spec_module.TrySpec.create(bot_ids=[
          try_spec_module.TryMirror.create(
              mastername='master-1', buildername='builder-1')
      ]))
  api.assertions.assertEqual(
      db[try_key_2],
      try_spec_module.TrySpec.create(bot_ids=[
          try_spec_module.TryMirror.create(
              mastername='master-2', buildername='builder-2')
      ]))

  # TryDatabase normalization **************************************************

  # Normalization of a TryDatabase
  try_db = try_spec_module.TryDatabase.create({
      'fake-try-master': {
          'builders': {
              'fake-try-builder': {
                  'bot_ids': [{
                      'mastername': 'master',
                      'buildername': 'builder',
                  }],
              },
          },
      },
  })
  try_db2 = try_spec_module.TryDatabase.normalize(try_db)
  api.assertions.assertIs(try_db2, try_db)

  # Normalization of a dictionary
  d = {
      'fake-try-master': {
          'builders': {
              'fake-try-builder': {
                  'bot_ids': [{
                      'mastername': 'master',
                      'buildername': 'builder',
                  }],
              },
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
