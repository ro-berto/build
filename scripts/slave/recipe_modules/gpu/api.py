# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class GpuApi(recipe_api.RecipeApi):
  def run_telemetry_gpu_test(self, test, name='', args=None,
                             results_directory=''):
    return self.m.chromium.run_telemetry_test(
        str(self.m.path.checkout('content', 'test', 'gpu', 'run_gpu_test')),
        test, name, args, results_directory)

  def archive_pixel_test_results(self, name, run_id, generated_dir,
                                 reference_dir, gsutil=''):
    if not gsutil:
      gsutil = self.m.path.build('scripts', 'slave', 'gsutil',
                                 platform_ext={'win': '.bat'})

    args = ['--run-id',
            run_id,
            '--generated-dir', generated_dir,
            '--gpu-reference-dir', reference_dir,
            '--gsutil', gsutil]
    return self.m.python(name,
                         self.m.path.build('scripts', 'slave', 'chromium',
                                           'archive_gpu_pixel_test_results.py'),
                         args, always_run=True)

