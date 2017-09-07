#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in chromium_utils.py."""

import os
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import chromium_utils


class FakeParser(object):
  def __init__(self):
    self.lines = []

  def ProcessLine(self, line):
    self.lines.append(line)


class FakeFilterObj(object):
  def __init__(self):
    self.lines = []

  def FilterLine(self, line):
    self.lines.append(line)

  # this is called when there is data without a trailing newline
  def FilterDone(self, line):
    self.lines.append(line)


def synthesizeCmd(args):
  basecmd = [sys.executable, '-c']
  basecmd.extend(args)
  return basecmd


class TestRunCommand(unittest.TestCase):

  def testRunCommandPlain(self):
    mycmd = synthesizeCmd(['exit()'])
    self.assertEqual(0, chromium_utils.RunCommand(mycmd, print_cmd=False))

  def testRunCommandParser(self):
    mycmd = synthesizeCmd(['print "1\\n2"'])
    parser = FakeParser()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       parser_func=parser.ProcessLine)
    self.assertEqual(0, retval)
    self.assertEqual(['1', '2', ''], parser.lines)

  def testRunCommandFilter(self):
    mycmd = synthesizeCmd(['print "1\\n2"'])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['1\n', '2\n'], filter_obj.lines)

  def testRunCommandFilterEndline(self):
    mycmd = synthesizeCmd(['import sys; sys.stdout.write("test")'])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['test'], filter_obj.lines)

  def testRunCommandPipesParser(self):
    firstcmd = synthesizeCmd(['print "1\\n2"'])

    oneliner = "import sys; [sys.stdout.write(l.strip()+'1\\n') for l in "
    oneliner += "sys.stdin.readlines()]"
    secondcmd = synthesizeCmd([oneliner])
    parser = FakeParser()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       parser_func=parser.ProcessLine)
    self.assertEqual(0, retval)
    self.assertEqual(['11', '21', ''], parser.lines)

  def testRunCommandPipesFilter(self):
    firstcmd = synthesizeCmd(['print "1\\n2"'])

    oneliner = "import sys; [sys.stdout.write(l.strip()+'1\\n') for l in "
    oneliner += "sys.stdin.readlines()]"
    secondcmd = synthesizeCmd([oneliner])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['11\n', '21\n'], filter_obj.lines)

  def testRunCommandPipesFailure(self):
    firstcmd = synthesizeCmd(['print "1"'])

    secondcmd = synthesizeCmd(["exit(1)"])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       filter_obj=filter_obj)
    self.assertEqual(1, retval)


SAMPLE_BUILDERS_PY = """\
{
  "master_base_class": "_FakeBaseMaster",
  "master_classname": "_FakeMaster",
  "master_port": 20999,
  "master_port_alt": 40999,
  "bot_port": 30999,
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "recipe": "test_recipe",
      "properties": {
        "config": "Release"
      },
      "scheduler": "test_repo",
      "os":  "linux",
      "version": "precise",
      "bot": "vm9999-m1",
      "botbuilddir": "test"
    }
  },
  "schedulers": {
    "test_repo": {
      "type": "git_poller",
      "git_repo_url": "https://chromium.googlesource.com/test/test.git",
    },
  },
}
"""


class GetBotsFromBuilders(unittest.TestCase):
  def test_normal(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_BUILDERS_PY)
      fp.close()

      bots = chromium_utils.GetBotsFromBuildersFile(fp.name)
      self.assertEqual([{
          'hostname': 'vm9999-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
      }], bots)
    finally:
      os.remove(fp.name)

  def test_range(self):
    # This tests that bash-style range expansion works for hostnames.
    # The interval should be fully closed, i.e., x..y includes both x and y.
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_BUILDERS_PY.replace('"bot": "vm9999-m1"',
                                          '"bots": "vm{1..3}-m1"'))
      fp.close()
      bots = chromium_utils.GetBotsFromBuildersFile(fp.name)
      self.assertEqual([
        {
          'hostname': 'vm1-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        },
        {
          'hostname': 'vm2-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        },
        {
          'hostname': 'vm3-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        }], bots)
    finally:
      os.remove(fp.name)

  def test_hostname_syntax_and_expansion(self):
    expand = chromium_utils.ExpandBotsEntry
    self.assertEqual(['vm1'], expand('vm1'))
    self.assertEqual(['vm1-c1', 'vm12-c1'], expand('vm{1,12}-c1'))
    self.assertEqual(['vm11-c1', 'vm12-c1'], expand('vm{11..12}-c1'))

    # These have mismatched braces.
    self.assertRaises(ValueError, expand, 'vm{')
    self.assertRaises(ValueError, expand, 'vm{{')
    self.assertRaises(ValueError, expand, 'vm}{')
    self.assertRaises(ValueError, expand, 'vm{{}')

    # Only one set of braces is allowed.
    self.assertRaises(ValueError, expand, 'vm{1,2}{3,4}')

    # An empty set of braces is not allowed.
    self.assertRaises(ValueError, expand, 'vm{}')

    # Nested braces are not allowed.
    self.assertRaises(ValueError, expand, 'vm{{{}}}')

    # The start must be smaller than the end.
    self.assertRaises(ValueError, expand, 'vm{3..2}')

    # Mixing both ranges and lists is not allowed.
    self.assertRaises(ValueError, expand, 'vm{2..3,4}')

    # Spaces are not allowed.
    self.assertRaises(ValueError, expand, 'vm{2 ,4}')

  def test_normalize_builders_with_mixins(self):
    builders = {
      'mixins': {
        'main_pool': {'os': 'linux', 'version': 'precise', 'bots': 'vm{1..4}'},
        'foo_recipe': {'recipe': 'foo'},
        'bar_recipe': {'recipe': 'bar'},
        'special_pool': {'bot': 'vm10'},
      },
      'builders': {
        'foo': {
          'scheduler': None,
          'mixins': ['foo_recipe', 'main_pool'],
        },
        'bar': {
          'scheduler': None,
          'mixins': ['bar_recipe', 'main_pool'],
        },
        'special_builder': {
          # This is a dumb example (you shouldn't override values), but it
          # is legal to do so.
          'recipe': 'test_recipe',
          'scheduler': None,
          'mixins': ['main_pool', 'special_pool'],
        }
      },
    }
    errors = []
    chromium_utils.NormalizeBuilders(builders, errors)
    self.assertEqual(errors, [])
    self.assertEqual(builders['bot_pools']['special_builder']['bots'],
                     ['vm10'])

  def assertBadBuilders(self, builders):
    errors = []
    chromium_utils.NormalizeBuilders(builders, errors)
    self.assertNotEqual(errors, [])

  def test_submixins(self):
    errors = []
    builders = {
      'mixins': {
        'precise': {
          'mixins': ['linux'],
          'version': 'precise',
        },
        'trusty': {
          'mixins': ['linux'],
          'version': 'trusty',
        },
        'linux': {
          'os': 'linux',
        },
      },
      'builders': {
        'trusty': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'mixins': ['trusty'],
          'bot': 'vm1',
        },
      },
    }
    chromium_utils.NormalizeBuilders(builders, errors)
    self.assertEqual(errors, [])
    self.assertEqual(builders['builders']['trusty']['os'], 'linux')
    self.assertEqual(builders['builders']['trusty']['version'], 'trusty')

  def test_bot_list(self):
    errors = []
    builders = {
      'builders': {
        'trusty': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'os': 'linux',
          'version': 'precise',
          'bots': ['vm1', 'vm{10..12}'],
        },
      },
    }
    chromium_utils.NormalizeBuilders(builders, errors)
    self.assertEqual(errors, [])
    self.assertEqual(['vm1', 'vm10', 'vm11', 'vm12'],
                     chromium_utils.GetBotNamesForBuilder(builders, 'trusty'))

  def test_builder_must_have_bots(self):
    self.assertBadBuilders({
      'builders': {
        'no_bots': {},
      },
    })

  def test_too_many_bot_fields(self):
    self.assertBadBuilders({
      'builders': {
        'too_many_bot_fields': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'os': 'linux',
          'version': 'precise',
          'bot': 'vm1',
          'bots': 'vm{2..3}'
        }
      },
    })

  def test_builder_and_bot_pool_with_same_name(self):
    self.assertBadBuilders({
      'builders': {
        'linux': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'os': 'linux',
          'version': 'precise',
          'bot': 'vm1',
        }
      },
      'bot_pools': {
        'linux': {
          'os': 'linux',
          'version': 'precise',
          'bots': 'vm{1..10}',
        },
      },
    })

  def test_missing_mixin(self):
    self.assertBadBuilders({
      'mixins': {},
      'builders': {
        'missing_mixin_builder': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'mixins': ['missing'],
          'os': 'linux',
          'version': 'precise',
          'bot': 'vm1',
        },
      },
    })

  def test_missing_bot_pool(self):
    self.assertBadBuilders({
      'builders': {
        'missing_bot_pool': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'bot_pool': 'missing',
        },
      },
    })

  def test_no_mixins_in_builder_defaults(self):
    self.assertBadBuilders({
      'builder_defaults': {
        'mixins': ['illegal_mixin'],
        'os': 'linux',
      },
      'builders': {
        'foo': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'bot': 'vm1',
        },
      },
    })

  def test_bad_bot_string(self):
    self.assertBadBuilders({
      'builders': {
        'bad_bot_string': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'bot': 'vm{1..3}',
        },
      },
    })

  def test_bot_pool_missing_os(self):
    errors = []
    builders = {
      'builders': {
        'sample': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'bot_pool': 'main',
        },
      },
      'bot_pools': {
        'main': {'bots': 'vm{1..3}'},
      },
    }
    chromium_utils.NormalizeBotPools(builders, errors)
    self.assertNotEqual(errors, [])

  def test_no_recipe(self):
    self.assertBadBuilders({
      'builders': {
        'missing_recipe': {
          'scheduler': None,
          'os': 'linux',
          'version': 'trusty',
          'bot': 'vm1',
        },
      },
    })

  def test_no_remote_run_repository(self):
    self.assertBadBuilders({
      'builders': {
        'missing_remote_run_repository': {
          'recipe': 'test_recipe',
          'scheduler': None,
          'use_remote_run': True,
          'os': 'linux',
          'version': 'trusty',
          'bot': 'vm1',
        },
      },
    })

  def test_no_scheduler(self):
    self.assertBadBuilders({
      'builders': {
        'missing_scheduler': {
          'recipe': 'test_recipe',
          'os': 'linux',
          'version': 'trusty',
          'bot': 'vm1',
        },
      },
    })


if __name__ == '__main__':
  unittest.main()
