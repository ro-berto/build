# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetFactoryProperties(api, build_properties):
  return {
      'checkout': 'git',
      'git_spec': {
          'url': 'http://github.com/toolkitchen/toolkit.git',
          'recursive': True,
      },
      'script': ['toolkit', 'build', 'gen_steps.py']
  }
