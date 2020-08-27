# iOS recipes

The recipes are the scripts which run on the iOS bots. This doc assumes you've
read the [docs] in [chromium/src] for details about how the iOS bots work and
that you know what [recipes] are. You may also want to read the [recipe module]
docs for iOS.

[TOC]

## Recipes

### unified\_builder\_tester.py

This is the recipe which runs on most iOS bots which need to do their own build
and test (even if they are not configured to run any tests). It simply checks
out Chromium, compiles for iOS, uploads any compilation outputs that are
configured to be uploaded, and runs tests if any exist. A successful build is
one in which no step fails.

This recipe is used on [chromium.mac].

### try.py

This is the recipe which runs on iOS try bots. It ensures a try bot's
configuration precisely mirrors that of a [chromium.mac] bot. It uses the
[analyzer] to reduce cycle time and retries compilation without the patch if it
fails with the patch in order to indicate whether or not tip of tree itself is
failing.

This recipe is used on [tryserver.chromium.mac].

[analyzer]: https://chromium.googlesource.com/chromium/src/+/master/tools/mb
[chromium.mac]: https://build.chromium.org/p/chromium.mac
[chromium/src]: https://chromium.googlesource.com/chromium/src
[docs]: https://chromium.googlesource.com/chromium/src/+/master/docs/ios_infra.md
[recipe module]: ../../recipe_modules/ios/README.md
[recipes]: https://chromium.googlesource.com/infra/infra/+/HEAD/doc/users/recipes.md
[tryserver.chromium.mac]: https://build.chromium.org/p/tryserver.chromium.mac/waterfall
