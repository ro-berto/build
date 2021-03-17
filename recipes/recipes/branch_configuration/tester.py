# Copyright 20201 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests a change for branch-conditional LUCI services starlark.

The starlark config for the chromium and chrome LUCI projects contains
branch-conditional logic to enable regenerating the configuration files
for release branches by only changing a JSON settings file.
Unfortunately, unless extreme care is taken, it's possible to make a
change on trunk that has no problems but that causes an error when
executed with the settings modified for a branch.

This recipe provides the means to ensure that the configuration can be
generated with the settings modified, so that unexpected errors
shouldn't occur when generating the branch config on branch day. It
provides no guarantees about the effect of the generated configuration
files, only that they can be generated.

To run this, the repo against which the recipe is run must have a script
that can be used to change the branch type of the configuration and
scripts that can be used to verify that the configuration "works". It is
not necessarily feasible to ensure that the configuration has the
desired effects, but at a minimum the starlark scripts can be executed
to verify that the configuration can be generated for the different
branch types with the change under test. See tester.proto for details on
the scripts.
"""

from recipe_engine import post_process

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb
from PB.recipes.build.branch_configuration import tester as tester_pb

PROPERTIES = tester_pb.InputProperties

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def _validate_properties(properties):
  errors = []

  if not properties.branch_script:
    errors.append('branch_script is empty')

  if not properties.branch_types:
    errors.append('branch_types is empty')

  if not properties.verification_scripts:
    errors.append('verification_scripts is empty')

  def validate_repeated_field(field_name, elements):
    element_map = {}
    for i, element in enumerate(elements):
      if not element:
        errors.append('{}[{}] is empty'.format(field_name, i))
      else:
        element_map.setdefault(element, []).append(i)

    for element, indices in element_map.iteritems():
      if len(indices) > 1:
        errors.append("multiple occurrences of '{}' in {}: {!r}".format(
            element, field_name, indices))

  validate_repeated_field('branch_types', properties.branch_types)

  validate_repeated_field('verification_scripts',
                          properties.verification_scripts)

  return errors


def _result(status, header, elements, footer=None):
  summary = [header, '']
  summary.extend('* {}'.format(e) for e in elements)
  if footer:
    summary.extend(['', footer])
  return result_pb.RawResult(status=status, summary_markdown='\n'.join(summary))


def RunSteps(api, properties):
  errors = _validate_properties(properties)
  if errors:
    return _result(
        status=common_pb.INFRA_FAILURE,
        elements=errors,
        header='The following errors were found with the input properties:')

  gclient_config = api.gclient.make_config()
  s = gclient_config.solutions.add()
  s.url = api.tryserver.gerrit_change_repo_url
  s.name = s.url.rsplit('/', 1)[-1]
  gclient_config.got_revision_mapping[s.name] = 'got_revision'

  with api.context(cwd=api.path['cache'].join('builder')):
    update_result = api.bot_update.ensure_checkout(
        patch=True, gclient_config=gclient_config)

  repo_path = api.path['cache'].join('builder',
                                     update_result.json.output['root'])

  bad_branch_types = []
  with api.context(cwd=repo_path):
    branch_script = repo_path.join(properties.branch_script)
    for branch_type in properties.branch_types:
      with api.step.nest(branch_type):
        api.step(
            'set branch type',
            [branch_script, 'set-type', '--type', branch_type],
            infra_step=True)

        with api.step.nest('verify'):
          try:
            with api.step.defer_results():
              for script in properties.verification_scripts:
                api.step(script, [script])
          except api.step.StepFailure:
            bad_branch_types.append(branch_type)

        with api.step.nest('restore'):
          api.git('restore', '.', infra_step=True)
          api.git('clean', '-f', infra_step=True)

  if bad_branch_types:
    return _result(
        status=common_pb.FAILURE,
        elements=bad_branch_types,
        header='The following branch types failed verification:',
        footer='See steps for more information')


def GenTests(api):
  yield api.test(
      'basic',
      api.buildbucket.try_build(),
      api.properties(
          tester_pb.InputProperties(
              branch_script='branch-script',
              branch_types=['branch-type1', 'branch-type2'],
              verification_scripts=[
                  'verification-script1',
                  'verification-script2',
              ],
          )),
      api.post_check(
          post_process.MustRun,
          'branch-type1.set branch type',
          'branch-type1.verify.verification-script1',
          'branch-type1.verify.verification-script2',
          'branch-type2.set branch type',
          'branch-type2.verify.verification-script1',
          'branch-type2.verify.verification-script2',
      ),
      api.post_check(post_process.StatusSuccess),
  )

  yield api.test(
      'failed set branch type step',
      api.buildbucket.try_build(),
      api.properties(
          tester_pb.InputProperties(
              branch_script='branch-script',
              branch_types=['bad-branch-type'],
              verification_scripts=[
                  'verification-script1',
                  'verification-script2',
              ],
          )),
      api.step_data('bad-branch-type.set branch type', retcode=1),
      api.post_check(post_process.StepException, 'bad-branch-type'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed verification step',
      api.buildbucket.try_build(),
      api.properties(
          tester_pb.InputProperties(
              branch_script='branch-script',
              branch_types=['branch-type1', 'branch-type2', 'branch-type3'],
              verification_scripts=[
                  'verification-script1',
                  'verification-script2',
              ],
          )),
      api.step_data('branch-type1.verify.verification-script1', retcode=1),
      api.step_data('branch-type3.verify.verification-script2', retcode=1),
      api.post_check(post_process.StepFailure,
                     'branch-type1.verify.verification-script1'),
      api.post_check(post_process.StepFailure, 'branch-type1'),
      api.post_check(post_process.StepFailure,
                     'branch-type3.verify.verification-script2'),
      api.post_check(post_process.StepFailure, 'branch-type3'),
      api.post_check(post_process.StepSuccess, 'branch-type2'),
      api.post_check(post_process.StatusFailure),
      api.post_check(post_process.ResultReasonRE,
                     '^The following branch types failed verification'),
      api.post_check(post_process.ResultReasonRE, r'\bbranch-type1\b'),
      api.post_check(post_process.ResultReasonRE, r'\bbranch-type3\b'),
      api.post_process(post_process.DropExpectation),
  )

  # Must appear last since it drops expectations
  def invalid_properties(*errors):
    test_data = api.post_check(post_process.StatusException)
    test_data += api.post_check(
        post_process.ResultReasonRE,
        '^The following errors were found with the input properties')
    for error in errors:
      test_data += api.post_check(post_process.ResultReasonRE, error)
    test_data += api.post_process(post_process.DropExpectation)
    return test_data

  yield api.test(
      'empty input properties',
      api.buildbucket.try_build(),
      api.properties(tester_pb.InputProperties()),
      invalid_properties(
          'branch_script is empty',
          'branch_types is empty',
          'verification_scripts is empty',
      ),
  )

  yield api.test(
      'invalid input properties',
      api.buildbucket.try_build(),
      api.properties(
          tester_pb.InputProperties(
              branch_script='branch-script',
              branch_types=['', 'branch-type', 'branch-type'],
              verification_scripts=[
                  '',
                  'verification-script',
                  'verification-script',
              ],
          )),
      invalid_properties(
          r'\bbranch_types\[0\] is empty\b',
          r"\bmultiple occurrences of 'branch-type' in branch_types: \[1, 2\]",
          r'\bverification_scripts\[0\] is empty\b',
          (r"\bmultiple occurrences of 'verification-script' "
           r'in verification_scripts: \[1, 2\]'),
      ),
  )
