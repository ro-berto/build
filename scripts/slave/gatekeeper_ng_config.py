#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Loads gatekeeper configuration files for use with gatekeeper_ng.py.

The gatekeeper json configuration file has two main sections: 'masters'
and 'categories.' The following shows the breakdown of a possible config,
but note that all nodes are optional (including the root 'masters' and
'categories' nodes).

A builder ultimately needs 4 lists (sets):
  closing_optional: steps which close the tree on failure
  forgiving_optional: steps which close the tree but don't email committers
  tree_notify: any additional emails to notify on tree failure
  sheriff_classes: classes of sheriffs to notify on build failure

Builders can inherit these properties from categories, they can inherit
tree_notify and sheriff_classes from their master, and they can have these
properties assigned in the builder itself. Any property not specified
is considered blank (empty set), and inheritance is always constructive (you
can't remove a property by inheriting or overwriting it). Builders can inherit
categories from their master.

A master consists of zero or more sections, which specify which builders are
watched by the section and what action should be taken.

The 'excluded_builders' key is a list of builder names that will not be
processed even if they match a configuration. This is useful when the builder
set is specified using the wildcard ('*'). Entries in this list may use
filename-style globbing (e.g., *mybuilder*) to specify builder name patterns.

The 'subject_template' key is the template used for the email subjects. Its
formatting arguments are found at https://chromium.googlesource.com/chromium/
  tools/chromium-build/+/master/gatekeeper_mailer.py, but the list is
reproduced here:

  %(result)s: 'warning' or 'failure'
  %(project_name): 'Chromium', 'Chromium Perf', etc.
  %(builder_name): the builder name
  %(reason): reason for launching the build
  %(revision): build revision
  %(buildnumber): buildnumber
  %(steps): comma-separated list of failed steps

The 'status_template' is what is sent to the status app if the tree is set to be
closed. Its formatting arguments are found in gatekeeper_ng.py's
close_tree_if_necessary().

'forgive_all' converts all closing_optional to be forgiving_optional. Since
forgiving_optional only email sheriffs + watchlist (not the committer), this is
a great way to set up experimental or informational builders without spamming
people. It is enabled by providing the string 'true'.

'forgiving_optional' and 'closing_optional' won't close the tree if the step is
missing.

'respect_build_status' means to use the buildbot result of the entire build
as an additional way to close the tree. As an example, if a build's closing
steps succeeded but the overall build result was FAILURE, the tree would
close if respect_build_status is set to True. respect_build_status only checks
for FAILURE, not any of the other statuses (including EXCEPTION). A build
status of SUCCESS will not override failing closing or forgiving steps.
respect_build_status is a boolean (true or false in JSON) and defaults to
False.

'close_tree' allows masters or builders to disable the --set-status option
set in gatekeeper_trees.json. In particular, this would be useful for a specific
builder on a tree-closing master which should notify the blamelist about
failures but should not close the tree. close_tree is a boolean (true or false
in JSON) and defaults to True.

Note that if a builder sets something as forgiving_optional which is set as
closing_optional in the master config, this value will be removed from
closing_optional. This allows builders to override master configuration values.

The 'comment' key can be put anywhere and is ignored by the parser.

# Python, not JSON.
{
  'masters': {
    'http://build.chromium.org/p/chromium.win': [
      {
        'sheriff_classes': ['sheriff_win'],
        'tree_notify': ['a_watcher@chromium.org'],
        'categories': ['win_extra'],
        'builders': {
          'XP Tests (1)': {
            'categories': ['win_tests'],
            'closing_optional': ['xp_special_step'],
            'forgiving_optional': ['archive'],
            'tree_notify': ['xp_watchers@chromium.org'],
            'sheriff_classes': ['sheriff_xp'],
          }
        }
      }
    ]
  },
  'categories': {
    'win_tests': {
      'comment': 'this is for all windows testers',
      'closing_optional': ['startup_test'],
      'forgiving_optional': ['boot_windows'],
      'tree_notify': ['win_watchers@chromium.org'],
      'sheriff_classes': ['sheriff_win_test']
    },
    'win_extra': {
      'closing_optional': ['extra_win_step']
      'subject_template': 'windows heads up on %(builder_name)',
    }
  }
}

In this case, XP Tests (1) would be flattened down to:
  closing_optional: ['startup_test', 'win_tests']
  forgiving_optional: ['archive', 'boot_windows']
  tree_notify: ['xp_watchers@chromium.org', 'win_watchers@chromium.org',
                'a_watcher@chromium.org']
  sheriff_classes: ['sheriff_win', 'sheriff_win_test', 'sheriff_xp']

Again, fields are optional and treated as empty lists/sets/strings if not
present.
"""

import copy
import cStringIO
import hashlib
import json
import optparse
import os
import sys


DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# Keys which have defaults besides None or set([]).
DEFAULTS = {
    'status_template': ('Tree is closed (Automatic: "%(unsatisfied)s" on '
                        '"%(builder_name)s" %(blamelist)s)'),
    'subject_template': ('buildbot %(result)s in %(project_name)s on '
                         '%(builder_name)s, revision %(revision)s'),
    'respect_build_status': False,
}


def allowed_keys(test_dict, *keys):
  keys = keys + ('comment',)
  assert all(k in keys for k in test_dict), (
      'not valid: %s; allowed: %s' % (
          ', '.join(set(test_dict.keys()) - set(keys)),
          ', '.join(keys)))



def check_builder_conflicts(special_keys, builder_cats, categories):
  """Checks if the builder has configuration conflicts.

  A conflict occurs if two keys in the builder dictionary (as determined by the
  special_keys dictionary) have duplicate items.

  special_keys: a dictionary mapping key -> conflicting key
  builder_cats: the categories for this particular builder
  categories: the general, known categories.
  """
  special_key_sets = {
      k: set() for k in (special_keys.keys() + special_keys.values())
  }

  for c in builder_cats:
    for key in special_key_sets:
      special_key_sets[key] |= set(categories[c].get(key, []))

  for k, v in special_keys.items():
    union = special_key_sets[k] & special_key_sets[v]
    if union:
      raise ValueError(
        "The builder categories have conflicting entries %s for keys %s "
        "and %s." % (union, k, v))


def load_gatekeeper_config(filename):
  """Loads and verifies config json, constructs builder config dict."""

  # Keys which are allowed in a master or builder section.
  master_keys = ['close_tree',
                 'excluded_builders',
                 'excluded_steps',
                 'forgive_all',
                 'respect_build_status',
                 'sheriff_classes',
                 'status_template',
                 'subject_template',
                 'tree_notify',
  ]

  builder_keys = ['close_tree',
                  'closing_optional',
                  'excluded_builders',
                  'excluded_steps',
                  'forgive_all',
                  'forgiving_optional',
                  'respect_build_status',
                  'sheriff_classes',
                  'status_template',
                  'subject_template',
                  'tree_notify',
  ]

  # These keys are strings instead of sets. Strings can't be merged,
  # so more specific (master -> category -> builder) strings clobber
  # more generic ones.
  strings = ['forgive_all', 'status_template', 'subject_template']

  # Bools also share the 'strings' clobbering logic.
  bools = ['close_tree', 'respect_build_status']

  with open(filename) as f:
    raw_gatekeeper_config = json.load(f)

  allowed_keys(raw_gatekeeper_config, 'categories', 'masters')

  categories = raw_gatekeeper_config.get('categories', {})
  masters = raw_gatekeeper_config.get('masters', {})

  for category in categories.values():
    allowed_keys(category, *builder_keys)

  gatekeeper_config = {}
  for master_url, master_sections in masters.iteritems():
    for master_section in master_sections:
      gatekeeper_config.setdefault(master_url, []).append({})
      allowed_keys(master_section, 'builders', 'categories', *master_keys)

      builders = master_section.get('builders', {})
      for buildername, builder in builders.iteritems():
        allowed_keys(builder, 'categories', *builder_keys)
        for key, item in builder.iteritems():
          if key in strings:
            assert isinstance(item, basestring)
          elif key in bools:
            assert isinstance(item, bool)
          else:
            assert isinstance(item, list)
            assert all(isinstance(elem, basestring) for elem in item)

        gatekeeper_config[master_url][-1].setdefault(buildername, {})
        gatekeeper_builder = gatekeeper_config[master_url][-1][buildername]

        # Populate with specified defaults.
        for k in builder_keys:
          if k in DEFAULTS:
            gatekeeper_builder.setdefault(k, DEFAULTS[k])
          elif k in strings:
            gatekeeper_builder.setdefault(k, '')
          elif k in bools:
            gatekeeper_builder.setdefault(k, True)
          else:
            gatekeeper_builder.setdefault(k, set())

        # Inherit any values from the master.
        for k in master_keys:
          if k in strings or k in bools:
            if k in master_section:
              gatekeeper_builder[k] = master_section[k]
          else:
            gatekeeper_builder[k] |= set(master_section.get(k, []))

        # Inherit any values from the categories.
        for c in master_section.get('categories', []):
          for k in builder_keys:
            if k in strings or k in bools:
              if k in categories[c]:
                gatekeeper_builder[k] = categories[c][k]
            else:
              gatekeeper_builder[k] |= set(categories[c].get(k, []))

        special_keys = {
          'forgiving': 'closing',
          'forgiving_optional': 'closing_optional',
        }

        check_builder_conflicts(
            special_keys, builder.get('categories', []), categories)

        for c in builder.get('categories', []):
          for k in builder_keys:
            if k in strings or k in bools:
              if k in categories[c]:
                gatekeeper_builder[k] = categories[c][k]
            else:
              gatekeeper_builder[k] |= set(categories[c].get(k, []))

        # If we're forgiving something in the builder that we set as
        # closing in the master config, then don't close on it. Builders
        # can override master configurations.
        for key, key_to_modify in special_keys.items():
          if key_to_modify in gatekeeper_builder:
            gatekeeper_builder[key_to_modify] -= set(
                gatekeeper_builder.get(key, []))

        # Add in any builder-specific values.
        for k in builder_keys:
          if k in strings or k in bools:
            if k in builder:
              gatekeeper_builder[k] = builder[k]
          else:
            gatekeeper_builder[k] |= set(builder.get(k, []))

        # Builder postprocessing.
        if gatekeeper_builder['forgive_all'] == 'true':
          gatekeeper_builder['forgiving_optional'] |= gatekeeper_builder[
              'closing_optional']
          gatekeeper_builder['closing_optional'] = set([])


        step_keys = [
            'closing_optional',
            'forgiving_optional',
        ]
        all_steps = reduce(
            lambda x, y:x.union(y),
            [gatekeeper_builder[x] for x in step_keys])

        # Make sure some steps are actually specified.
        if not all_steps and not gatekeeper_builder['respect_build_status']:
          raise ValueError(
            'You must specify at least one of %s or set respect_build_status '
            'for builder "%s" on master %s.' % (
                ','.join(step_keys), buildername, master_url))


  return gatekeeper_config


def load_gatekeeper_tree_config(filename):
  """Loads and verifies tree config json, returned loaded config json."""
  with open(filename) as f:
    trees_config = json.load(f)

  tree_config_keys = ['build-db',
                      'config',
                      'default-from-email',
                      'filter-domain',
                      'gitiles-config',
                      'masters',
                      'open-tree',
                      'password-file',
                      'revision-properties',
                      'set-status',
                      'status-url',
                      'status-user',
                      'track-revisions',
                      'use-project-email-addresses',
                     ]

  for tree_name, tree_config in trees_config.iteritems():
    allowed_keys(tree_config, *tree_config_keys)
    assert isinstance(tree_name, basestring)

    masters = tree_config.get('masters', [])
    assert isinstance(masters, dict)
    assert all(isinstance(master, basestring) for master in masters)
    assert all(isinstance(allowed, list) for allowed in masters.values())

    assert isinstance(tree_config.get('build-db', ''), basestring)
    assert isinstance(tree_config.get('config', ''), basestring)
    assert isinstance(tree_config.get('default-from-email', ''), basestring)
    assert isinstance(tree_config.get('filter-domain', ''), basestring)
    assert isinstance(tree_config.get('gitiles-config', {}), dict)
    assert isinstance(tree_config.get('open-tree', True), bool)
    assert isinstance(tree_config.get('password-file', ''), basestring)
    assert isinstance(tree_config.get('revision-properties', ''), basestring)
    assert isinstance(tree_config.get('set-status', True), bool)
    assert isinstance(tree_config.get('status-url', ''), basestring)
    assert isinstance(tree_config.get('status-user', ''), basestring)
    assert isinstance(tree_config.get('track-revisions', True), bool)
    assert isinstance(
        tree_config.get('use-project-email-addresses', True), bool)

    assert (not tree_config.get('default-from-email') or
            not tree_config.get('use-project-email-address')), (
      'You can only specify one of "default-from-email",'
      ' "use-project-email-address".')

  return trees_config

def gatekeeper_section_hash(gatekeeper_section):
  st = cStringIO.StringIO()
  flatten_to_json(gatekeeper_section, st)
  return hashlib.sha256(st.getvalue()).hexdigest()


def inject_hashes(gatekeeper_config):
  new_config = copy.deepcopy(gatekeeper_config)
  for master in new_config.values():
    for section in master:
      section['section_hash'] = gatekeeper_section_hash(section)
  return new_config


# Python's sets aren't JSON-encodable, so we convert them to lists here.
class SetEncoder(json.JSONEncoder):
  # pylint: disable=E0202
  def default(self, obj):
    if isinstance(obj, set):
      return sorted(list(obj))
    return json.JSONEncoder.default(self, obj)


def flatten_to_json(gatekeeper_config, stream):
  json.dump(gatekeeper_config, stream, cls=SetEncoder, sort_keys=True)


def main():
  prog_desc = 'Reads gatekeeper.json and emits a flattened config.'
  usage = '%prog [options]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--json', default=os.path.join(DATA_DIR, 'gatekeeper.json'),
                    help='location of gatekeeper configuration file')
  parser.add_option('--no-hashes', action='store_true',
                    help='don\'t insert gatekeeper section hashes')
  options, _ = parser.parse_args()

  gatekeeper_config = load_gatekeeper_config(options.json)

  if not options.no_hashes:
    gatekeeper_config = inject_hashes(gatekeeper_config)

  flatten_to_json(gatekeeper_config, sys.stdout)
  print

  return 0


if __name__ == '__main__':
  sys.exit(main())
