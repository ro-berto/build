# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr

from recipe_engine import post_process
from recipe_engine.types import FrozenDict

from RECIPE_MODULES.build.chromium_tests.attr_util import (
    attrib, attrs, enum_attrib, mapping_attrib, sequence_attrib)

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # attrib *********************************************************************
  @attr.s(frozen=True)
  class AttribTest(object):
    required = attrib(str)
    optional = attrib(str, default=None)
    default = attrib(str, default='default')

  # test requires arguments for attributes with no defaults
  with api.assertions.assertRaises(TypeError) as caught:
    AttribTest()
  message_fragment = '__init__() takes at least 2 arguments'
  api.assertions.assertIn(message_fragment, caught.exception.message)

  # test validation of attribute type
  with api.assertions.assertRaises(TypeError) as caught:
    AttribTest(required=1)
  message = (
      "'required' must be <type 'basestring'> (got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test value and defaults
  x = AttribTest(required='required')
  api.assertions.assertEqual(x.required, 'required')
  api.assertions.assertIsNone(x.optional)
  api.assertions.assertEqual(x.default, 'default')

  # test None value allowed for attribute with None default
  x = AttribTest(required='required', optional=None)
  api.assertions.assertIsNone(x.optional)

  # enum_attrib ****************************************************************
  @attr.s(frozen=True)
  class EnumAttribTest(object):
    required = enum_attrib([1, 2, 3])
    optional = enum_attrib([4, 5, 6], default=None)
    default = enum_attrib([7, 8, 9], default=7)

  # test requires arguments for attributes with no defaults
  with api.assertions.assertRaises(TypeError) as caught:
    EnumAttribTest()
  message_fragment = '__init__() takes at least 2 arguments'
  api.assertions.assertIn(message_fragment, caught.exception.message)

  # test validation of attribute value
  with api.assertions.assertRaises(ValueError) as caught:
    EnumAttribTest(required=4)
  message = "'required' must be in (1, 2, 3) (got 4)"
  api.assertions.assertEqual(caught.exception.message, message)

  # test value and defaults
  x = EnumAttribTest(required=1)
  api.assertions.assertEqual(x.required, 1)
  api.assertions.assertIsNone(x.optional)
  api.assertions.assertEqual(x.default, 7)

  # test None value allowed for attribute with None default
  x = EnumAttribTest(required=1, optional=None)
  api.assertions.assertIsNone(x.optional)

  # sequence_attrib ************************************************************
  @attr.s(frozen=True)
  class SequenceAttribTest(object):
    required = sequence_attrib()
    optional = sequence_attrib(default=None)
    default = sequence_attrib(default=[1, 2, 3])
    typed = sequence_attrib(str, default=None)

  # test requires arguments for attributes with no defaults
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest()
  message_fragment = '__init__() takes at least 2 arguments'
  api.assertions.assertIn(message_fragment, caught.exception.message)

  # test validation of attribute value
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest(required=1)
  message = (
      "'required' must be <type 'tuple'> (got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test value and defaults
  x = SequenceAttribTest(required=[1, 2, 3])
  api.assertions.assertEqual(x.required, (1, 2, 3))
  api.assertions.assertIsNone(x.optional)
  api.assertions.assertEqual(x.default, (1, 2, 3))

  # test None value allowed for attribute with None default
  x = SequenceAttribTest(required=[1, 2, 3], optional=None)
  api.assertions.assertIsNone(x.optional)

  # test validation of element types
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest(required=[1, 2, 3], typed=[4, 5, 6])
  message = ("'typed' members must be <type 'basestring'> "
             "(got 4 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # mapping_attrib *************************************************************
  @attr.s(frozen=True)
  class MappingAttribTest(object):
    required = mapping_attrib()
    optional = mapping_attrib(default=None)
    default = mapping_attrib(default={'a': 1, 'b': 2, 'c': 3})
    typed = mapping_attrib(str, int, default=None)

  # test requires arguments for attributes with no defaults
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest()
  message_fragment = '__init__() takes at least 2 arguments'
  api.assertions.assertIn(message_fragment, caught.exception.message)

  # test validation of attribute value
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(required=1)
  message = ("'required' must be <class 'recipe_engine.types.FrozenDict'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test value and defaults
  x = MappingAttribTest(required={1: 1, 2: 2, 3: 3})
  api.assertions.assertEqual(x.required, FrozenDict({1: 1, 2: 2, 3: 3}))
  api.assertions.assertIsNone(x.optional)
  api.assertions.assertEqual(x.default, FrozenDict({'a': 1, 'b': 2, 'c': 3}))

  # test None value allowed for attribute with None default
  x = MappingAttribTest(required={1: 1, 2: 2, 3: 3}, optional=None)
  api.assertions.assertIsNone(x.optional)

  # test validation of key types
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(required={1: 1, 2: 2, 3: 3}, typed={1: 1})
  message = ("'typed' keys must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test validation of value types
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(required={1: 1, 2: 2, 3: 3}, typed={'a': 'a'})
  message = (
      "'typed' values must be <type 'int'> (got 'a' that is a <type 'str'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # attrs **********************************************************************
  with api.assertions.assertRaises(TypeError) as caught:

    @attrs(frozen=True)
    class AttrsTest(object):
      x = attrib(str, default=1)

  message = ("default for 'x' must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  @attrs(frozen=True)
  class AttrsTest(object):
    x = attrib(str, default='bar')

  x = AttrsTest()
  api.assertions.assertEqual(x.x, 'bar')

  # string handling ************************************************************
  @attrs(frozen=True)
  class StrTest(object):
    x = attrib(str)

  # make sure a unicode can be asigned
  x = StrTest(x=u'foo')
  api.assertions.assertEqual(x.x, u'foo')


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
