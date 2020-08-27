# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class SymuploadApi(recipe_api.RecipeApi):
  """Chromium specific module for symuploads."""

  def __init__(self, properties, **kwargs):
    super(SymuploadApi, self).__init__(**kwargs)
    self._properties = properties

  def symupload(self, binary, artifact, url):
    """Uploads the given symbols file.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      url: URL of the symbol server to upload to.
    """
    cmd = [
        binary,
        artifact,
        url,
    ]
    self.m.step('symupload %s' % artifact, cmd)

  def __call__(self, build_dir):
    """

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
    """
    if not self._properties.symupload_datas:
      return

    with self.m.step.nest('Symupload'):
      # Check binary before moving on
      symupload_binary = self.m.path.join(build_dir, 'symupload')
      if not self.m.path.exists(symupload_binary):
        raise self.m.step.StepFailure('The symupload binary cannot be found '
                                      'at %s. Please ensure targets symupload '
                                      'and dump_syms are being built such that '
                                      'the binaries are generated.' %
                                      str(symupload_binary))

      for symupload_data in self._properties.symupload_datas:
        self.symupload(symupload_binary,
                       self.m.path.join(build_dir, symupload_data.artifact),
                       symupload_data.url)
