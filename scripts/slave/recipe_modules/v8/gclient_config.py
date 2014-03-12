from RECIPE_MODULES.gclient import CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  soln = c.solutions.add()
  soln.name = 'v8'
  soln.url = 'http://v8.googlecode.com/svn/branches/bleeding_edge'
  c.got_revision_mapping['v8'] = 'got_revision'


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


@CONFIG_CTX(includes=['v8'])
def mozilla_tests(c):
  c.solutions[0].custom_deps['v8/test/mozilla/data'] = ChromiumSvnSubURL(
      c, 'chrome', 'trunk', 'deps', 'third_party', 'mozilla-tests')

@CONFIG_CTX(includes=['v8'])
def clang(c):
  c.solutions[0].custom_deps['v8/tools/clang/scripts'] = ChromiumSvnSubURL(
      c, 'chrome', 'trunk', 'src', 'tools', 'clang', 'scripts')
