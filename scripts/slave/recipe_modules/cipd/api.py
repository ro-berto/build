# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class CIPDApi(recipe_api.RecipeApi):
  """CIPDApi provides support for CIPD."""
  def __init__(self, *args, **kwargs):
    super(CIPDApi, self).__init__(*args, **kwargs)
    self.bin_path = None

  def install_client(self, step_name):
    bin_path = self.m.path['slave_build'].join('cipd')
    script_input = {
      'platform': self.platform_tag(),
      'bin_path': bin_path,
    }

    self.m.python(
        name=step_name,
        script=self.resource('bootstrap.py'),
        stdin=self.m.json.input(script_input))

    # TODO(seanmccullough): clean up older CIPD installations.

  def platform_tag(self):
    return "%s-%s" % (
        self.m.platform.name.replace('win', 'windows'),
        {
            32: '386',
            64: 'amd64',
        }[self.m.platform.bits],
    )

  def ensure_installed(self, root, pkgs):
    pkg_list = []
    for pkg_name in sorted(pkgs):
      pkg_spec = pkgs[pkg_name]
      pkg_list.append("%s %s" % (pkg_name, pkg_spec['version']))

    list_data = self.m.raw_io.input("\n".join(pkg_list))
    bin_path = self.m.path['slave_build'].join('cipd')
    self.m.step(
      "ensure_installed",
			[bin_path.join('cipd'), "ensure",
          "--root", root, "--list", list_data],
    )

