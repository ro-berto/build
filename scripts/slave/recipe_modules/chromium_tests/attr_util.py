# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utilities to simplify declaring attr-created types."""

import attr
from attr import converters, validators
import six
import sys

from recipe_engine import util
from recipe_engine.types import FrozenDict, freeze

_SPECIAL_DEFAULTS = (None, attr.NOTHING)


def _instance_of(type_, name_qualifier=''):
  """Replacement for validators.instance_of that allows for modifying the name.

  This allows for more helpful error messages when referring to subsidiary
  portions of values (e.g. keys of a dict).
  """
  if type_ == str:
    type_ = six.string_types[0]

  def inner(obj, attribute, value):
    if not isinstance(value, type_):
      raise TypeError("'{name}'{name_qualifier} must be {type!r} "
                      '(got {value!r} that is a {actual!r}).'.format(
                          name=attribute.name,
                          name_qualifier=name_qualifier,
                          type=type_,
                          actual=type(value),
                          value=value,
                      ))

  return inner


def _attrib(default, validator, converter=None):
  if default is None:
    validator = validators.optional(validator)
    if converter is not None:
      converter = converters.optional(converter)
  return attr.ib(default=default, validator=validator, converter=converter)


def attrib(type_, default=attr.NOTHING):
  """Declare an immutable scalar attribute.

  Arguments:
    type_ - The type of the attribute. Attempting to assign a value that is not
      an instance of type_ will fail (except None if default is None).
    default - The default value of the attribute. If no default is specified,
      the attribute must be explicitly initialized when creating an object. If
      default is None, None will also be considered an acceptable value for the
      attribute. Otherwise, default must be an instance of type_.
  """
  assert type_ is not None
  validator = _instance_of(type_)
  return _attrib(default, validator)


def enum_attrib(values, default=attr.NOTHING):
  """Declare an immutable attribute that can take one of a fixed set of values.

  Arguments:
    values - A container containing the allowed values of the attributes.
      Attempting to assign a value that is not in values will fail (except None
      if default is None).
    default - The default value of the attribute. If no default is specified,
      the attribute must be explicitly initialized when creating an object. If
      default is None, None will also be considered an acceptable value for the
      attribute. Otherwise, default must be a value in values.
  """
  values = tuple(values)
  validator = validators.in_(values)
  return _attrib(default, validator)


def _null_validator(obj, attribute, value):
  pass


def sequence_attrib(member_type=None, default=attr.NOTHING):
  """Declare an immutable attribute containing a sequence of values.

  The value will be converted to a tuple. Attempting to assign a value that is
  not iterable will fail (except None if default is None).

  Arguments:
    member_type - The type of all contained elements of the attribute. If
      provided, attempting to assign a value with elements that are not
      instances of member_type will fail.
    default - The default value of the attribute. If no default is specified,
      the attribute must be explicitly initialized when creating an object. If
      default is None, None will also be considered an acceptable value for the
      attribute. Otherwise, default must be an iterable value.
  """
  member_validator = _null_validator
  if member_type is not None:
    member_validator = _instance_of(member_type, ' members')
  validator = validators.deep_iterable(
      iterable_validator=_instance_of(tuple), member_validator=member_validator)

  def converter(value):
    try:
      return tuple(value)
    except TypeError:
      # Let the validator provide a more helpful exception message
      return value

  return _attrib(default, validator, converter)


def mapping_attrib(key_type=None, value_type=None, default=attr.NOTHING):
  """Declare an immutable attribute containing a mapping of values.

  The value will be converted to a FrozenDict (with all contained keys and
  values being converted to an immutable type via freeze). Attempting to assign
  a value that cannot be used to initialize a dict will fail.

  Arguments:
    key_type - The type of all contained keys of the attribute. If provided,
      attempting to assign a value with keys that are not instances of key_type
      will fail.
    value_type - The type of all contained values of the attribute. If provided,
      attempting to assign a value with values that are not instances of
      value_type will fail.
    default - The default value of the attribute. If no default is specified,
      the attribute must be explicitly initialized when creating an object. If
      default is None, None will also be considered an acceptable value for the
      attribute. Otherwise, default must be a value that can initialize a dict.
  """
  if default not in _SPECIAL_DEFAULTS:
    default = freeze(dict(default))
  key_validator = value_validator = _null_validator
  if key_type is not None:
    key_validator = _instance_of(key_type, ' keys')
  if value_type is not None:
    value_validator = _instance_of(value_type, ' values')
  validator = validators.deep_mapping(
      mapping_validator=_instance_of(FrozenDict),
      key_validator=key_validator,
      value_validator=value_validator)
  converter = freeze
  return _attrib(default, validator, converter)


def attrs(slots=True, **kwargs):
  """A replacement for attr.s that provides some additional conveniences.

  The following conveniences are provided:
  * The attribute default values are validated when the class is defined, rather
    than validation errors occurring when attempting to create on object that
    uses the defaults.
  * Classes are created frozen, which prevents changing attribute values.
  * Classes are created slotted by default, which prevents being able to assign
    to undeclared attributes.
  """

  def inner(cls):
    cls = attr.s(frozen=True, slots=slots, **kwargs)(cls)
    for a in attr.fields(cls):
      if a.validator is not None and a.default is not attr.NOTHING:
        try:
          a.validator(None, a, a.default)
        except Exception as e:
          message = 'default for ' + e.message
          raise type(e)(message), None, sys.exc_info()[2]
    return cls

  return inner
