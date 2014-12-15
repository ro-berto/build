# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This recipe module allows triggering builds within the same master.

Example:
    api.trigger({
        'buildername': 'My Builder',
        'another_property': 'value',
    })

    # This triggers a new build on "My Builder" builder with "another_property"
    property set to "value".

    You can trigger multiple builds in one steps:
    api.trigger({'buildername': 'Release'}, {'buildername': 'Debug'})
"""

from slave import recipe_api


class TriggerApi(recipe_api.RecipeApi):
  """APIs for triggering new builds."""

  def __init__(self, **kwargs):
    super(TriggerApi, self).__init__(**kwargs)

  def __call__(self, *propertiesList, **kwargs):
    """Triggers new builds by builder names.

    Args:
      propertiesList: a list of build property dicts for the builds to
        trigger. Each dict triggers a build. See "Known properties" below.
      name: (in kwargs) name of the step. If not specified, it is generated
        automatically, its format may change in future.

    Known properties:
      buildername (str): Buildbot-specific, required in Buildbot environment.
      buildbot.changes (a list of dicts): Buildbot-specific, changes for the
        triggered builds. Each change is a dict with keys (all optional):
          author (str)
          revision
          revlink (str): link to a web view of the revision.
          comment
          when_timestamp (int): timestamp of the change, in seconds since Unix
            Epoch.
          branch
          category (str): Buildbot change category
          files (list of str): list of changed filenames
        The first change is used to populate source stamp properties.

    Examples:
      Create Buildbot changes:
        api.trigger({
            'builderName': 'Release',
            'my_prop': 123,
            'buildbot.changes': [{
                'author': 'someone@chromium.org',
                'branch': 'master',
                'files': ['a.txt.'],
                'comments': 'Refactoring',
                'revision': 'deadbeef',
                'revlink':
                  'http://chromium.googlesource.com/chromium/src/+/deadbeef',
                'when_timestamp': 1416859562,
            }]
        })
    """
    builder_names = []
    for properties in propertiesList:
      assert isinstance(properties, dict), ('properties must be a dict: %s'
                                            % (properties,))
      builder_name = properties.get('buildername')
      assert builder_name, 'buildername property is missing: %s' % (properties,)
      if builder_name not in builder_names:
        builder_names.append(builder_name)

    name = kwargs.get('name') or ('trigger %s' % ', '.join(builder_names))
    trigger_specs = [
        {
          'properties': properties,
        } for properties in propertiesList
    ]
    return self.m.step(
        name,
        cmd=[],
        trigger_specs=trigger_specs,
    )
