# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


REPOS = (
  'polymer-dev',
  'platform-dev',
  'CustomElements',
  'ShadowDOM',
  'HTMLImports',
  'observe-js',
  'NodeBind',
  'TemplateBinding',
  'polymer-expressions',
  'PointerGestures',
  'PointerEvents',
)

REPO_DEPS = {
  'polymer-dev': [
    'platform-dev',
    'CustomElements',
    'PointerGestures',
    'PointerEvents',
    'ShadowDOM',
    'HTMLImports',
    'observe-js',
    'NodeBind',
    'TemplateBinding',
    'polymer-expressions',
  ],
  'platform-dev': [
    'CustomElements',
    'PointerGestures',
    'PointerEvents',
    'ShadowDOM',
    'HTMLImports',
    'observe-js',
    'NodeBind',
    'TemplateBinding',
    'polymer-expressions',
  ],
  'NodeBind': [
    'observe-js'
  ],
  'TemplateBinding': [
    'observe-js',
    'NodeBind',
  ],
  'polymer-expressions': [
    'observe-js',
    'NodeBind',
    'TemplateBinding',
  ],
  'PointerGestures': [
    'PointerEvents',
  ],
}
