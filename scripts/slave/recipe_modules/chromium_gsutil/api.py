# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class ChromiumGSUtilApi(recipe_api.RecipeApi):
  def download_latest_file(self, base_url, partial_name, destination,
                           name='Download latest file from GS'):
    """Get the latest archived object with the given base url and partial name.

    Args:
      base_url: Base Google Storage archive URL (gs://...) containing the build.
      partial_name: Partial name of the archive file to download.
      destination: Destination file/directory where the file will be downloaded.
      name: The name of the step.
    """
    gsutil_download_path = self.repo_resource(
        'scripts', 'slave', 'gsutil_download.py')
    args = ['--url', base_url,
            '--dst', destination,
            '--partial-name', partial_name]
    with self.m.context(cwd=self.m.path['start_dir']):
      return self.m.build.python(name, gsutil_download_path, args)
