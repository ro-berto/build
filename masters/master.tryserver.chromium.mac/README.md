# tryserver.chromium.mac

A try bot is used to test proposed patches which are not yet committed. A subset
of try bots form the [commit queue], these try bots run on every patch before it
is committed. Not every try bot needs to be part of the commit queue, some are
optional. An optional try bot can be manually triggered by a user who wants some
additional test coverage for their patch. Optional try bots will not be
triggered by the commit queue, and failures on optional try bots will not
prevent a patch from being committed.

Request [try job access] in order to trigger try jobs against your patch.

[TOC]

## Adding a non-CQ iOS try bot

This section assumes you've read the [docs] in [chromium/src] for details about
how the iOS try bots work and how to make common changes to things like
`gn_args` or the tests being run. The following instructions are for the case
where you actually need to add a brand new try bot.

First you will need to write a config for your try bot. The configs can be found
in [src/ios/build/bots/chromium.mac]. All iOS try bots on
[tryserver.chromium.mac] mirror iOS builders on [chromium.mac], so you need to
create a config for a chromium.mac bot even if you don't actually plan on
creating a new builder on chromium.mac.

Once the config is created, you will need to add the builder to [master.cfg] and
[slaves.cfg]. In master.cfg, find the `b_ios_*` block and copy/paste. Leave the
`factory` property as is, but change the `name`. Remember, the name of the try
bot here must match the name of the config from the previous step. Once you've
created the builder definition, add it to `c['builders']`. In slaves.cfg, find
the `ios` function and add an entry to the `slave_map`. The key should be the
name of your new bot and the value should be a list of slaves that will back the
bot.

In order to get slaves, Google employees should file a ticket at
[go/infrasys-bug] requesting 1 or 2 Macs for tryserver.chromium.mac. You will
need a lot more if you plan to make your try bot part of the commit queue.

### Promoting a non-CQ iOS try bot to the commit queue

After adding a non-CQ iOS try bot, ensure you have enough capacity. Ensure you
have at least as many slaves as the existing iOS CQ try bots. You can find the
list of current CQ try bots in [src/infra/config/cq.cfg]. Find the entry for the
bucket named `master.tryserver.chromium.mac`.

Once you have enough capacity, enable a CQ experiment by adding a `builders`
entry with an `experiment_percentage` field in addition to `name`. Start with a
small experiment, like `10`%. A CQ experiment will cause your try bot to be
triggered on the specified percentage of CQ requests. Failures on an
experimental try bot will not block the patch from being committed. Once your
try bot is seeing a lot of successful executions, ramp up the experiment. You
must enable a `100`% experiment to properly load test your try bot before
promoting it to the commit queue. To finally promote a `100`% experiment to the
CQ, remove the `experiment_percentage`.

At this point you should also have a matching builder on [chromium.mac] with the
same name as your try bot. See the [chromium.mac docs] for details.

[chromium.mac]: https://build.chromium.org/p/chromium.mac
[chromium.mac docs]: ../master.chromium.mac/README.md
[chromium/src]: https://chromium.googlesource.com/chromium/src
[commit queue]: https://dev.chromium.org/developers/testing/commit-queue
[docs]: https://chromium.googlesource.com/chromium/src/+/master/docs/ios_infra.md
[go/infrasys-bug]: https://goto.google.com/infrasys-bug
[master.cfg]: ./master.cfg
[slaves.cfg]: ./slaves.cfg
[src/infra/config/cq.cfg]: https://chromium.googlesource.com/chromium/src/+/master/infra/config/cq.cfg
[src/ios/build/bots/chromium.mac]: https://chromium.googlesource.com/chromium/src/+/master/ios/build/bots/chromium.mac
[try job access]: https://www.chromium.org/getting-involved/become-a-committer#TOC-Try-job-access
[tryserver.chromium.mac]: https://build.chromium.org/p/tryserver.chromium.mac/waterfall
