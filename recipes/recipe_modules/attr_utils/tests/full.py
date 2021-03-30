# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr

from recipe_engine import post_process
from recipe_engine.config_types import NamedBasePath, Path
from recipe_engine.types import FrozenDict
from recipe_engine.util import Placeholder

from RECIPE_MODULES.build.attr_utils import (FieldMapping, attrib, attrs,
                                             cached_property, callable_attrib,
                                             command_args_attrib, enum_attrib,
                                             mapping, mapping_attrib,
                                             sequence_attrib)

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # attrib *********************************************************************
  with api.assertions.assertRaises(TypeError) as caught:
    attrib(1)
  message = ('constraint must be one of a type, a tuple of types '
             'or an AttributeConstraint, got 1')
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(TypeError) as caught:
    attrib((str, 1, 'x'))
  message = "All members of constraint must be types, got [1, 'x']"
  api.assertions.assertEqual(str(caught.exception), message)

  @attr.s(frozen=True)
  class AttribTest(object):
    required = attrib(str)
    optional = attrib(str, default=None)
    default = attrib(str, default='default')
    multi_typed = attrib((str, int), default=None)

  # test requires arguments for attributes with no defaults
  with api.assertions.assertRaises(TypeError) as caught:
    AttribTest()

  message_fragment = "No value provided for required attribute 'required'"
  api.assertions.assertIn(message_fragment, str(caught.exception))

  # test validation of attribute type
  with api.assertions.assertRaises(TypeError) as caught:
    AttribTest(required=1)
  message = (
      "'required' must be <type 'basestring'> (got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(str(caught.exception), message)

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
  api.assertions.assertEqual(str(caught.exception), message)

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
  api.assertions.assertEqual(str(caught.exception), message)

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
  api.assertions.assertEqual(str(caught.exception), message)

  # test validation of element types
  with api.assertions.assertRaises(TypeError) as caught:
    SequenceAttribTest(value=[1, 2, 3], typed=[4, 5, 6])
  message = ("members of 'typed' must be <type 'basestring'> "
             "(got 4 that is a <type 'int'>).")
  api.assertions.assertEqual(str(caught.exception), message)

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
      str(caught.exception),
      ("members of 'args' must be one of (<type 'int'>, <type 'long'>, "
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
  api.assertions.assertEqual(str(caught.exception), message)

  # test validation of types of mapping keys
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(value={1: 1, 2: 2, 3: 3}, typed={1: 1})
  message = ("keys of 'typed' must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(str(caught.exception), message)

  # test validation of types of mapping values
  with api.assertions.assertRaises(TypeError) as caught:
    MappingAttribTest(value={1: 1, 2: 2, 3: 3}, typed={'a': 'a'})
  message = ("values of 'typed' must be <type 'int'> "
             "(got 'a' that is a <type 'str'>).")
  api.assertions.assertEqual(str(caught.exception), message)

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

  # mapping ********************************************************************
  with api.assertions.assertRaises(TypeError) as caught:
    mapping[str, 1]  # pylint: disable=pointless-statement

  message = ('value_constraint must be one of a type, a tuple of types, '
             'an AttributeConstraint or Ellipsis, got 1')
  api.assertions.assertEqual(str(caught.exception), message)

  @attr.s(frozen=True)
  class MappingTest(object):
    typed = attrib(mapping[str, int])
    key_typed = attrib(mapping[str, ...])
    value_typed = attrib(mapping[..., int])

  x = MappingTest(
      typed={
          '1': 1,
          '2': 2
      },
      key_typed={
          '3': 3,
          '4': '4'
      },
      value_typed={
          '5': 5,
          6: 6
      },
  )
  api.assertions.assertEqual(x.typed, FrozenDict({'1': 1, '2': 2}))
  api.assertions.assertEqual(x.key_typed, FrozenDict({'3': 3, '4': '4'}))
  api.assertions.assertEqual(x.value_typed, FrozenDict({'5': 5, 6: 6}))

  # callable_attrib ************************************************************
  def test_callback():
    print 'foo'  # pragma: no cover

  @attr.s(frozen=True)
  class CallableAttribTest(object):
    callback = callable_attrib()

  # test validation of attribute value
  with api.assertions.assertRaises(TypeError) as caught:
    CallableAttribTest(callback='x')
  message = "'callback' must be callable (got 'x' that is a <type 'str'>)."
  api.assertions.assertEqual(str(caught.exception), message)

  # test successful validation
  x = CallableAttribTest(callback=test_callback)
  api.assertions.assertEqual(x.callback, test_callback)

  # attrs **********************************************************************
  with api.assertions.assertRaises(TypeError) as caught:

    @attrs()
    class AttrsTest(object):
      x = attrib(str, default=1)

  message = ("default for 'x' must be <type 'basestring'> "
             "(got 1 that is a <type 'int'>).")
  api.assertions.assertEqual(str(caught.exception), message)

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

    @classmethod
    def create(cls, **kwargs):
      return cls(**kwargs)

  # Test that the getter is executed only once
  x = CachedPropertyTest('foo')
  api.assertions.assertEqual(len(calls), 0)

  api.assertions.assertEqual(x.y, 'FOO')
  api.assertions.assertEqual(len(calls), 1)

  api.assertions.assertEqual(x.y, 'FOO')
  api.assertions.assertEqual(len(calls), 1)

  # Test that the property cannot be set
  with api.assertions.assertRaises(AttributeError):
    x.y = 'bar'

  # Test that the inheritance hierarchy is not affected by attrs/cached_property
  @attrs()
  class InheritedCachedPropertyTest(CachedPropertyTest):
    z = attrib(str)

    @cached_property
    def w(self):
      return self.z.upper()  # pragma: no cover

    @classmethod
    def create(cls, **kwargs):
      return super(InheritedCachedPropertyTest, cls).create(x='foo', **kwargs)

  # If attrs uses inheritance to manage cached properties, then the
  # class hierarchy will be:
  # * attrs-created InheritedCachedPropertyTest
  # * InheritedCachedPropertyTest
  # * attrs-created CachedPropertyTest
  # * CachedPropertyTest
  # This causes InheritedCachedPropertyTest.create to be called twice, resulting
  # in a TypeError due to multiple values for keyword argument 'x'
  x = InheritedCachedPropertyTest.create(z='bar')
  api.assertions.assertEqual(x.x, 'foo')


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
