# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.v8.v8_notifier import V8Notifier


def Update(config, active_master, c):
  c['status'].extend([
    V8Notifier(
        config,
        active_master,
        categories_steps={
          '': [
            'runhooks',
            'gn',
            'compile',
            'Check',
            'OptimizeForSize',
            'Mjsunit',
            'Webkit',
            'Benchmarks',
            'Test262',
            'Mozilla',
          ],
        },
        exclusions={
          'V8 Linux - mipsel - sim': [],
          'V8 Mips - big endian - nosnap - 1': [],
          'V8 Mips - big endian - nosnap - 2': [],
          'V8 Linux - ppc - sim': [],
          'V8 Linux - ppc64 - sim': [],
          'V8 Linux - s390 - sim': [],
          'V8 Linux - s390x - sim': [],
          'V8 Linux - x87 - nosnap - debug builder': [],
          'V8 Linux - x87 - nosnap - debug': [],
        },
        sendToInterestedUsers=True,
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={
          's390': ['runhooks', 'compile', 'Check'],
        },
        extraRecipients=[
          'joransiu@ca.ibm.com',
          'jyan@ca.ibm.com',
          'michael_dawson@ca.ibm.com',
        ],
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={
          'x87': ['runhooks', 'compile', 'Check'],
        },
        extraRecipients=[
          'weiliang.lin@intel.com',
          'chunyang.dai@intel.com',
          'zhengxing.li@intel.com',
        ],
    ),
  ])
