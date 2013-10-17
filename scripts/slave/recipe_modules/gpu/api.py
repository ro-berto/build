# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class GpuApi(recipe_api.RecipeApi):
  def run_telemetry_gpu_test(self, test, step_name='', args=[],
      results_directory=''):
    # Choose a reasonable default for the location of the sandbox binary
    # on the bots.
    env = {}
    if self.m.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = '/opt/chromium/chrome_sandbox'

    if not step_name:
      step_name = test

    # The step name must end in 'test' or 'tests' in order for the results to
    # automatically show up on the flakiness dashboard.
    if not (step_name.endswith('test') or step_name.endswith('tests')):
      step_name = '%s_tests' % step_name

    test_args = [test,
        '--show-stdout',
        '--output-format=gtest',
        '--browser=%s' % self.m.chromium.c.BUILD_CONFIG.lower()]

    if args:
      test_args = test_args + args

    if not results_directory:
      results_directory = self.m.path.slave_build('gtest-results', step_name)

    return self.m.chromium.runtests(
        str(self.m.path.checkout('content', 'test', 'gpu', 'run_gpu_test')),
        test_args,
        annotate='gtest',
        name=step_name,
        test_type=step_name,
        generate_json_file=True,
        results_directory=results_directory,
        build_number=self.m.properties['buildnumber'],
        builder_name=self.m.properties['buildername'],
        python_mode=True,
        env=env)

  def archive_pixel_test_results(self, step_name, run_id, generated_dir,
      reference_dir, gsutil=''):
    if not gsutil:
      gsutil = self.m.path.build('scripts', 'slave', 'gsutil',
          platform_ext={'win': '.bat'})

    args = ['--run-id',
        run_id,
        '--generated-dir', generated_dir,
        '--gpu-reference-dir', reference_dir,
        '--gsutil', gsutil]
    return self.m.python(step_name,
        self.m.path.build('scripts', 'slave', 'chromium', \
            'archive_gpu_pixel_test_results.py'),
        args, always_run=True)

