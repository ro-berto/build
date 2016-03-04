# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from recipe_engine import recipe_api



class CTSwarmingApi(recipe_api.RecipeApi):
  """Provides steps to run CT tasks on swarming bots."""

  CT_GS_BUCKET = 'cluster-telemetry'

  @property
  def downloads_dir(self):
    """Path to where artifacts should be downloaded from Google Storage."""
    return self.m.path['slave_build'].join('src', 'content', 'test', 'ct')

  def checkout_dependencies(self):
    """Checks out all repositories required for CT to run on swarming bots."""
    # Checkout chromium and swarming.
    self.m.chromium.set_config('chromium')
    self.m.gclient.set_config('chromium')
    self.m.bot_update.ensure_checkout(force=True)
    self.m.swarming_client.checkout()
    # Ensure swarming_client is compatible with what recipes expect.
    self.m.swarming.check_client_version()

  def download_CT_binary(self, ct_binary_name):
    """Downloads the specified CT binary from GS into the downloads_dir."""
    binary_dest = self.downloads_dir.join(ct_binary_name)
    self.m.gsutil.download(
        name="download %s" % ct_binary_name,
        bucket=self.CT_GS_BUCKET,
        source='swarming/binaries/%s' % ct_binary_name,
        dest=binary_dest)
    # Set executable bit on the binary.
    self.m.python.inline(
        name='Set executable bit on %s' % ct_binary_name,
        program='''
import os
import stat

os.chmod('%s', os.stat('%s').st_mode | stat.S_IEXEC)
''' % (str(binary_dest), str(binary_dest))
    )

  def download_page_artifacts(self, page_type, slave_num):
    """Downloads all the artifacts needed to run benchmarks on a page.

    The artifacts are downloaded into subdirectories in the downloads_dir.

    Args:
      page_type: str. The CT page type. Eg: 1k, 10k.
      slave_num: int. The number of the slave used to determine which GS
                 directory to download from. Eg: for the top 1k, slave1 will
                 contain webpages 1-10, slave2 will contain 11-20.
    """
    # Download page sets.
    page_sets_dir = self.downloads_dir.join('slave%s' % slave_num, 'page_sets')
    self.m.file.makedirs('page_sets dir', page_sets_dir)
    self.m.gsutil.download(
        bucket=self.CT_GS_BUCKET,
        source='swarming/page_sets/%s/slave%s/*' % (page_type, slave_num),
        dest=page_sets_dir)

    # Download archives.
    wpr_dir = page_sets_dir.join('data')
    self.m.file.makedirs('WPR dir', wpr_dir)
    self.m.gsutil.download(
        bucket=self.CT_GS_BUCKET,
        source='swarming/webpage_archives/%s/slave%s/*' % (page_type,
                                                           slave_num),
        dest=wpr_dir)
