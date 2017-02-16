# chromium.mac

A buildbot builder (or "bot") is used to test newly committed patches.
[chromium.mac] is the main waterfall for Mac and iOS.

[TOC]

## Adding an iOS bot

This section assumes you've read the [docs] in [chromium/src] for details about
how the iOS bots work and how to make common changes to things like
`gn_args` or the tests being run. The following instructions are for the case
where you actually need to add a brand new bot.

First you will need to write a config for your bot. The configs can be found
in [src/ios/build/bots/chromium.mac].

Once the config is created, you will need to add the builder to
[master\_ios\_cfg.py] and [slaves.cfg]. In master\_ios\_cfg.py, add your bot to
the `SingleBranchScheduler` and to `specs`. Remember, the name of the bot here
must match the name of the config from the previous step. In slaves.cfg, add
your bot to `slaves` by copy/pasting a dict for one of the other iOS bots and
changing the `builder` to your bot's name and `hostname` to the slave it will
run on.

In order to get slaves, Google employees should file a ticket at
[go/infrasys-bug] requesting 1 Mac for chromium.mac.

It's good practice to add a try bot equivalent to any bot you add here. Because
these bots are sheriffed, a committed patch that fails your new bot may end up
being reverted. Providing a try bot ensures that developers have the ability to
test their patch against your bot before committing, reducing the likelihood
that their patch will be unexpectedly reverted by a sheriff.

See the [tryserver.chromium.mac docs] for details.

[chromium.mac]: https://build.chromium.org/p/chromium.mac
[chromium/src]: https://chromium.googlesource.com/chromium/src
[docs]: https://chromium.googlesource.com/chromium/src/+/master/docs/ios_infra.md
[go/infrasys-bug]: https://goto.google.com/infrasys-bug
[master\_ios\_cfg.py]: ./master_ios_cfg.py
[slaves.cfg]: ./slaves.cfg
[src/ios/build/bots/chromium.mac]: https://chromium.googlesource.com/chromium/src/+/master/ios/build/bots/chromium.mac
[tryserver.chromium.mac docs]: ../master.tryserver.chromium.mac/README.md
