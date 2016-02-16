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

    shapiro_p_value = stats.shapiro(list_a)[1], stats.shapiro(list_b)[1]
    mann_whitney_p_value = stats.mannwhitneyu(list_a, list_b).pvalue
    anderson_p_value = stats.anderson_ksamp([list_a, list_b]).significance_level
    welch_p_value = stats.ttest_ind(list_a, list_b, equal_var=False)[1]

    results = {
        'first_sample': list_a,
        'second_sample': list_b,
        'shapiro_p_value': shapiro_p_value,
        'mann_p_value': mann_whitney_p_value,
        'anderson_p_value': anderson_p_value,
        'welch_p_value': welch_p_value,
    }

    if (results['shapiro_p_value'][0] < significance and
        results['shapiro_p_value'][1] < significance):
      results['normal-y'] = True
    else:
      results['normal-y'] = False
    results['significantly_different'] = bool(
        float(results['mann_p_value']) < float(significance))

    print json.dumps(results)
    return 0

if __name__ == '__main__':
  sys.exit(main())
