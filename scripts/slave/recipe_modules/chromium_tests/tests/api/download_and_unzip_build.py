from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]

def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.buildbucket.builder_name
  bot_config = api.chromium_tests.create_bot_config_object([
      api.chromium_tests.create_bot_id(mastername, buildername)])
  api.chromium_tests.configure_build(bot_config)
  update_step, build_config = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.download_and_unzip_build(
      mastername, buildername, update_step, build_config,
      **api.properties.get('kwargs', {}))

def GenTests(api):
  yield api.test(
      'read-gn-args',
      api.chromium.ci_build(mastername='chromium.linux', builder='Linux Tests'),
      api.properties(
          parent_mastername='chromium.linux',
          parent_buildername='Linux Builder',
          kwargs=dict(read_gn_args=True)),
      api.post_process(post_process.MustRun, 'read GN args'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do-not-read-gn-args',
      api.chromium.ci_build(mastername='chromium.linux', builder='Linux Tests'),
      api.properties(
          parent_mastername='chromium.linux',
          parent_buildername='Linux Builder',
          kwargs=dict(read_gn_args=False)),
      api.post_process(post_process.DoesNotRun, 'read GN args'),
      api.post_process(post_process.DropExpectation),
  )
