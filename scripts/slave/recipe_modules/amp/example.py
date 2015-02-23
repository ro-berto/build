
DEPS = [
  'amp',
  'json',
  'path',
  'properties',
]

BUILDERS = {
  'normal_example': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_device_name': {
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_device_os': {
    'device_name': ['SampleDevice'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_api_address': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_port': '80',
    'api_protocol': 'http',
  },
  'no_api_port': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_protocol': 'http',
  },
  'no_api_protocol': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
  },
  'split_example': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'multiple_devices': {
    'device_name': ['SampleDevice0', 'SampleDevice1'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'multiple_device_oses': {
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS0', 'SampleDeviceOS1'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'device_oem': {
    'device_name': ['SampleDevice'],
    'device_oem': ['SampleDeviceOEM'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'minimum_device_os': {
    'device_minimum_os': 'MinimumSampleDeviceOS',
    'device_name': ['SampleDevice'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'device_os_and_minimum_device_os': {
    'device_minimum_os': 'MinimumSampleDeviceOS',
    'device_name': ['SampleDevice'],
    'device_os': ['SampleDeviceOS'],
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
  'underspecified_with_timeout': {
    'device_minimum_os': 'MinimumSampleDeviceOS',
    'device_name': ['SampleDevice0', 'SampleDevice1'],
    'device_timeout': 60,
    'api_address': '127.0.0.1',
    'api_port': '80',
    'api_protocol': 'http',
  },
}

AMP_RESULTS_BUCKET = 'chrome-amp-results'

def GenSteps(api):
  builder = BUILDERS[api.properties['buildername']]
  api.path['checkout'] = api.path['slave_build'].join('src')

  api.amp.trigger_test_suite(
      'example_gtest_suite', 'gtest',
      api.amp.gtest_arguments('example_gtest_suite'),
      api.amp.amp_arguments(
          device_minimum_os=builder.get('device_minimum_os', None),
          device_name=builder.get('device_name', None),
          device_oem=builder.get('device_oem', None),
          device_os=builder.get('device_os', None),
          device_timeout=builder.get('device_timeout', None),
          api_address=builder.get('api_address', None),
          api_port=builder.get('api_port', None),
          api_protocol=builder.get('api_protocol', None)))

  api.amp.trigger_test_suite(
      'example_uirobot_suite', 'uirobot',
      api.amp.uirobot_arguments(app_under_test='Example.apk'),
      api.amp.amp_arguments(
          device_minimum_os=builder.get('device_minimum_os', None),
          device_name=builder.get('device_name', None),
          device_oem=builder.get('device_oem', None),
          device_os=builder.get('device_os', None),
          device_timeout=builder.get('device_timeout', None),
          api_address=builder.get('api_address', None),
          api_port=builder.get('api_port', None),
          api_protocol=builder.get('api_protocol', None)))

  api.amp.collect_test_suite(
      'example_gtest_suite', 'gtest',
      api.amp.gtest_arguments('example_gtest_suite'),
      api.amp.amp_arguments(api_address=builder.get('api_address', None),
                            api_port=builder.get('api_port', None),
                            api_protocol=builder.get('api_protocol', None)))

  api.amp.upload_logcat_to_gs(AMP_RESULTS_BUCKET, 'example_gtest_suite')

  api.amp.collect_test_suite(
      'example_uirobot_suite', 'uirobot',
      api.amp.uirobot_arguments(),
      api.amp.amp_arguments(api_address=builder.get('api_address', None),
                            api_port=builder.get('api_port', None),
                            api_protocol=builder.get('api_protocol', None)))

  api.amp.upload_logcat_to_gs(AMP_RESULTS_BUCKET, 'example_uirobot_suite')

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

  yield (
    api.test('bad_test_id_data_for_upload') +
    api.properties.generic(buildername='split_example') +
    api.override_step_data('[upload logcat] load example_gtest_suite data',
                           api.json.output({})))
