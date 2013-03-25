#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for results_dashboard testcases."""

import json
import os
import shutil
import tempfile
import unittest
import urllib
import urllib2

import test_env  # pylint: disable=W0403,W0611

from slave import results_dashboard
from slave import slave_utils
from testing_support.super_mox import mox


class IsEncodedJson(mox.Comparator):
  def __init__(self, expected_json):
    self._json = expected_json

  def equals(self, rhs):
    rhs_json = urllib.unquote_plus(rhs.data.replace("data=", ""))
    return sorted(json.loads(self._json)) == sorted(json.loads(rhs_json))

  def __repr__(self):
    return "<Is Request JSON %s>" % self._json


class ResultsDashboardTest(unittest.TestCase):
  def setUp(self):
    super(ResultsDashboardTest, self).setUp()
    self.mox = mox.Mox()
    self.build_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.build_dir, results_dashboard.CACHE_DIR))
    self.cache_filename = os.path.join(self.build_dir,
                                       results_dashboard.CACHE_DIR,
                                       results_dashboard.CACHE_FILENAME)

  def tearDown(self):
    self.mox.UnsetStubs()
    shutil.rmtree(self.build_dir)

  def _SendResults(self, send_results_args, expected_new_json, errors):
    self.mox.UnsetStubs()  # Needed for multiple calls from same test.
    self.mox.StubOutWithMock(slave_utils, "GetActiveMaster")
    slave_utils.GetActiveMaster().AndReturn("ChromiumPerf")
    self.mox.StubOutWithMock(urllib2, "urlopen")
    for json_line, error in zip(expected_new_json, errors):
      if error:
        urllib2.urlopen(IsEncodedJson(json_line)).AndRaise(error)
      else:
        urllib2.urlopen(IsEncodedJson(json_line))
    self.mox.ReplayAll()
    send_results_args.append(self.build_dir)
    results_dashboard.SendResults(*send_results_args)
    self.mox.VerifyAll()

  def test_SingleLogLine(self):
    args = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_MultipleLogLines(self):
    args = [
        "bar-summary.dat", [
            '{"traces": {"baz": ["100.0", "5.0"]},'
            ' "rev": "12345", "webkit_rev": "6789"}',
            '{"traces": {"box": ["101.0", "4.0"]},'
            ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }}, {
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/box",
        "revision": "12345",
        "value": "101.0",
        "error": "4.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_ModifiedTraceNames(self):
    args = [
        "bar-summary.dat",
        ['{"traces": {"bar": ["100.0", "5.0"], "bar_ref": ["99.0", "2.0"],'
         ' "baz/y": ["101.0", "3.0"], "notchanged": ["102.0", "1.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }},{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/ref",
        "revision": "12345",
        "value": "99.0",
        "error": "2.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }}, {
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz_y",
        "revision": "12345",
        "value": "101.0",
        "error": "3.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }},{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/notchanged",
        "revision": "12345",
        "value": "102.0",
        "error": "1.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_ByUrlGraph(self):
    args = [
        "bar_by_url-summary.dat",
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_FailureRetried(self):
    args = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [urllib2.URLError("reason")]
    self._SendResults(args, expected_new_json, errors)
    args2 = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["101.0", "6.0"]},'
         ' "rev": "12346", "webkit_rev": "6790"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json.append(json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12346",
        "value": "101.0",
        "error": "6.0",
        "supplemental_columns": {
            "r_webkit_rev": "6790",
        }
    }]))
    errors = [None, None]
    self._SendResults(args2, expected_new_json, errors)

  def test_SuccessNotRetried(self):
    args = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)
    args2 = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["101.0", "6.0"]},'
         ' "rev": "12346", "webkit_rev": "6790"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json2 = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12346",
        "value": "101.0",
        "error": "6.0",
        "supplemental_columns": {
            "r_webkit_rev": "6790",
        }
    }])]
    errors = [None]
    self._SendResults(args2, expected_new_json2, errors)

  def test_FailureCached(self):
    args = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [urllib2.URLError("reason")]
    self._SendResults(args, expected_new_json, errors)
    cache_file = open(self.cache_filename, "rb")
    actual_cache = cache_file.read()
    cache_file.close()
    self.assertEqual(expected_new_json[0], actual_cache)

  def test_NoResendAfterMultipleErrors(self):
    previous_lines = "\n".join([
        json.dumps([{
            "master": "ChromiumPerf",
            "bot": "linux-release",
            "test": "foo/bar/baz",
            "revision": "12345",
            "value": "100.0",
            "error": "5.0",
            "supplemental_columns": {
                "r_webkit_rev": "6789",
            }}]),
        json.dumps([{
            "master": "ChromiumPerf",
            "bot": "linux-release",
            "test": "foo/bar/baz",
            "revision": "12346",
            "value": "101.0",
            "error": "5.0",
            "supplemental_columns": {
                "r_webkit_rev": "6789",
            }}]),
        json.dumps([{
            "master": "ChromiumPerf",
            "bot": "linux-release",
            "test": "foo/bar/baz",
            "revision": "12347",
            "value": "99.0",
            "error": "5.0",
            "supplemental_columns": {
                "r_webkit_rev": "6789",
            }}])
    ])
    cache_file = open(self.cache_filename, "wb")
    cache_file.write(previous_lines)
    cache_file.close()
    args = [
        "bar-summary.dat",
        ['{"traces": {"baz": ["102.0", "5.0"]},'
         ' "rev": "12348", "webkit_rev": "6789"}'],
        "linux-release",
        "foo",
        "https://chrome-perf.googleplex.com"]
    expected_new_json = [json.dumps([{
        "master": "ChromiumPerf",
        "bot": "linux-release",
        "test": "foo/bar/baz",
        "revision": "12345",
        "value": "100.0",
        "error": "5.0",
        "supplemental_columns": {
            "r_webkit_rev": "6789",
        }}])]
    errors = [urllib2.URLError("reason")]
    self._SendResults(args, expected_new_json, errors)
    cache_file = open(self.cache_filename, "rb")
    actual_cache_lines = cache_file.readlines()
    cache_file.close()
    self.assertEqual(4, len(actual_cache_lines))
    for line in previous_lines.split("\n") + expected_new_json:
      self.assertTrue(line + "\n" in actual_cache_lines)


if __name__ == '__main__':
  unittest.main()
