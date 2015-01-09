
DEPS = [
  'amp',
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
}


def GenSteps(api):
  builder = BUILDERS[api.properties['buildername']]
  api.path['checkout'] = api.path['slave_build'].join('src')
  api.amp.run_android_test_suite(
      'example_gtest_suite step',
      'gtest',
      api.amp.gtest_arguments('example_gtest_suite'),
      api.amp.amp_arguments(device_name=builder.get('device_name', None),
                            device_os=builder.get('device_os', None),
                            api_address=builder.get('api_address', None),
                            api_port=builder.get('api_port', None),
                            api_protocol=builder.get('api_protocol', None)))

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('%s_basic' % buildername) +
        api.properties.generic(buildername=buildername))

