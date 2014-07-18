# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import base_flavor


"""Default flavor utils class, used for desktop builders."""


class DeviceDirs(object):
  def __init__(self,
               gm_actual_dir,
               gm_expected_dir,
               perf_data_dir,
               resource_dir,
               skimage_expected_dir,
               skimage_in_dir,
               skimage_out_dir,
               skp_dirs,
               skp_perf_dir,
               tmp_dir):
    self._gm_actual_dir = gm_actual_dir
    self._gm_expected_dir = gm_expected_dir
    self._perf_data_dir = perf_data_dir
    self._playback_actual_images_dir = skp_dirs.actual_images_dir
    self._playback_actual_summaries_dir = skp_dirs.actual_summaries_dir
    self._playback_expected_summaries_dir = skp_dirs.expected_summaries_dir
    self._resource_dir = resource_dir
    self._skimage_expected_dir = skimage_expected_dir
    self._skimage_in_dir = skimage_in_dir
    self._skimage_out_dir = skimage_out_dir
    self._skp_dir = skp_dirs.skp_dir()
    self._skp_perf_dir = skp_perf_dir
    self._tmp_dir = tmp_dir

  @property
  def gm_actual_dir(self):
    """Holds images and JSON summary written out by the 'gm' tool."""
    return self._gm_actual_dir

  @property
  def gm_expected_dir(self):
    """Holds expectations JSON summary read by the 'gm' tool."""
    return self._gm_expected_dir

  @property
  def perf_data_dir(self):
    return self._perf_data_dir

  @property
  def playback_actual_images_dir(self):
    """Holds image files written out by the 'render_pictures' tool."""
    return self._playback_actual_images_dir

  @property
  def playback_actual_summaries_dir(self):
    """Holds actual-result JSON summaries written by 'render_pictures' tool."""
    return self._playback_actual_summaries_dir

  @property
  def playback_expected_summaries_dir(self):
    """Holds expected-result JSON summaries read by 'render_pictures' tool."""
    return self._playback_expected_summaries_dir

  @property
  def resource_dir(self):
    return self._resource_dir

  @property
  def skimage_in_dir(self):
    return self._skimage_in_dir

  @property
  def skimage_expected_dir(self):
    return self._skimage_expected_dir

  @property
  def skimage_out_dir(self):
    return self._skimage_out_dir

  @property
  def skp_dir(self):
    """Holds SKP files that are consumed by RenderSKPs and BenchPictures."""
    return self._skp_dir

  @property
  def skp_perf_dir(self):
    return self._skp_perf_dir

  @property
  def tmp_dir(self):
    return self._tmp_dir


class DefaultFlavorUtils(base_flavor.BaseFlavorUtils):
  """Utilities to be used by build steps.

  The methods in this class define how certain high-level functions should
  work. Each build step flavor should correspond to a subclass of
  DefaultFlavorUtils which may override any of these functions as appropriate
  for that flavor.

  For example, the AndroidFlavorUtils will override the functions for
  copying files between the host and Android device, as well as the
  'step' function, so that commands may be run through ADB.
  """

  def step(self, name, cmd, **kwargs):
    """Wrapper for the Step API; runs a step as appropriate for this flavor."""
    path_to_app = self._skia_api.m.chromium.output_dir.join(cmd[0])
    if (self._skia_api.m.platform.is_linux and
        'x86_64' in self._skia_api.builder_name and
        not 'TSAN' in self._skia_api.builder_name):
      new_cmd = ['catchsegv', path_to_app]
    else:
      new_cmd = [path_to_app]
    new_cmd.extend(cmd[1:])
    return self._skia_api.m.step(name, new_cmd, **kwargs)

  def device_path_join(self, *args):
    """Like os.path.join(), but for paths on a connected device."""
    return self._skia_api.m.path.join(*args)

  def device_path_exists(self, path):
    """Like os.path.exists(), but for paths on a connected device."""
    return self._skia_api.m.path.exists(path)

  def get_device_dirs(self):
    """ Set the directories which will be used by the build steps.

    These refer to paths on the same device where the test executables will
    run, for example, for Android bots these are paths on the Android device
    itself. For desktop bots, these are just local paths.
    """
    pardir = self._skia_api.m.path.pardir
    join = self._skia_api.m.path['slave_build'].join
    return DeviceDirs(
        gm_actual_dir=join('gm', 'actual'),
        gm_expected_dir=join('gm', 'expected'),
        perf_data_dir=self._skia_api.perf_data_dir,
        resource_dir=self._skia_api.resource_dir,
        skimage_expected_dir=join('skimage', 'expected'),
        skimage_in_dir=self._skia_api.skimage_in_dir,
        skimage_out_dir=self._skia_api.skimage_out_dir,
        skp_dirs=self._skia_api.local_skp_dirs,
        skp_perf_dir=self._skia_api.perf_data_dir,
        tmp_dir=join('tmp'))
