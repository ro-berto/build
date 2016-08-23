"""Launches an anaconda environment to run some scipy hypothesis tests."""

import json
import os
import subprocess
import sys

class ScipyNotInstalledError(Exception):
  pass

def main(argv, anaconda_path=None):
  _, list_a, list_b, significance  = argv

  # Do not even test if there's a single repeated value on both samples.
  if len(set(json.loads(list_a) + json.loads(list_b))) == 1:
    return {
        'first_sample': json.loads(list_a),
        'second_sample': json.loads(list_b),
        'mann_p_value': None,
        'significantly_different': False
    }

  if not anaconda_path:
    if os.name == 'nt':
      anaconda_path = r'c:\conda-py-scientific\python.exe'
    else:
      anaconda_path = '/opt/conda-py-scientific/bin/python'
  if not os.path.exists(anaconda_path):
    raise ScipyNotInstalledError()

  inner_script_location = os.path.join(os.path.dirname(os.path.realpath(
      __file__)), 'significantly_different_inner.py')

  conda_environ = dict(os.environ)
  del conda_environ["PYTHONPATH"]

  return json.loads(subprocess.check_output(
      [anaconda_path, inner_script_location,list_a, list_b, significance],
      env=conda_environ))

if __name__ == '__main__':
  result = main(sys.argv)
  if result:
    print json.dumps(result, indent=4)
    sys.exit(0)
  sys.exit(1)
