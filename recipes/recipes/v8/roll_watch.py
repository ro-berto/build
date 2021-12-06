# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api
from recipe_engine.post_process import (
    Filter, DoesNotRun, DoesNotRunRE, DropExpectation, MustRun,
    ResultReasonRE, StatusException, StatusFailure, StepException)

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
            kind=list,
            help='Roller descriptors',
            default=[])
}


def RunSteps(api, watched_rollers):
    with api.depot_tools.on_path():
        for roller in watched_rollers:
            with api.step.nest('Roller: \'%s\'' % roller['subject']):
                process_roller(api, roller)


def process_roller(api, roller):
    rejects = find_open_CLs(api, roller)
    for cl in rejects:
        if cl['subject'] == roller['subject']:
            process_cl(api, roller, cl)


def find_open_CLs(api, roller):
    return api.gerrit.get_changes(
        'https://%s' % roller['review-host'],
        query_params=[
            ('project', roller['project'] ),
            ('owner', roller['account']),
            ('status', 'open'),
        ],
        o_params = ['LABELS', 'CURRENT_REVISION', 'DOWNLOAD_COMMANDS'],
        limit=20,
        step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
        name = 'Find open CLs',
    )


def process_cl(api, roller, cl):
    cl_path = '%s/+/%s' % (cl['project'], cl['_number'])
    with api.step.nest('Checking CL') as parent_step:
        parent_step.presentation.links[cl_path] = 'https://%s/c/%s' % (
            roller['review-host'], cl_path,
        )
        last_patch = cl['revisions'].values()[0]
        builds = api.buildbucket.search(
            builds_service_pb2.BuildPredicate(
                gerrit_changes=list([{
                    'host' : roller['review-host'],
                    'change' : cl['_number'],
                    'patchset' : last_patch['_number'],
                    'project': roller['project'],
                }]),
            ),
            limit=100,
            fields=['steps.*'],
            report_build = False,
        )
        failures = [build for build in builds
                if build.status == common_pb2.FAILURE]
        if failures:
            parent_step.presentation.step_text = '\nCL failed in CQ!'
            parent_step.presentation.status = api.step.FAILURE


def GenTests(api):
    def test(api, name):
        return (api.test(name) +
                api.properties(watched_rollers=[{
                    'subject': 'Update dependencies',
                    'review-host': 'review.googlesource.com',
                    'project': 'v8/v8',
                    'account': 'autoroll@service-accounts.com',
                }]))

    yield test(api, "no-cls")

    yield (
        test(api, "roller-with-stale-cls") + 
        api.override_step_data('Roller: \'Update dependencies\'.'
                'gerrit Find open CLs',
                api.json.output([{
                        '_number': 123,
                        'subject': 'Update dependencies (Frontend)',
                        'project':'project1',
                        'revisions': {
                                'last': {'_number': 1}
                        }
                }])
        ))

    yield (
        test(api, "roll-failing-in-cq") + 
        api.override_step_data('Roller: \'Update dependencies\'.'
                'gerrit Find open CLs',
                api.json.output([{
                        '_number': 123,
                        'subject': 'Update dependencies',
                        'project':'project1',
                        'revisions': {
                                'last': {'_number': 1}
                        }
                }])
        ) + 
        api.buildbucket.simulated_search_results([
                build_pb2.Build(id=1, status=common_pb2.SUCCESS),
                build_pb2.Build(id=2, status=common_pb2.FAILURE),
            ], step_name = 'Roller: \'Update dependencies\'.'
            'Checking CL.buildbucket.search'
        ))
