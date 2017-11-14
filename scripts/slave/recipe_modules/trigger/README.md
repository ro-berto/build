# trigger recipe module

Trigger recipe allows you to trigger new builds and pass arbitrary properties.

**WARNING: Deprecated.
You should use
[`recipe_engine/buildbucket`](https://chromium.googlesource.com/infra/luci/recipes-py/+/6b01324b35c2a7046b67292f7be0cd827f7fd94c) instead.**

## Examples
Basic:

    api.trigger({
        'builder_name': 'HelloWorld',
        'properties': {
            'my_prop': 123,
        },
    })

This triggers a new build on HelloWorld builder with "my_prop" build property
set to 123.

You can trigger multiple builds in one steps:

    api.trigger(
        {'builder_name': 'Release'},
        {'builder_name': 'Debug'},
    )

You can trigger a build on a different buildbot master:

    api.trigger({
        'builder_name': 'Release',
        'bucket': 'master.tryserver.chromium.linux', # specify master name here.
    })

This uses [buildbucket](../../../master/buildbucket) underneath and must be
configured.

Specify different Buildbot changes:

    api.trigger({
        'builder_name': 'Release',
        'buildbot_changes': [{
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

**WARNING**: on buildbot, this requires certain configuration on the
master prior first use. See more below.

## Master configuration for buildbucket triggering

*   if you don't use builders.pyl, in master.cfg of the source master
    `ActiveMaster` parameter MUST be passed to `AnnotationFactory` for the
    builder that is triggering a build.
*   source master's master_site_config.py MUST have
    `service_account_(file|path)` set
*   the source master's service account must have permissions to schedule builds
    in the target master's bucket. If they use same service account, it is fine.
*   the target master MUST be polling buildbucket
