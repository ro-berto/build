# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.v8.v8_notifier import V8Notifier


V8_STEPS = [
  'update',
  'runhooks',
  'gn',
  'compile',
  'Presubmit',
  'Static-Initializers',
  'Check',
  'Unittests',
  'OptimizeForSize',
  'Mjsunit',
  'Webkit',
  'Benchmarks',
  'Test262',
  'Mozilla',
  'GCMole',
  'Fuzz',
  'Deopt Fuzz',
  'Simple Leak Check',
]


def Update(config, active_master, c):
  c['status'].extend([
    V8Notifier(
        config,
        active_master,
        categories_steps={'release': V8_STEPS},
        sendToInterestedUsers=True,
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={'roll': V8_STEPS},
        extraRecipients=[
          'machenbach@chromium.org',
          'hablich@chromium.org',
        ],
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={'mips': V8_STEPS},
        extraRecipients=[
          'akos.palfi@imgtec.com',
          'balazs.kilvady@imgtec.com',
          'dusan.milosavljevic@imgtec.com',
          'gergely.kis@imgtec.com',
          'paul.lind@imgtec.com',
        ],
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={'ppc': V8_STEPS},
        extraRecipients=[
          'mbrandy@us.ibm.com',
          'michael_dawson@ca.ibm.com',
        ],
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={
          'clusterfuzz': [
            'update',
            'runhooks',
            'gn',
            'compile',
            'gsutil upload',
            'ClusterFuzz Archive', # Legacy.
          ],
        },
        extraRecipients=[
          'machenbach@chromium.org',
          'v8-clusterfuzz-sheriff@chromium.org',
        ],
    ),
  ])

