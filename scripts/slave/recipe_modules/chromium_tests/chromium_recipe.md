# Chromium Recipes: Reference Doc

[TOC]

## I just want to....

This section covers common tasks for chromium developers. If you want a more
full background on the chromium recipes, go to the [Background](#Background)
section.

### Create a New Builder

We're going to walkthrough an example of wanting to add a builder to the
`chromium.linux` master.

*** note
Make sure to read the [following](#Getting-your-bot-on-the-main-waterfall)
section once you have read this section.
***

1. Add the builder configs to the corresponding master file in the
  `chromium_tests` recipe module: [`chromium_tests/chromium_linux.py`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/scripts/slave/recipe_modules/chromium_tests/chromium_linux.py)
   .
1. Add the builder to [`src/testing/buildbot/chromium.linux.json`](https://chromium.googlesource.com/chromium/src/+/master/testing/buildbot/chromium.linux.json)
   .
1. Add the new builder to the buildbot master config.
    1. If the builder is not using [`builders.pyl`](https://chromium.googlesource.com/infra/infra/+/master/doc/users/services/buildbot/builders.pyl.md)
      , then you need to declare the new builder in [`master.cfg`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/masters/master.chromium.linux/master.cfg)
      , assign it a recipe name and a slave pool (`slaves.cfg`).
    2. If the builder is using `builders.pyl`, then look at the [docs](https://chromium.googlesource.com/infra/infra/+/master/doc/users/services/buildbot/builders.pyl.md)
      and modify the corresponding file.
1. Request a master restart [here](https://chromium.googlesource.com/infra/infra/+/master/doc/users/contacting_troopers.md)
   .
1. Add the new builder to the console for the desired master in `luci-milo.cfg`
  and `luci-milo-dev.cfg` in the
  [ `infra/config` branch of `chromium/src`](https://chromium.googlesource.com/chromium/src/+/infra/config)
  . Existing entries in those configurations should be good examples. Your new
  entry should minimally include:
    1. `name`: a string matching either `buildbot/$MASTER_NAME/$BUILDER_NAME`
      (for buildbot bots) or `buildbucket/$BUCKET_NAME/$BUILDER_NAME` (for LUCI
      bots).
    1. `category`: a string containing one or more categories separated by `|`.

        **Note**: the order of builders within a console's configuration
        determines the order in which the builders appear on that console, and
        adjacent builders that share one or more categories will have those
        categories merged in the UI. As such, it's best to list your new builder
        next to other builders that share its categories.

    1. `short_name`: a string containing at most three characters that will be
      used to represent the builder on the console.

You also need to think about provisioning hardware for the new slaves. File a
ticket with the label `Infra-Labs` (http://go/infrasys-bug is a good place to
start) with information about the hardware you need, and someone on the labs
team will take a look at it, and help you get the hardware you need.

#### Getting your bot on the main waterfall

Generally, you're going to want to add a new builder to our FYI waterfall first,
before adding it to the main waterfall. This is so that we can monitor it, and
make sure it's consistently and reliably green, before making it a tree closing
bot. So, before you add the bot to `chromium.linux`, add it to the
`chromium.fyi` master. So, follow the instructions above, but instead of adding
the builder to the `chromium.linux` master, add it to the `chromium.fyi` master.

Once everything is tested and the builder works, you *must* get chrome eng
review to sign off on the addition to the main waterfall. Once you have that
approval move the waterfall builder config to the appropriate main waterfall
master (e.g. `chromium.linux`)

* Update its chromium recipe module config (e.g. [`chromium_linux.py`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/scripts/slave/recipe_modules/chromium_tests/chromium_linux.py)
  )
* Update master config (e.g. [`master.chromium.linux/master_cfg.py`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/masters/master.chromium.linux/master.cfg)
  ).
* Request a master restart [here](https://chromium.googlesource.com/infra/infra/+/master/doc/users/contacting_troopers.md)
   .

### Create a New Trybot

Every new main waterfall bot *must* have corresponding trybot coverage. In
addition, you can request a new trybot if you have a configuration you are
interested in testing.

`chromium` recipe trybots currently are configured by specifying the main
waterfall configuration they are supposed to emulate. This information is stored
in the [`chromium_tests/trybots.py`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/scripts/slave/recipe_modules/chromium_tests/trybots.py)
file. So, for example, the `linux_android_rel_ng` trybot is
configured as follows:

      ...
      'linux_android_rel_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder',
        'tester': 'Android Tests',
      },
      ...

For example, suppose we want to add a builder named `new_fancy_android_device`
to `tryserver.chromium.android`, which is a copy of the builder named
`fancy_android_device` on the main `chromium.android` waterfall.
We would do the following

1. Add the builder configuration of

        ...
        'new_fancy_android_device': {
          'mastername': 'chromium.android',
          'buildername': 'fancy_android_device',
        },
        ...

2. Add the new trybot to the corresponding tryserver master. In this case,
   that's [`tryserver.chromium.android`](https://chromium.googlesource.com/chromium/tools/build.git/+/master/masters/master.tryserver.chromium.android/)
   .
3. Request a master restart [here](https://chromium.googlesource.com/infra/infra/+/master/doc/users/contacting_troopers.md)
   .

You can then schedule tryjobs on the bot using `git cl try -b
new_fancy_android_device`.

#### Getting your trybot on the CQ.

Coming soon...

For now, email [chrome-infra@](mailto:chrome-infra@google.com)

### Add a compile target

First, please consider why you're doing this. If it's needed for a test,
then let the test declare needed its compile targets (this is part of the Test
interface from [`steps.py`](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipe_modules/chromium_tests/steps.py)
, and when you add this test to a builder the right targets will
automatically compile.

The technical way would be to modify the `compile_targets` key in your bot
config. For example, in [`scripts/slave/recipe_modules/chromium_tests/chromium_linux.py`](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipe_modules/chromium_tests/chromium_linux.py)
, to add the compile target `your_target_here`:

    'Linux Builder': {
      ...
      'compile_targets': [
        ...
        'your_target_here',
      ],
      ...
    },

*** note
Adding this allows you to confirm that it works with recipe expectations.
***

### Add a new gtest-based test to a bot

Add it to the JSON test spec. Example ([`src/testing/buildbot/chromium.linux.json`](https://code.google.com/p/chromium/codesearch#chromium/src/testing/buildbot/chromium.linux.json)):

    "Linux Builder": {
      "gtest_tests": [
        {
          "test": "base_unittests"
        },
      ...
      ]
    }

Changes to the JSON file can be tested on the trybots, and you can verify that
they take effect and build still passes.

### Add a new non gtest-based test
Generally, look at [steps.py](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipe_modules/chromium_tests/steps.py)
, and either use an existing class there, or add a new one.

## Background
Chromium tests are currently run on buildbot, and are organized by builders.
A builder, in buildbot’s terminology, is a sequence of steps
(typically, individual commands) executed by a slave, and controlled by
the central master process.

Since such tightly controlled system is hard to maintain at scale, and requires
human attention and frequent downtimes for master restarts on every update,
Chrome Infra introduced [recipes](https://chromium.googlesource.com/external/github.com/luci/recipes-py/+/master/doc/user_guide.md).

A recipe is a single command executed as a single buildbot builder step
(called steps), which dynamically generates all the other steps. This moves the
control over steps from the master to the slaves, allows for dynamic creation of
steps at runtime, and, most importantly, eliminates the need for master restarts
when a builder configuration changes.

Recipe-based builders have a very generic configuration on the buildbot master,
and all the other specific configs live in recipes and recipe modules
(more on that later).

Additional requirement is to keep continuous integration (aka waterfall)
builders in sync with the tryserver (commit queue) builders.

## Life of a CL
To give recipes some context, let’s consider what a typical Chromium CL goes
through, from its inception to landing into the repository.

1. A developer clones Chromium repo locally, and makes a change.
1. The change is uploaded to Rietveld at http://codereview.chromium.org.
1. The developer may run manual try jobs (git cl try).
1. The change goes through the approval process, and eventually receives an LGTM.
1. The change is submitted to Commit Queue (CQ), which:
  1. Checks for a valid LGTM
  1. Runs all required try jobs - a subset of the equivalent waterfall jobs
  1. If all jobs succeed, commits the change to the repository.
1. Continuous Integration masters (waterfall) run the complete set of jobs on
the new revision (often batched with other revisions).
1. If all tests pass, the revision stays. Otherwise it may be reverted.

On a typical day, Chromium CQ may check up to 400 CLs, and land over 300 of
them. At peak times, CQ may land as many as 30 CLs every hour.

## Constraints and Requirements
In order for the system to function efficiently and reliably, several important
constraints are enforced.

* Speed: Each builder must be fast, to ensure short cycle time and efficient development.
  * Heavy tests are run in parallel using Swarming infrastructure
  * On the waterfall, compile and tests are split into two separate builders,
  so they can run in parallel, reducing the latency between each verified revision.
* Accuracy: CQ must guarantee correctness of CLs with high accuracy.
  * For capacity reasons, we cannot run tests on every single architecture in
  CQ, so only the most important subset is run.
  * It is very important for CQ jobs to run exactly the same steps (compile and
  test) as in the waterfall. Any discrepancy often leads to missed bugs and a
  broken tree.
* Reliability: CQ should land correct CLs, and reject incorrect ones.
  * In practice, false rejections will happen, but it is important to keep them
  to a minimum.
  * For that, CQ employs a sophisticated system of retries, and various
  heuristics determining when it is OK to give up on a CL.

## Implementation

Each of the requirements above needs a fairly complex and highly tuned system
to perform each step of the verification. Therefore, Chrome Infra provides a
common library of recipes implementing all of these requirements, and expects
developers to use it with minimum configuration on their part.

Currently, the following components are involved in configuring a builder:

### master.cfg/builders.pyl

  c['builders'] = `<list of builder specs>`

Each waterfall builder is specified using a dict like this
(example from [master.chromium.mac/master_mac_cfg.py](https://code.google.com/p/chromium/codesearch#chromium/build/masters/master.chromium.mac/master_mac_cfg.py&sq=package:chromium&l=55)
):

``` python
{
  'name': 'mac-rel'
  'factory': m_annotator.BaseFactory(
      'chromium',     # name of the recipe
      factory_properties=None,  # optional factory properties
      triggers=[<list of triggered builders>]),
  'notify_on_missing': True,
  'category': '3mac',
}
```

Note the name of the recipe: `chromium`. Together with the name of the master
and builder, this fully determines the builder configuration in the master. All
the other details (specific steps) are configured in the recipe and recipe
modules.

Similarly, a tryserver builder is specified using `chromium_trybot` recipe (from [master.tryserver.chromium.mac/master.cfg](https://code.google.com/p/chromium/codesearch#chromium/build/masters/master.tryserver.chromium.mac/master.cfg&sq=package:chromium)
):

``` python
{
  'name': 'mac-rel',
  'factory': m_annotator.BaseFactory('chromium_trybot'),
  # Share build directory [...] to save space.
  'slavebuilddir': 'mac'
}
```

Again, the recipe, master and builder names fully determine the configuration
on the master side. Changing how the builder is defined can now be done without
restarting the master.

If the master is configured using `builders.pyl`, then the above description
does not apply. Please see [this](https://chromium.googlesource.com/infra/infra/+/HEAD/doc/users/services/buildbot/builders.pyl.md)
document instead for a description of how `builders.pyl` works.

### chromium.py: the main [waterfall] recipe

Path: [build/scripts/slave/recipes/chromium.py](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipes/chromium.py)

This is a very short “glue” recipe which reads the detailed configurations,
prepares the checkout, compiles the targets, and runs the tests. All the
specifics are done in a shared recipe module `chromium_tests`.

### chromium_trybot.py: the tryserver recipe, and trybot configs

Path: [build/scripts/slave/recipes/chromium_trybot.py ](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipes/chromium_trybot.py)

Each trybot (builder) is defined in terms of the corresponding main waterfall
builders. This config file is in
[build/scripts/slave/recipe_modules/chromium_tests/trybots.py](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipe_modules/chromium_tests/trybots.py&l=359)

```
'mac_chromium_rel_ng': {
    'mastername': 'chromium.mac',
    'buildername': 'Mac Builder',
    'tester': 'Mac10.8 Tests',
}
```

The recipe takes the corresponding compile and test configs, and adds the
tryserver specific logic, such as applying a patch from a CL, retrying compile
and failed tests without the patch, and failing / succeeding the build
appropriately.

In particular, if compile fails both with and without a patch, the entire job
fails. However, if a small portion of tests fails in the same way with and
without a patch, the job succeeds (the failures are assumed not because of the
CL, and are tolerable to continue the development).

This implements the requirement that try bots (CQ) are always in sync with the
waterfall builders. This recipe also uses the best proven retry strategies, thus
keeping CQ jobs robust and accurate.

### chromium_tests module: implements actual steps

Path: [build/scripts/slave/recipe_modules/chromium_tests/api.py](https://code.google.com/p/chromium/codesearch#chromium/build/scripts/slave/recipe_modules/chromium/api.py)

Implements methods like `configure_build`, `prepare_checkout`, compile, etc.
that take configuration parameters and actually run the steps.

### src/testing/buildbot/*.json: per-master configs: targets & tests

Example config: [src/testing/buildbot/chromium.mac.json](https://code.google.com/p/chromium/codesearch#chromium/src/testing/buildbot/chromium.mac.json&sq=package:chromium)

These configs live in the project repo, and define additional compile targets and specific tests to run on each builder.
