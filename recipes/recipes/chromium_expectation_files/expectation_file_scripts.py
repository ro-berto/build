# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (DoesNotRun, DropExpectation,
                                        ResultReason, StatusException,
                                        StatusFailure, StatusSuccess,
                                        StepCommandRE, StepFailure, StepSuccess)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb
from PB.recipes.build.chromium_expectation_files.expectation_file_scripts \
    import InputProperties, ScriptInvocation
from RECIPE_MODULES.build import proto_validation

PROPERTIES = InputProperties

DEPS = [
    'chromium',
    'chromium_bootstrap',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/git_cl',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/random',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
    'recipe_engine/url',
]

VALIDATORS = proto_validation.Registry()

ROTATION_URL = (
    'https://chrome-ops-rotation-proxy.appspot.com/current/oncallator:')

RUBBER_STAMPER = 'rubber-stamper@appspot.gserviceaccount.com'

# It's possible for 'main' to already exist, so use a different name from that
# to be safe.
MAIN_BRANCH = 'main_expectations'


def RunSteps(api, properties):
  errors = VALIDATORS.validate(properties)
  if errors:
    summary = ['The following errors were found with the input properties:', '']
    summary.extend(errors)
    return result_pb.RawResult(
        status=common_pb.INFRA_FAILURE, summary_markdown='\n'.join(summary))

  api.gclient.set_config('chromium_skip_wpr_archives_download')
  with api.chromium_bootstrap.update_gclient_config() as callback:
    update_step = api.bot_update.ensure_checkout(refs=['refs/heads/main'])
    callback(update_step.json.output['manifest'])
  api.gclient.runhooks()
  api.git(
      'config',
      'user.name',
      'Expectation File Editor',
      name='set git config user.name')
  api.git.new_branch(MAIN_BRANCH, name='create main branch')

  failures = []
  for script_invocation in properties.scripts:
    with api.step.nest(script_invocation.step_name):
      # We don't care about the specific branch name, just that there won't be
      # any overlap.
      api.git.new_branch(str(api.time.time()), name='create script branch')
      try:
        _RunScript(api, script_invocation)
      except api.step.StepFailure as e:
        failures.append(e)
      finally:
        api.git('reset', '--hard', 'HEAD', name='reset to HEAD')
        api.git('checkout', MAIN_BRANCH, name='return to main branch')

  if failures:
    exception_type = api.step.InfraFailure if any(
        isinstance(f, api.step.InfraFailure)
        for f in failures) else api.step.StepFailure
    raise exception_type('%d script invocation(s) failed' % len(failures))


def _RunScript(api, script_invocation):
  result_output_file = api.raw_io.output_text(
      suffix='.html', name='script_results')
  has_bug_file = False
  cmd = [api.path['checkout'].join(script_invocation.script)]
  cmd.extend(script_invocation.args)
  cmd.extend(['--result-output-file', result_output_file])
  if (script_invocation.script_type ==
      ScriptInvocation.ScriptType.UNEXPECTED_PASS):
    has_bug_file = True
    cmd.extend(['--bug-output-file', api.raw_io.output_text()])
  elif (script_invocation.script_type ==
        ScriptInvocation.ScriptType.FLAKE_FINDER):
    cmd.append('--bypass-up-to-date-check')

  invocation_step = api.step(name='run script', cmd=cmd)
  invocation_step.presentation.logs['HTML results'] = (
      invocation_step.raw_io.output_texts['script_results'])
  cl_cmdline = ['//' + script_invocation.script] + list(script_invocation.args)
  bug_file_contents = ''
  if has_bug_file:
    bug_file_contents = invocation_step.raw_io.output_text

  _UploadCL(api, script_invocation, bug_file_contents, cl_cmdline)


def _GenerateCLMessage(script_invocation,
                       bug_file_contents,
                       cmdline,
                       additional_text=None):
  additional_text = additional_text or ''
  cl_description = [
      script_invocation.cl_title,
      '\n\n',
      'Autogenerated CL from running:\n\n%s\n\n' % ' '.join(cmdline),
      additional_text,
  ]
  if bug_file_contents:
    cl_description.extend([bug_file_contents, '\n'])
  if script_invocation.additional_trybots:
    cl_description.append('Cq-Include-Trybots: %s\n' %
                          ','.join(script_invocation.additional_trybots))
  return ''.join(cl_description)


def _UploadCL(api, script_invocation, bugs, cmdline):
  message = _GenerateCLMessage(script_invocation, bugs, cmdline)
  api.git('add', '-u')
  api.git('commit', '-m', 'commit expectation file changes')

  reviewer_list = _GetReviewerList(api, script_invocation)
  if not reviewer_list:
    api.step.empty('missing reviewers', status='FAILURE')
  # Choose a random reviewer from the list.
  reviewer_list = [api.random.choice(reviewer_list)]
  original_reviewer_list = reviewer_list
  cc_list = []
  if script_invocation.submit_type == ScriptInvocation.SubmitType.AUTO:
    cc_list = reviewer_list
    reviewer_list = [RUBBER_STAMPER]

  # TODO(crbug.com/1340614): Add in --enable-auto-submit once we're ready to
  # start actually using this recipe on bots regularly.
  upload_args = ['--force', '--send-mail', '--reviewers', reviewer_list[0]]
  if cc_list:
    upload_args.extend(['--cc', ','.join(cc_list)])
  with api.context(cwd=api.path['checkout']):
    result = api.git_cl.upload(
        message,
        upload_args=upload_args,
        name='upload cl',
        stdout=api.raw_io.output_text(),
        raise_on_failure=False)
    # Upload succeeded, we're done.
    if not result.retcode:
      return
    # If expectation conflicts were found, upload the CL and let the reviewer
    # know that they will need to resolve them. If we were going to submit
    # automatically, switch to manual submission since automatic will not
    # pass the CQ with the conflicts in.
    if 'Found conflicts for pattern' in result.stdout:
      upload_args = [
          '--force', '--send-mail', '--reviewers', original_reviewer_list[0],
          '--bypass-hooks'
      ]
      message = _GenerateCLMessage(
          script_invocation, bugs, cmdline,
          'Found conflicts in expectations, these will need to be manually '
          'resolved before submitting.')
      api.git_cl.upload(
          message, upload_args=upload_args, name='upload cl (has conflicts)')
    else:
      api.step.raise_on_failure(result)


def _GetReviewerList(api, script_invocation):
  if script_invocation.reviewer_rotation:
    # Pull reviewers from a rotation.
    rotation = script_invocation.reviewer_rotation
    url = api.url.join(ROTATION_URL, rotation)
    rotation_json = api.url.get_json(
        url, step_name='get %s rotation JSON' % rotation).output
    return rotation_json['emails']
  # List of reviewers provided.
  return script_invocation.reviewer_list.reviewer


@VALIDATORS.register(InputProperties)
def _validate_input_properties(message, ctx):
  ctx.validate_repeated_field(message, 'scripts')


@VALIDATORS.register(ScriptInvocation)
def _validate_script_invocation(message, ctx):
  ctx.validate_field(message, 'step_name')
  ctx.validate_field(message, 'script')
  ctx.validate_field(message, 'script_type')
  ctx.validate_field(message, 'submit_type')
  ctx.validate_field(message, 'cl_title')

  reviewer_selection = message.WhichOneof('reviewer_selection')
  if reviewer_selection:
    ctx.validate_field(message, reviewer_selection)
  else:
    ctx.error('No reviewer_rotation/reviewer_list set.')


@VALIDATORS.register(ScriptInvocation.ReviewerList)
def _validate_reviewer_list(message, ctx):
  ctx.validate_repeated_field(message, 'reviewer')


def GenTests(api):
  yield api.test(
      'happy_path_flake_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.FLAKE_FINDER,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.post_process(StepCommandRE, 'step_name.run script', [
          '.*some/script.py',
          '--some-arg',
          '--result-output-file',
          '.*',
          '--bypass-up-to-date-check',
      ]),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py --some-arg\n\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'conflict_flake_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.FLAKE_FINDER,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.step_data(
          'step_name.upload cl',
          api.raw_io.stream_output_text(
              'output\nFound conflicts for pattern', stream='stdout'),
          retcode=1),
      api.post_process(StepFailure, 'step_name.upload cl'),
      api.post_process(StepCommandRE, 'step_name.upload cl (has conflicts)', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r',
          '--bypass-hooks',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py --some-arg\n\nFound conflicts in expectations, '
           'these will need to be manually resolved before submitting.'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'no_conflict_failure_flake_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.FLAKE_FINDER,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.step_data('step_name.upload cl', retcode=1),
      api.post_process(StepFailure, 'step_name.upload cl'),
      api.post_process(DoesNotRun, 'step_name.upload cl (has conflicts)'),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'conflict_then_failure_flake_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.FLAKE_FINDER,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.step_data(
          'step_name.upload cl',
          api.raw_io.stream_output_text(
              'output\nFound conflicts for pattern', stream='stdout'),
          retcode=1),
      api.step_data('step_name.upload cl (has conflicts)', retcode=1),
      api.post_process(StepFailure, 'step_name.upload cl'),
      api.post_process(StepFailure, 'step_name.upload cl (has conflicts)'),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'conflict_switches_to_manual_flake_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.FLAKE_FINDER,
                  submit_type=ScriptInvocation.SubmitType.AUTO,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.step_data(
          'step_name.upload cl',
          api.raw_io.stream_output_text(
              'output\nFound conflicts for pattern', stream='stdout'),
          retcode=1),
      api.post_process(StepFailure, 'step_name.upload cl'),
      api.post_process(StepCommandRE, 'step_name.upload cl (has conflicts)', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r',
          '--bypass-hooks',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py --some-arg\n\nFound conflicts in expectations, '
           'these will need to be manually resolved before submitting.'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'happy_path_unexpected_pass_finder',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  args=['--some-arg'],
              )
          ])),
      api.step_data('step_name.run script',
                    api.raw_io.output_text('Bug: 1234')),
      api.post_process(StepCommandRE, 'step_name.run script', [
          '.*/some/script.py',
          '--some-arg',
          '--result-output-file',
          '.*',
          '--bug-output-file',
          '.*',
      ]),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py --some-arg\n\nBug: 1234\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'additional_trybots',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
                  additional_trybots=['tb1', 'tb2'],
              )
          ])),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py\n\nCq-Include-Trybots: tb1,tb2\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'one_reviewer_selected',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=[
                      'r1',
                      'r2',
                  ]),
                  cl_title='cl_title')
          ])),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r2',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py\n\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'auto_submit',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.AUTO,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title'),
          ])),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'rubber-stamper@appspot.gserviceaccount.com',
          '--cc',
          'r',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py\n\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'reviewer_rotation',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_rotation='reviewer_rotation',
                  cl_title='cl_title',
              )
          ])),
      api.url.json('step_name.get reviewer_rotation rotation JSON',
                   {'emails': ['r@google.com']}),
      api.post_process(
          StepCommandRE,
          'step_name.get reviewer_rotation rotation JSON',
          [
              '.*',
              '.*',
              '.*',
              '--url',
              ('https://chrome-ops-rotation-proxy.appspot.com/'
               'current/oncallator:/reviewer_rotation'),
              '.*',
              '.*',
              '.*',
              '.*',
          ],
      ),
      api.post_process(StepCommandRE, 'step_name.upload cl', [
          '.*',
          '.*',
          'upload',
          '--force',
          '--send-mail',
          '--reviewers',
          'r@google.com',
          '--message-file',
          ('cl_title\n\nAutogenerated CL from running:\n\n'
           '//some/script.py\n\n'),
      ]),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'no_reviewers',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_rotation='reviewer_rotation',
                  cl_title='cl_title')
          ])),
      api.url.json('step_name.get reviewer_rotation rotation JSON',
                   {'emails': []}),
      api.post_process(StepFailure, 'step_name.missing reviewers'),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_missing_scripts',
      api.properties(InputProperties(scripts=[])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts is empty'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_missing_step_name',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].step_name is not set'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_missing_script',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].script is not set'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_unspecified_script_type',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType
                  .SCRIPT_TYPE_UNSPECIFIED,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].script_type is not set'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_unspecified_submit_type',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType
                  .SUBMIT_TYPE_UNSPECIFIED,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].submit_type is not set'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_reviewer_selection_none_set',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'No reviewer_rotation/reviewer_list set.'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_reviewer_selection_empty_list',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=[]),
                  cl_title='cl_title',
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].reviewer_list.reviewer is empty'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'validate_missing_cl_title',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
              )
          ])),
      api.post_process(
          ResultReason,
          'The following errors were found with the input properties:\n\n'
          'scripts[0].cl_title is not set'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'multiple_scripts_with_failure',
      api.properties(
          InputProperties(scripts=[
              ScriptInvocation(
                  step_name='step_name_failure',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title'),
              ScriptInvocation(
                  step_name='step_name_success',
                  script='some/script.py',
                  script_type=ScriptInvocation.ScriptType.UNEXPECTED_PASS,
                  submit_type=ScriptInvocation.SubmitType.MANUAL,
                  reviewer_list=ScriptInvocation.ReviewerList(reviewer=['r']),
                  cl_title='cl_title')
          ])),
      api.step_data('step_name_failure.run script', retcode=1),
      api.post_process(StepFailure, 'step_name_failure.run script'),
      api.post_process(StepSuccess, 'step_name_success'),
      api.post_process(StatusFailure),
      api.post_process(ResultReason, '1 script invocation(s) failed'),
      api.post_process(DropExpectation),
  )
