# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class UrlApi(recipe_api.RecipeApi):
  def join(self, *parts):
    return '/'.join(str(x).strip('/') for x in parts)

  def fetch(self, url, step_name=None, attempts=None, **kwargs):
    if not step_name:
      step_name = 'fetch %s' % url
    args = [
        url,
        '--outfile', self.m.raw_io.output(),
    ]
    if attempts:
      args.extend(['--attempts', attempts])
    fetch_result = self.m.python(
        name=step_name,
        script=self.m.path['build'].join('scripts', 'tools', 'pycurl.py'),
        args=args,
        **kwargs)
    return fetch_result.raw_io.output
