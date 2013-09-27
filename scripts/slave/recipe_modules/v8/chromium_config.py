from RECIPE_MODULES.chromium import CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  if c.TARGET_ARCH == 'arm':
    v8_target_arch = 'arm'
  elif c.TARGET_ARCH == 'mips':
    v8_target_arch = 'mips'
  elif c.TARGET_BITS == 64:
    v8_target_arch = 'x64'
  else:
    v8_target_arch = 'ia32'
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = v8_target_arch
  del c.gyp_env.GYP_DEFINES['component']
  c.build_config_fs = c.BUILD_CONFIG
  c.build_dir = ''

  c.compile_py.build_tool = 'make'
  c.compile_py.default_targets = ['buildbot']