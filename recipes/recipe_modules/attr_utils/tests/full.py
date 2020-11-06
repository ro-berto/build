# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr

from recipe_engine import post_process
from recipe_engine.config_types import NamedBasePath, Path
from recipe_engine.types import FrozenDict
from recipe_engine.util import Placeholder

from RECIPE_MODULES.build.attr_utils import (FieldMapping, attrib, attrs,
                                             cached_property,
                                             command_args_attrib, enum_attrib,
                                             mapping_attrib, sequence_attrib)

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

  message_fragment = "No value provided for required attribute 'required'"
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

  # test None value for attribute with non-None default results in default
  x = AttribTest(required='required', default=None)
  api.assertions.assertEqual(x.default, 'default')

  # required after optional handling *******************************************
  @attr.s(frozen=True)
  class RequiredTest(object):
    optional = attrib(str, default=None)
    required = attrib(str)

  with api.assertions.assertRaises(TypeError) as caught:
    RequiredTest()

  message = "No value provided for required attribute 'required'"
  api.assertions.assertEqual(caught.exception.message, message)

  # test successful validation
  x = RequiredTest(required='required')
  api.assertions.assertEqual(x.required, 'required')

  # enum_attrib ****************************************************************
  @attr.s(frozen=True)
  class EnumAttribTest(object):
    value = enum_attrib([1, 2, 3])

  # test validation of attribute value
  with api.assertions.assertRaises(ValueError) as caught:
    EnumAttribTest(value=4)
  message = "'value' must be in (1, 2, 3) (got 4)"
  api.assertions.assertEqual(caught.exception.message, message)

  # test successful validation
  x = EnumAttribTest(value=1)
  api.assertions.assertEqual(x.value, 1)

  # sequence_attrib ************************************************************
  @attr.s(frozen=True)
  class SequenceAttribTest(object):
    value = sequence_attrib()
    typed = sequence_attrib(str, default=None)

  # test validation of attribute value
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest(value=1)
  message = "'value' must be <type 'tuple'> (got 1 that is a <type 'int'>)."
  api.assertions.assertEqual(caught.exception.message, message)

  # test validation of element types
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest(value=[1, 2, 3], typed=[4, 5, 6])
  message = ("'typed' members must be <type 'basestring'> "
             "(got 4 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test successful validation
  x = SequenceAttribTest(value=[1, 2, 3], typed=['4', '5', '6'])
  api.assertions.assertEqual(x.value, (1, 2, 3))
  api.assertions.assertEqual(x.typed, ('4', '5', '6'))

  # command_args ***************************************************************
  @attr.s(frozen=True)
  class CommandArgsAttribTest(object):
    args = command_args_attrib()

  # test validation of element types
  with api.assertions.assertRaises(TypeError) as caught:
    CommandArgsAttribTest([[]])

  api.assertions.assertEqual(
      caught.exception.message,
      ("'args' members must be (<type 'int'>, <type 'long'>, "
       "<type 'basestring'>, <class 'recipe_engine.config_types.Path'>, "
       "<class 'recipe_engine.util.Placeholder'>) "
       "(got [] that is a <type 'list'>)."))

  # test that all valid argument types can be passed
  args = [
      0, 1L, 'x',
      Path(NamedBasePath('fake-base-path')),
      Placeholder('fake-placeholder')
  ]
  x = CommandArgsAttribTest(args)
  api.assertions.assertEqual(x.args, tuple(args))

  # mapping_attrib *************************************************************
  @attr.s(frozen=True)
  class MappingAttribTest(object):
    value = mapping_attrib()
    typed = mapping_attrib(str, int, default=None)

  # test validation of attribute value
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(value=1)
  message = ("'value' must be <class 'recipe_engine.types.FrozenDict'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test validation of types of mapping keys
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(value={1: 1, 2: 2, 3: 3}, typed={1: 1})
  message = ("'typed' keys must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test validation of types of mapping values
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(value={1: 1, 2: 2, 3: 3}, typed={'a': 'a'})
  message = (
      "'typed' values must be <type 'int'> (got 'a' that is a <type 'str'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  # test successful validation
  x = MappingAttribTest(
      value={
          1: 1,
          2: 2,
          3: 3,
      },
      typed={
          '4': 4,
          '5': 5,
          '6': 6,
      },
  )
  api.assertions.assertEqual(x.value, FrozenDict({1: 1, 2: 2, 3: 3}))
  api.assertions.assertEqual(x.typed, FrozenDict({'4': 4, '5': 5, '6': 6}))

  # attrs **********************************************************************
  with api.assertions.assertRaises(TypeError) as caught:

    @attrs()
    class AttrsTest(object):
      x = attrib(str, default=1)

  message = ("default for 'x' must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(caught.exception.message, message)

  @attrs()
  class AttrsTest(object):
    x = attrib(str, default='bar')

  x = AttrsTest()
  api.assertions.assertEqual(x.x, 'bar')

  # string handling ************************************************************
  @attrs()
  class StrTest(object):
    x = attrib(str)

  # make sure a unicode can be asigned
  x = StrTest(x=u'foo')
  api.assertions.assertEqual(x.x, u'foo')

  # FieldMapping ***************************************************************
  @attrs()
  class FieldMappingTest(FieldMapping):
    x = attrib(str, default=None)
    y = attrib(str, default=None)

  x = FieldMappingTest()
  with api.assertions.assertRaises(KeyError):
    _ = x['x']
  api.assertions.assertEqual(dict(x), {})

  x = FieldMappingTest(x='foo', y='bar')
  api.assertions.assertEqual(x['x'], 'foo')
  api.assertions.assertEqual(dict(x), {'x': 'foo', 'y': 'bar'})

  # cached_property ************************************************************
  calls = []

  @attrs()
  class CachedPropertyTest(object):
    x = attrib(str)

    @cached_property
    def y(self):
      calls.append(1)
      return self.x.upper()

  x = CachedPropertyTest('foo')
  api.assertions.assertEqual(len(calls), 0)

  api.assertions.assertEqual(x.y, 'FOO')
  api.assertions.assertEqual(len(calls), 1)

  api.assertions.assertEqual(x.y, 'FOO')
  api.assertions.assertEqual(len(calls), 1)

  with api.assertions.assertRaises(AttributeError):
    x.y = 'bar'


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
