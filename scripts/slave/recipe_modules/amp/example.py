
DEPS = [
  'amp',
  'json',
  'path',
  'properties',
]

BUILDERS = {
  'normal_example': {
    'device_name': 'SampleDevice',
    'device_os': 'SampleDeviceOS',
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_device_name': {
    'device_os': 'SampleDeviceOS',
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_device_os': {
    'device_name': 'SampleDevice',
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_api_address': {
    'device_name': 'SampleDevice',
    'device_os': 'SampleDeviceOS',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_api_port': {
    'device_name': 'SampleDevice',
    'device_os': 'SampleDeviceOS',
    'api_address': '127.0.0.1',
    'api_protocol': 'http',
  },
  'no_api_protocol': {
    'device_name': 'SampleDevice',
    'device_os': 'SampleDeviceOS',
    'api_address': '127.0.0.1',
    'api_port': '80',
  },
  'split_example': {
    'device_name': 'SampleDevice',
    'device_os': 'SampleDeviceOS',
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  }
}


def GenSteps(api):
  builder = BUILDERS[api.properties['buildername']]
  api.path['checkout'] = api.path['slave_build'].join('src')

  if api.properties['buildername'].startswith('split'):
    api.amp.trigger_android_test_suite(
        'example_gtest_suite', 'gtest',
        api.amp.gtest_arguments('example_gtest_suite'),
        api.amp.amp_arguments(device_name=builder.get('device_name', None),
                              device_os=builder.get('device_os', None),
                              api_address=builder.get('api_address', None),
                              api_port=builder.get('api_port', None),
                              api_protocol=builder.get('api_protocol', None)))

    api.amp.collect_android_test_suite(
        'example_gtest_suite', 'gtest',
        api.amp.gtest_arguments('example_gtest_suite'),
        api.amp.amp_arguments(api_address=builder.get('api_address', None),
                              api_port=builder.get('api_port', None),
                              api_protocol=builder.get('api_protocol', None)))
  else:
    api.amp.run_android_test_suite(
        'example_gtest_suite step',
        'gtest',
        api.amp.gtest_arguments('example_gtest_suite'),
        api.amp.amp_arguments(device_name=builder.get('device_name', None),
                              device_os=builder.get('device_os', None),
                              api_address=builder.get('api_address', None),
                              api_port=builder.get('api_port', None),
                              api_protocol=builder.get('api_protocol', None)))

    api.amp.run_android_test_suite(
        'example_gtest_suite (trigger)',
        'gtest',
        api.amp.gtest_arguments('example_gtest_suite'),
        api.amp.amp_arguments(device_name=builder.get('device_name', None),
                              device_os=builder.get('device_os', None),
                              api_address=builder.get('api_address', None),
                              api_port=builder.get('api_port', None),
                              api_protocol=builder.get('api_protocol', None),
                              trigger='test_trigger_file.json'))

    api.amp.run_android_test_suite(
        'example_gtest_suite (collect)',
        'gtest',
        api.amp.gtest_arguments('example_gtest_suite'),
        api.amp.amp_arguments(device_name=builder.get('device_name', None),
                              device_os=builder.get('device_os', None),
                              api_address=builder.get('api_address', None),
                              api_port=builder.get('api_port', None),
                              api_protocol=builder.get('api_protocol', None),
                              collect='test_trigger_file.json'))

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('%s_basic' % buildername) +
        api.properties.generic(buildername=buildername))

  yield (
      api.test('bad_device_data_from_trigger') +
      api.properties.generic(buildername='split_example') +
      api.override_step_data('[trigger] example_gtest_suite',
                             api.json.output({})))

  yield (
      api.test('bad_device_data_for_collect') +
      api.properties.generic(buildername='split_example') +
      api.override_step_data('[collect] load example_gtest_suite data',
                             api.json.output({})))
