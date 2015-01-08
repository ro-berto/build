buildbucket module can be used to connect a Buildbot master to buildbucket.

## Configuration

Configuring a buildbot master is straightforward:

    from master import buildbucket

    buildbucket.setup(
        c,
        build_namespaces=['chromium'],
        service_json_key_filename='my_secret_key.json',
    )

* build_namespaces (list of str): list of build namespaces to peek and build.
* service_json_key_filename (str): path to a json key file, such as
  [cr-buildbucket-dev-9c9efb83ec4b.json](cr-buildbucket-dev-9c9efb83ec4b.json).
  A production json key can be obtained by
  [filing ticket](buildbucket-service-account-bug).

### Playing with build bucket
When testing, ```'cr-buildbucket-dev.appspot.com'``` development server can be
specified in ```buildbucket_hostname``` parameter.
[cr-buildbucket-dev-9c9efb83ec4b.json](cr-buildbucket-dev-9c9efb83ec4b.json) can
be used to authenticate to cr-buildbucket-dev.

## How it works in the nutshell
Every ten seconds a Buildbot master checks if it has capacity to run more
builds. If it does, it [peeks](api_peek) builds in the specified build
namespaces. For each valid peeked build master checks if the builder has
capacity to run a build right away. If master decides to run a peeked build, it
leases it. If leased successfully, master schedules a build.

During build lifetime master reports build
status back to buildbucket. When the build starts, master calls
[start](api_start) API, and when build finishes, it calls [succeed](api_succeed)
or [fail](api_fail) APIs. Buildbot master subscribes to build ETA update and
calls [heartbeat](api_heartbeat) API every 10 seconds. If master discovers that
a build lease expired, it stops the build.

### Parameters
Buildbot-buildbucket integration supports the following build parameters:

* builder_name (str): required name of a builder to trigger. If builder is not
  found, the build is skipped.
* properties (dict): arbitrary build properties. Property 'buildbucket' is
  reserved.
* changes (list of dict): list of changes to be associated with the build, used
  to create Buildbot changes for builds.
  Each change is a dict with keys:
    * id (str): a unique identity of the change.
      If id and revision are specified, buildbot master will search for an
      existing buildbot change prior creating a new one. Also see implementation
      details below.
    * revision (str): change revision, such as commit sha or svn revision.
    * author (dict): author of the change
        * email (str)
        * name (str): full name
    * create_ts (int): change creation timestamp, in microseconds since Epoch.
    * files (list of dict): list of changed files.
      Each file is a dict with keys:
        * path (str): file path relative to the repository root.
    * message (str): change description.
    * branch (str)
    * url (str): url to human-viewable change page.
    * project (str): name of project this change refers to.

### Applications

* Scheduling code does not have to be hosted on buildbot.
* Triggering build across masters: trigger recipe module will be updated to
  trigger builds using buildbucket.
* Parallel masters: since buildbot master does not lease/schedule a build that
  it cannot handle right away, multiple masters can be setup to poll the same
  build namespace(s). This allows parallel build processing.

### Implementation details

* Buildbucket-specific information, such as build id and lease key, is stored in
  "buildbucket" property of Buidlbot entities.
* When change id and revision are specified, buildbot master executes a database
  query to find all changes matching a revision, assuming revision is uniquish,
  and then searches in memory for change by id.

[api_peek]: https://cr-buildbucket.appspot.com/_ah/api/explorer/#p/buildbucket/v1/buildbucket.peek
[api_start]: https://cr-buildbucket.appspot.com/_ah/api/explorer/#p/buildbucket/v1/buildbucket.start
[api_heartbeat]: https://cr-buildbucket.appspot.com/_ah/api/explorer/#p/buildbucket/v1/buildbucket.heartbeat
[api_succeed]: https://cr-buildbucket.appspot.com/_ah/api/explorer/#p/buildbucket/v1/buildbucket.succeed
[api_fail]: https://cr-buildbucket.appspot.com/_ah/api/explorer/#p/buildbucket/v1/buildbucket.fail
[cr-buildbucket-dev-9c9efb83ec4b.json]: http://storage.googleapis.com/cr-buildbucket-dev/cr-buildbucket-dev-9c9efb83ec4b.json
[buildbucket-service-account-bug]: https://go/buildbucket-service-account-bug
