"""This file is meant to be run in an environment where scipy is available."""
import json
import logging
import sys

try:
  from scipy import stats
except ImportError:
  def main():
    # scipy required, see module docstring.
    logging.warning(sys.modules[__name__].__doc__)
    return 1
else:

  def main():
    if len(sys.argv) < 4:
      return 1
    _, list_a, list_b, significance = sys.argv[:4]
    list_a = json.loads(list_a)
    list_b = json.loads(list_b)
    significance = float(significance)

    mann_whitney_p_value = stats.mannwhitneyu(list_a, list_b).pvalue

    results = {
        'first_sample': list_a,
        'second_sample': list_b,
        'mann_p_value': mann_whitney_p_value,
    }

    results['significantly_different'] = bool(
        float(results['mann_p_value']) < float(significance))

    print json.dumps(results)
    return 0

if __name__ == '__main__':
  sys.exit(main())
