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

  def upload(self, src_path, dest_uri, jobs=None, retries=None, acl=None):
    """Upload the provided src to the destination uri.
    Supports both file and dir upload

    Args:
      src_path: Path to upload to GS
      dest_uri: URI for destination
      jobs: (int) maximum copies to run in parallel
      retries: (int) number of times to retry
      acl: value to pass to for argument -a of gsutil cp

    gsutil [options] cp <src> gs://<dest_uri>
    will copy <src>/xyz... to gs://<dest_uri>/xyz...
    """

    gsutil_cp_dir = self.repo_resource('scripts', 'slave', 'gsutil_cp_dir.py')
    args = [src_path, dest_uri]
    if jobs:
      args += ['-j', jobs]
    if retries:
      args += ['-r', retries]
    if acl:
      args += ['-a', acl]

    with self.m.context(cwd=self.m.path['start_dir']):
      return self.m.build.python('gsutil upload', gsutil_cp_dir, args)
