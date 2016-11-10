# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Custom exceptions for bisect."""

class BisectException(Exception):
  pass

class InconclusiveBisectException(BisectException):
  """To be raised when a bisect cannot identify a culprit"""
  pass

class UntestableRevisionException(BisectException):
  """When a specific revision cannot be built or tested."""
  pass
