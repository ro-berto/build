from RECIPE_MODULES.gclient import CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  soln = c.solutions.add()
  soln.name = 'v8'
  soln.url = 'http://v8.googlecode.com/svn/branches/bleeding_edge'
