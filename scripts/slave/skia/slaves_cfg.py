# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Utilities for working with slaves.cfg files."""


import os


def _slaves_cfg_path(master_name):
  def _make_path(master_name, build_dir):
    return os.path.abspath(os.path.join(
        os.path.abspath(os.path.dirname(__file__)), os.pardir, os.pardir,
        os.pardir, os.pardir, build_dir, 'masters',
        'master.' + master_name, 'slaves.cfg'))
  path = _make_path(master_name, 'build')
  if os.path.isfile(path):
    return path
  path = _make_path(master_name, 'build_internal')
  if os.path.isfile(path):
    return path
  return None


def get(master_name):
  """Return a dictionary of the buildslaves for the given master.

  Keys are slavenames and values are the unmodified slave dicts from the
  slaves.cfg file for the given master.
  """
  variables = {}
  execfile(_slaves_cfg_path(master_name), variables)
  slaves_cfg = {}
  for slave_dict in variables['slaves']:
    slaves_cfg[slave_dict['hostname']] = slave_dict
  return slaves_cfg

