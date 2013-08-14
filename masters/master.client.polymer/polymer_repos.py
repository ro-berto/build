# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


REPOS = (
  'polymer',
  'platform',
  'CustomElements',
  'mdv',
  'PointerGestures',
  'PointerEvents',
  'ShadowDOM',
  'HTMLImports',
  'observe-js',
  'NodeBind',
  'TemplateInstances',
  'polymer-expressions',
)

REPO_DEPS = {
  'polymer': [
    'platform',
    'CustomElements',
    'mdv',
    'PointerGestures',
    'PointerEvents',
    'ShadowDOM',
    'HTMLImports',
    'observe-js',
    'NodeBind',
    'TemplateInstances',
    'polymer-expressions',
  ],
  'platform': [
    'CustomElements',
    'mdv',
    'PointerGestures',
    'PointerEvents',
    'ShadowDOM',
    'HTMLImports',
    'observe-js',
    'NodeBind',
    'TemplateInstances',
    'polymer-expressions',
  ],
  'mdv': [
    'observe-js',
    'NodeBind',
    'TemplateInstances',
    'polymer-expressions',
  ],
  'PointerGestures': [
    'PointerEvents',
  ],
}
