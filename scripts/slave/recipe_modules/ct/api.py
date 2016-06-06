# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from recipe_engine import recipe_api



class CTApi(recipe_api.RecipeApi):
  """Provides steps to run CT tasks."""

  CT_GS_BUCKET = 'cluster-telemetry'

  def download_skps(self, page_type, slave_num, skps_chromium_build, dest_dir):
    """Downloads SKPs corresponding to the specified page type, slave and build.

    The SKPs are downloaded into subdirectories in the dest_dir.

    Args:
      api: RecipeApi instance.
      page_type: str. The CT page type. Eg: 1k, 10k.
      slave_num: int. The number of the slave used to determine which GS
                 directory to download from. Eg: for the top 1k, slave1 will
                 contain SKPs from webpages 1-10, slave2 will contain 11-20.
      skps_chromium_build: str. The build the SKPs were captured from.
      dest_dir: path obj. The directory to download SKPs into.
    """
    skps_dir = dest_dir.join('slave%s' % slave_num)
    self.m.file.makedirs('SKPs dir', skps_dir)
    full_source = 'gs://%s/skps/%s/%s/slave%s' % (
        self.CT_GS_BUCKET, page_type, skps_chromium_build, slave_num)
    self.m.gsutil(['-m', 'rsync', '-d', '-r', full_source, skps_dir])
