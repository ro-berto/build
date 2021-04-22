# chromium_tests_builder_config

This module provides the types and methods for other modules to get the
per-builder config object that `chromium_tests` uses for the majority of its
operations.

## Public interface

In addition to the API object that is injected into dependent APIs, the
following types and constants are available to be imported:

* `BuilderConfig` - The configuration information for a running builder. This
  may incorporate the BuilderSpec for multiple builders since try builders may
  mirror multiple builders and/or testers. The *chromium_tests* recipe module
  requires a `BuilderConfig` for nearly all of its operations.
* `BuilderSpec` - The configuration information for a single builder.
  * `COMPILE_AND_TEST`, `TEST`, `PROVIDE_TEST_SPEC` - Constants that the
    `execution_mode` field of BuilderSpec can be set to.
* `BuilderDatabase` - A mapping enabling looking up the `BuilderSpec` for a
  builder given its `BuilderId`.
* `TryMirror` - The configuration information specifying the builder and
  an optional tester that a try builder mirrors. Use when constructing a
  `TrySpec`.
* `TrySpec` - The configuration information specifying one or more mirrors
  and optional configuration that controls try-specific behavior.
  * `COMPILE_AND_TEST`, `COMPILE` - Constants that the `execution_mode` field
    of `TrySpec` can be set to.
* `TryDatabase` - A mapping enabling looking up the `TrySpec` for a builder
  given its `BuilderId`.

## How to get a BuilderConfig

There are 2 ways to get a `BuilderConfig`:

* `lookup_builder`
* `BuilderConfig.create`

The `lookup_builder` method should be preferred in almost all cases. It
looks up the currently-running builder in statically defined
`TryDatabase` and `BuilderDatabase` instances containing the builders
for the *chromium* project. It returns the `BuilderId` and
`BuilderConfig` for the builder. A `BuilderId` can be passed in to look
up a builder other than the currently-running builder. Both databases
can be overridden if the lookup is for builders in another project.

There are some situations where a `BuilderConfig` for pre-determined builders is
not appropriate (e.g. findit will create mirrors for builder-tester pairs that
don't necessarily correspond to any defined try builders). In these cases, the
`BuilderConfig` should be manually created using the `create` factory method.
When manually creating a `BuilderConfig`, the `TrySpec` that defines the mirrors
and the try-specific behavior will also need to be created manually.
