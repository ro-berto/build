# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import re

# Note: this module is tested by a unit test config_validation_test.py,
# rather than recipe simulation tests.

_BISECT_CONFIG_SCHEMA = {
    'command': {'type': 'string', 'required': True},
    'good_revision': {'type': 'revision', 'required': True},
    'bad_revision': {'type': 'revision', 'required': True},
    'bisect_bot': {'type': 'string'},
    'metric': {'type': 'string'},
    'bug_id': {'type': 'integer'},
    'repeat_count': {'type': 'integer'},
    'max_time_minutes': {'type': 'integer'},
    'bisect_mode': {'type': 'string',
                    'choices': ['mean', 'return_code', 'std_dev']},
    'gs_bucket': {'type': 'string'},
    'builder_host': {'type': 'string'},
    'builder_port': {'type': 'integer'},
    'test_type': {'type': 'string'},
    'improvement_direction': {'type': 'integer'},
    'recipe_tester_name': {'type': 'string'},
    'try_job_id': {'type': 'integer'},
}


def from_properties(bisect_config_dict):
  """Converts bisect config from a dict property value.

  Properties do not necessarily distinguish integers and floats, e.g.
  0 may turn into 0.0. This function fixes integer values.

  Does not validate the config.
  """
  bisect_config_dict = copy.deepcopy(bisect_config_dict)
  for p, schema in _BISECT_CONFIG_SCHEMA.iteritems():
    v = bisect_config_dict.get(p)
    if schema['type'] == 'integer' and isinstance(v, float):
      bisect_config_dict[p] = int(v)
  return bisect_config_dict


class ValidationFail(Exception):
  """An exception class that represents a failure to validate."""


def validate_bisect_config(config, schema=None):
  """Checks the correctness of the given bisect job config."""
  schema = _BISECT_CONFIG_SCHEMA if schema is None else schema
  for key in set(schema):
    validate_key(config, schema, key)

  if 'good_revision' in schema and 'bad_revision' in schema:
    _validate_revisions(config.get('good_revision'), config.get('bad_revision'))

  if 'bisect_mode' in schema and 'metric' in schema:
    _validate_metric(config.get('bisect_mode'), config.get('metric'))


def validate_key(config, schema, key):  # pragma: no cover
  """Checks the correctness of the given field in a config."""
  if schema[key].get('required') and config.get(key) is None:
    raise ValidationFail('Required key "%s" missing.' % key)
  if config.get(key) is None:
    return  # Optional field.
  value = config[key]
  field_type = schema[key].get('type')
  if field_type == 'string':
    _validate_string(value, key)
  elif field_type == 'integer':
    _validate_integer(value, key)
  elif field_type == 'revision':
    _validate_revision(value, key)
  elif field_type == 'boolean':
    _validate_boolean(value, key)
  if 'choices' in schema[key] and value not in schema[key]['choices']:
    _fail(value, key)


def _fail(value, key):
  raise ValidationFail('Invalid value %r for "%s".' % (value, key))


def _validate_string(value, key):  # pragma: no cover
  if not isinstance(value, basestring):
    _fail(value, key)


def _validate_revision(value, key):  # pragma: no cover
  s = str(value)
  if not (s.isdigit() or re.match('^[0-9A-Fa-f]{40}$', s)):
    _fail(value, key)


def _validate_integer(value, key):  # pragma: no cover
  try:
    int(value)
  except ValueError:
    _fail(value, key)


def _validate_boolean(value, key):  # pragma: no cover
  if value not in (True, False):
    _fail(value, key)


def _validate_revisions(good_revision, bad_revision):  # pragma: no cover
  try:
    earlier = int(good_revision)
    later = int(bad_revision)
  except ValueError:
    return  # The revisions could be sha1 hashes.
  if earlier >= later:
    raise ValidationFail('Order of good_revision (%d) and bad_revision(%d) '
                         'is reversed.' % (earlier, later))


def _validate_metric(bisect_mode, metric):  # pragma: no cover
  if bisect_mode not in ('mean', 'std_dev'):
    return
  if not (isinstance(metric, basestring) and ((metric.count('/') == 1) or
                                              (metric.count('/') == 2))):
    raise ValidationFail('Invalid value for "metric": %s' % metric)
