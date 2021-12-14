# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from PB.recipe_engine import result
from recipe_engine.post_process import (
    DropExpectation, DropExpectation, StatusFailure, StatusSuccess)

from PB.go.chromium.org.luci.buildbucket.proto import (
        builds_service as builds_service_pb2,
        common as common_pb2,
        build as build_pb2)
from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'depot_tools/depot_tools',
    'depot_tools/gerrit',
    'depot_tools/git',

    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


PROPERTIES = {
    'watched_rollers': Property(
            help='Roller descriptors',
            default=[],
            kind=list
    )
}


def RunSteps(api, watched_rollers):
    with api.depot_tools.on_path():
        for roller in watched_rollers:
            with api.step.nest("Roller: '%s'" % roller['name']):
                process_roller(api, roller)
    if any(roller.get('has_failure', False) for roller in watched_rollers):
        return result.RawResult(status=common_pb2.FAILURE)


def process_roller(api, roller):
    open_cls = find_open_CLs(api, roller)
    for cl in open_cls:
        if verify_subject(roller, cl):
            process_cl(api, roller, cl)


def find_open_CLs(api, roller):
    return api.gerrit.get_changes(
        'https://%s' % roller['review-host'],
        query_params=[
            ('project', roller['project'] ),
            ('owner', roller['account']),
            ('status', 'open'),
            ('-hashtag', 'rw_reported'),
        ] + additional_criteria(roller),
        o_params = ['LABELS', 'CURRENT_REVISION'],
        limit=20,
        step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
        name='Find open CLs',
    )


def verify_subject(roller, cl):
    return ('subject' not in roller) or (roller['subject'] == cl['subject'])


def additional_criteria(roller):
    return [term.split(':') for term in roller.get('criteria',[])]


def process_cl(api, roller, cl):
    with api.step.nest('Checking CL') as parent_step:
        present_cl_link(roller, cl, parent_step.presentation)
        builds = find_cq_blocking_builds(api, roller, cl)
        failures = [build for build in builds if failed(build)]
        if failures:
            run_failure_recovery(api, roller, cl, failures)


def find_cq_blocking_builds(api, roller, cl):
    return api.buildbucket.search(
        builds_service_pb2.BuildPredicate(
            gerrit_changes=[{
                'host' : roller['review-host'],
                'change' : cl['_number'],
                'patchset' : last_patch_number(cl),
                'project': roller['project'],
            }],
            tags=[common_pb2.StringPair(key='cq_experimental', value='false')]
        ),
        limit=100,
        fields=['steps.*'],
        report_build = False,
    )


def present_cl_link(roller, cl, presentation):
    cl_path = '%s/+/%s' % (cl['project'], cl['_number'])
    presentation.links[cl_path] = 'https://%s/c/%s' % (
            roller['review-host'],
            cl_path,
    )


def last_patch_number(cl):
    return cl['revisions'].values()[0]['_number']


def failed(build):
    return build.status in [common_pb2.FAILURE, common_pb2.INFRA_FAILURE]


def run_failure_recovery(api, roller, cl, failures):
    default_recovery = ['mark_as_reported','just_fail']
    for recovery_fn_name in roller.get('failure_recovery', default_recovery):
        recovery_fn = find_recovery_fn(recovery_fn_name)
        recovery_fn(api, roller, cl, failures)


def find_recovery_fn(name):
    return {
        'just_fail': just_fail,
        'just_pass': just_pass,
        'mark_as_reported': mark_as_reported,
    }[name]


def just_fail(api, roller, cl, failures):
    failure_step = api.step("Roller '%s' failed" % roller['name'], cmd=None)
    failure_step.presentation.status = api.step.FAILURE
    present_cl_link(roller, cl, failure_step.presentation)
    roller['has_failure'] = True


def just_pass(api, roller, cl, failures):
    pass


def mark_as_reported(api, roller, cl, failures):
    api.gerrit.call_raw_api('https://%s' % roller['review-host'],
                '/changes/%s/hashtags' % cl['_number'],
                method='POST',
                body={"add":["rw_reported"]},
                accept_statuses=[200, 201],
                name='Mark as reported')


def GenTests(api):
    def test(api, name, **kwargs):
        config = {
                'name' : 'roller',
                'subject': 'Update dependencies',
                'review-host': 'review.googlesource.com',
                'project': 'v8/v8',
                'account': 'autoroll@service-accounts.com',
        }
        config.update(**kwargs)
        return (api.test(name) +
                api.properties(watched_rollers=[config]))

    def find_fake_cls(api):
        return api.override_step_data("Roller: 'roller'."
                'gerrit Find open CLs',
                api.json.output([{
                        '_number': 123,
                        'subject': 'Update dependencies',
                        'project':'project1',
                        'revisions': {
                                'last': {'_number': 1}
                        }
                }]))

    def find_fake_builds(*builds):
        return api.buildbucket.simulated_search_results(list(builds),
            step_name = "Roller: 'roller'.Checking CL.buildbucket.search")

    def build(build_id, status, builder_name=None, experimental=False):
        exp_tag = common_pb2.StringPair(key='cq_experimental',
                value='true' if experimental else 'false')
        return build_pb2.Build(id=build_id, status=status, tags=[exp_tag])

    yield test(api, "no-cls")

    yield (
        test(api, "roller-with-stale-cls") +
        find_fake_cls(api) +
        api.post_process(StatusSuccess))

    yield (
        test(api, "roll-failing-in-cq-default") +
        find_fake_cls(api) +
        find_fake_builds(
                build(1, common_pb2.SUCCESS),
                build(2, common_pb2.FAILURE),
        ) +
        api.post_process(StatusFailure))

    yield (
        test(api, "roll-failing-in-cq-just-pass",
                criteria=["hashtags:sometag"],
                failure_recovery = ["just_pass"]) +
        find_fake_cls(api) +
        find_fake_builds(
                build(1, common_pb2.SUCCESS),
                build(2, common_pb2.FAILURE),
        ) +
        api.post_process(StatusSuccess))
