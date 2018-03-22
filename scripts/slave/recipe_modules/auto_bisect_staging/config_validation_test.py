#!/usr/bin/env vpython
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import os
import sys
import unittest

import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.path.pardir))

from auto_bisect_staging import config_validation


class ConfigValidationTest(unittest.TestCase):  # pragma: no cover

  def test_validate_bisect_config_empty_config(self):
    config_validation.validate_bisect_config(config={}, schema={})

  def test_validate_bisect_config_with_missing_required_fails(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_bisect_config(
          config={},
          schema={'foo': {'type': 'integer', 'required': True}})

  def test_validate_bisect_config_with_one_field_passes(self):
    config_validation.validate_bisect_config(
        config={'foo': 123},
        schema={'foo': {'type': 'integer'}})

  def test_validate_optional_field_passes(self):
    config_validation.validate_bisect_config(
        config={},
        schema={'foo': {'type': 'integer'}})

  def test_validate_not_in_schema_passes(self):
    config_validation.validate_bisect_config(
        config={'foo': 'asdf'},
        schema={})

  def test_validate_bisect_config_larger_passing_example(self):
    schema = {
        'good_revision': {'type': 'revision'},
        'bad_revision': {'type': 'revision'},
        'str1': {'type': 'string'},
        'str2': {'type': 'string'},
        'int1': {'type': 'integer'},
        'int2': {'type': 'integer'},
        'bool1': {'type': 'boolean'},
        'bool2': {'type': 'boolean'},
    }
    config = {
        'good_revision': '0123456789abcdeabcde0123456789abcdeabcde',
        'bad_revision': 'bbbbbaaaaa0000011111bbbbbaaaaa0000011111',
        'str1': u'unicode-string',
        'str2': '',
        'int1': '12345',
        'int2': 12345,
        'bool1': True,
        'bool2': False,
    }
    config_validation.validate_bisect_config(config, schema)

  def test_validate_revisions_out_of_order_failure(self):
    schema = {
        'good_revision': {'type': 'revision'},
        'bad_revision': {'type': 'revision'},
    }
    config = {
        'good_revision': 200,
        'bad_revision': 100,
    }
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_bisect_config(config, schema)

  def test_validate_metric_with_return_code_not_required(self):
    schema = {
        'metric': {'type': 'string'},
        'bisect_mode': {'type': 'string'},
    }
    config = {
        'bisect_mode': 'return_code',
    }
    config_validation.validate_bisect_config(config, schema)

  def test_validate_metric_missing_failure(self):
    schema = {
        'metric': {'type': 'string'},
        'bisect_mode': {'type': 'string'},
    }
    config = {
        'bisect_mode': 'mean',
    }
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_bisect_config(config, schema)

  def test_validate_metric_format_failure(self):
    schema = {
        'metric': {'type': 'string'},
        'bisect_mode': {'type': 'string'},
    }
    config = {
        'bisect_mode': 'mean',
        'metric': 'a/b/c/d',
    }
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_bisect_config(config, schema)

  def test_validate_metric_format_pass(self):
    schema = {
        'metric': {'type': 'string'},
        'bisect_mode': {'type': 'string'},
    }
    config = {
        'bisect_mode': 'mean',
        'metric': 'a/b',
    }
    config_validation.validate_bisect_config(config, schema)

  def test_validate_string_failure(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': 12345},
          schema={'x': {'type': 'string'}},
          key='x')

  def test_validate_integer_failure(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': '123a'},
          schema={'x': {'type': 'integer'}},
          key='x')

  def test_validate_key_optional_value_is_none_passes(self):
    config_validation.validate_key(
        config={'x': None},
        schema={'x': {'type': 'integer'}},
        key='x')

  def test_validate_required_value_is_none_fails(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': None},
          schema={'x': {'type': 'integer', 'required': True}},
          key='x')

  def test_validate_revision_failure(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': 'abcdef'},
          schema={'x': {'type': 'revision'}},
          key='x')

  def test_validate_boolean_failure(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': 'true'},
          schema={'x': {'type': 'boolean'}},
          key='x')

  def test_validate_choice_failure(self):
    with self.assertRaises(config_validation.ValidationFail):
      config_validation.validate_key(
          config={'x': 3},
          schema={'x': {'type': 'int', 'choices': [1, 2]}},
          key='x')


if __name__ == '__main__':
  unittest.main()  # pragma: no cover
