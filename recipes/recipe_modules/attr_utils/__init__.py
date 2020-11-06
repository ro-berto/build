# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utilities for declaring immutable attr types.

This module provides `attrs` as a replacement for `attr.s` that has the
following differences in behavior.
* The attribute default values are validated when the class is defined,
  rather than validation errors occurring when attempting to create on
  object that uses the defaults.
* Classes are created frozen, which prevents changing attribute values.
* Classes are created slotted by default, which prevents being able to
  assign to undeclared attributes.
* A more helpful exception message is provided when required attributes
  are not initialized.
* Parentheses must be used in the decorator even if no arguments are
  specified.

It provides the following functions for defining attribute values on a
class:
* `attrib` - An attribute with an enforced type.
* `enum_attrib` - An attribute that takes on a fixed set of values.
* `sequence_attrib` - An attribute that takes a sequence of values,
  optionally enforcing the type of elements of the sequence. The value
  is converted to a tuple.
* `command_args_attrib` - An attribute that takes a sequence of values,
  enforcing that all values are of a type that can be passed to the step
  API. The value is converted to a `tuple`.
* `mapping_attrib` - An attribute that takes a mapping of keys to
  values, optionally enforcing the type of keys and/or values. The value
  is converted to a `FrozenDict`.

All of the functions for defining attributes accept a `default` argument
that has the same behavior:
* If `default` is not specified, the attribute is required: a value must
  be provided for the attribute when creating an object. In contrast to
  `attr.ib`, a required attribute can appear after an optional attribute
  or in a class that has a base with an optional attribute; the ordering
  of the arguments in `__init__` is not adjusted to account for this, so
  it may be necessary to specify it as a keyword argument if values are
  not being provided for all preceding optional attributes.
* If `default` is `None`, the attribute is optional: a value does not
  need to be provided for the attribute when creating an object. `None`
  is an acceptable value in addition to any other values allowed by the
  attribute and will be the default value.
* If `default` is not `None`, the attribute is optional: a value does
  not need to be provided for the attribute when creating an object.
  Values for the attribute will always conform to the definition; the
  attribute's default value will be used if provided the value `None`.

The following additional utilities are provided:
* `cached_property` - Like property, but will only be executed once.
* `FieldMapping` - Mixin to provide dict-like access to a class defined
  with `attrs`.
"""

import collections
import sys

import attr
from attr import converters, validators
import six

from recipe_engine.config_types import Path
from recipe_engine.types import FrozenDict, freeze
from recipe_engine.util import Placeholder

_NOTHING = object()

_SPECIAL_DEFAULTS = (None, _NOTHING)


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
  elif default is _NOTHING:
    wrapped_validator = validator or (lambda o, a, v: None)

    def validator(obj, attribute, value):
      if value is _NOTHING:
        raise TypeError(
            "No value provided for required attribute '{name}'".format(
                name=attribute.name))
      wrapped_validator(obj, attribute, value)

  else:
    wrapped_converter = converter or (lambda x: x)

    def converter(x):
      return wrapped_converter(converters.default_if_none(default)(x))

  return attr.ib(default=default, validator=validator, converter=converter)


def attrib(type_, default=_NOTHING):
  """Declare an immutable scalar attribute.

  Arguments:
    * type_ - The type of the attribute. Attempting to assign a value
      that is not an instance of type_ will fail (except None if default
      is None).
    * default - The default value of the attribute. See module
      documentation for description of the default behavior.
  """
  assert type_ is not None
  validator = _instance_of(type_)
  return _attrib(default, validator)


def enum_attrib(values, default=_NOTHING):
  """Declare an immutable attribute that can take one of a fixed set of
  values.

  Arguments:
    * values - A container containing the allowed values of the
      attributes. Attempting to assign a value that is not in values
      will fail (except None if default is None).
    * default - The default value of the attribute. See module
      documentation for description of the default behavior.
  """
  values = tuple(values)
  validator = validators.in_(values)
  return _attrib(default, validator)


def _null_validator(obj, attribute, value):
  pass


def sequence_attrib(member_type=None, default=_NOTHING):
  """Declare an immutable attribute containing a sequence of values.

  The value will be converted to a tuple. Attempting to assign a value
  that is not iterable will fail (except None if default is None).

  Arguments:
    * member_type - The type of all contained elements of the attribute.
      If provided, attempting to assign a value with elements that are
      not instances of member_type will fail.
    * default - The default value of the attribute. See module
      documentation for description of the default behavior.
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


def command_args_attrib(default=_NOTHING):
  """Declare an immutable attribute containing a sequence of arguments.

  The value will be converted to a tuple. Attempting to assign a value
  that is not iterable will fail (except None if default is None). The
  allowable values for elements of the iterable are the same as for the
  command line for a call to the step api.

  Arguments:
    * default - The default value of the attribute. See module
      documentation for description of the default behavior.
  """
  # The set of allowed types should be kept in sync with the types allowed by
  # _validate_cmd_list in
  # https://source.chromium.org/chromium/infra/infra/+/master:recipes-py/recipe_modules/step/api.py
  arg_types = (int, long, basestring, Path, Placeholder)
  return sequence_attrib(member_type=arg_types, default=default)


def mapping_attrib(key_type=None, value_type=None, default=_NOTHING):
  """Declare an immutable attribute containing a mapping of values.

  The value will be converted to a FrozenDict (with all contained keys
  and values being converted to an immutable type via freeze).
  Attempting to assign a value that cannot be used to initialize a dict
  will fail.

  Arguments:
    * key_type - The type of all contained keys of the attribute. If
      provided, attempting to assign a value with keys that are not
      instances of key_type will fail.
    * value_type - The type of all contained values of the attribute. If
      provided, attempting to assign a value with values that are not
      instances of value_type will fail.
    * default - The default value of the attribute. See module
      documentation for description of the default behavior.
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


@attr.s(frozen=True)
class _CachedProperty(object):
  """Descriptor for computing cached properties.

  See https://docs.python.org/3/howto/descriptor.html for a description
  of how descriptors in python work (information is applicable to
  python2).

  This class implements a non-data descriptor that when invoked for an
  instance will call its getter to get its value. It will then set the
  value on the instance's attribute. Because it is a non-data
  descriptor, instance attributes take precedence, so it will not be
  invoked again for the same instance.
  """
  getter = attr.ib()

  def __get__(self, obj, type_=None):
    # Used if someone attempts to access the class attribute
    if obj is None:  # pragma: no cover
      return self
    value = freeze(self.getter(obj))
    object.__setattr__(obj, self.getter.__name__, value)
    return value


def cached_property(getter):
  """Decorator for a method to create a property calculated only once.

  The decorator should be applied to a method on a class created using
  the attrs decorator. The method must take zero arguments. The first
  time the property is accessed, the getter will be called to compute
  the value. The value is frozen so that all data accessible via the
  containing class is immutable. All subsequent access of the property
  will get the same value.

  The decorator saves the cost of computing values that are expensive
  but also communicates to a reader of the code that for a given object
  the value of the property will not change.

  The value returned by the getter should not include any mutable state
  in its computation so that the value is dependent only on the value of
  the containing object. Otherwise, it becomes harder to reason about
  what the value will be/what the state was that led to the returned
  value.
  """
  return _CachedProperty(getter)


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
    cached_properties = None
    # If the class is using slots, then we need to take extra steps so that
    # there are slots for the cached properties
    if slots:
      cached_properties = {
          a for a, val in cls.__dict__.iteritems()
          if isinstance(val, _CachedProperty)
      }
    cls = attr.s(frozen=True, slots=slots, **kwargs)(cls)
    if slots and cached_properties:
      cls = type(cls.__name__, (cls,), {'slots': cached_properties})
    for a in attr.fields(cls):
      if a.validator is not None and a.default is not _NOTHING:
        try:
          a.validator(None, a, a.default)
        except Exception as e:
          message = 'default for ' + e.message
          raise type(e)(message), None, sys.exc_info()[2]

    return cls

  return inner


class FieldMapping(collections.Mapping):
  """Mixin to give attrs-types dict-like access.

  An attrs-type that inherits from this mixin can be treated like a
  mapping. The mapping will have keys for each of the attrs fields that
  are not None, with the key being the name of the field.

  This mixin eases transitioning away from raw-dicts to attrs types.
  """

  def __getitem__(self, key):
    if key in attr.fields_dict(type(self)):
      value = getattr(self, key)
      if value is not None:
        return value
    raise KeyError(key)

  def _non_none_attrs(self):
    for k, v in attr.asdict(self).iteritems():
      if v is not None:
        yield k

  def __iter__(self):
    return self._non_none_attrs()

  def __len__(self):
    return sum(1 for a in self._non_none_attrs())
