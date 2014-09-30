# Copyright 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from master.factory import annotator_factory


AF = annotator_factory.AnnotatorFactory()


# Trigger that is fired when an official build passes.
smoke_test_trigger = Triggerable(
    name='smoke_test_trigger', builderNames=['Syzygy Official'])


# Windows binaries smoke-test builder for Syzygy.
smoke_test_builder = {
  'name': 'Syzygy Smoke Test',
  'factory': AF.BaseFactory(recipe='syzygy/smoke_test',
                            triggers=['smoke_test_trigger']),
  'auto_reboot': False,
  'category': 'official',
}


def Update(config, active_master, c):
  c['schedulers'].append(smoke_test_trigger)
  c['builders'].append(smoke_test_builder)
