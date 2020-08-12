# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to generate Java coverage metadata file.

The code coverage data format is defined at:
https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto
"""

import argparse
import fnmatch
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree
import zlib

import aggregation_util
import combine_jacoco_reports
import repository_util

# The sources_json_file is generated by jacoco_instr.py with source directories
# and input path to non-instrumented jars.
# e.g.
# 'source_dirs': [
#     "chrome/android/java/src/org/chromium/chrome/browser/toolbar/bottom",
#     "chrome/android/java/src/org/chromium/chrome/browser/ui/system",
# ]
# 'input_path':
#   '$CHROMIUM_OUTPUT_DIR/\
#    obj/chrome/android/features/tab_ui/java__process_prebuilt-filtered.jar'

SOURCES_JSON_FILES_SUFFIX = '__jacoco_sources.json'

# These should match the jar class files generated in internal_rules.gni
_DEVICE_CLASS_EXCLUDE_SUFFIX = 'host_filter.jar'
_HOST_CLASS_EXCLUDE_SUFFIX = 'device_filter.jar'


def get_files_with_suffix(root_dir, suffix):
  """Gets all files with a given suffix.

  Args:
    root_dir: Directory in which to search for files.
    suffix: Suffix to look for.

  Returns:
    A list of absolute paths to files that match.
  """
  files = []
  for root, _, filenames in os.walk(root_dir):
    basenames = fnmatch.filter(filenames, '*' + suffix)
    files.extend([os.path.join(root, basename) for basename in basenames])

  return files


def get_coverage_metric_summaries(tree_root):
  """Gets coverage summaries data to given dictionary.

  Code coverage Metric message definition:
  https://bit.ly/2SeYACG

  Args:
    tree_root: The root element to search for "counter" tag.

  Returns:
    A list of calculated coverage metric summaries.
  """
  summaries = []
  counter_map = {
      counter.attrib['type'].lower(): counter
      for counter in tree_root.findall('counter')
  }

  for metric in combine_jacoco_reports.JAVA_COVERAGE_METRICS:
    summary = {'name': metric, 'covered': 0, 'total': 0}
    if metric in counter_map:
      covered = int(counter_map[metric].attrib['covered'])
      missed = int(counter_map[metric].attrib['missed'])
      summary['covered'] = covered
      summary['total'] = covered + missed
    summaries.append(summary)

  return summaries


def _create_classfile_args(class_files, exclude_suffix=None):
  """Returns a list of files that don't have a given suffix.

  Args:
    class_files: A list of class files.
    exclude_suffix: Suffix to look for to exclude.

  Returns:
    A list of files that don't use the suffix.
  """
  result_class_files = []
  for f in class_files:
    if exclude_suffix:
      if not f.endswith(exclude_suffix):
        result_class_files += ['--classfiles', f]
    else:
      result_class_files += ['--classfiles', f]

  return result_class_files


def _get_file_coverage_data(file_path, source_file, diff_mapping):
  """Gets single source file coverage data from sourcefile element.

  Args:
    file_path: The file path relevant to the src root.
    source_file: The sourcefile element to calculate coverage data.
    diff_mapping: A json object that stores the diff mapping. Only meaningful to
      per-cl coverage.

  Returns:
    A dictionary of calculated source file coverage data.
  """
  file_coverage = {}
  # Source path needs to start with '//', https://bit.ly/2XC80ZL
  file_coverage['path'] = '//' + file_path
  file_coverage['lines'] = []
  file_coverage['branches'] = []

  for line in source_file.findall('line'):
    line_number = line.attrib['nr']
    if diff_mapping and file_path in diff_mapping:
      line_mapping = diff_mapping[file_path]
      if line_number in line_mapping:
        line_number = line_mapping[line_number][0]
      else:
        # Skip this line since it is deleted on Gerrit.
        continue
    line_number = int(line_number)

    covered_instructions = int(line.attrib['ci'])
    missed_branches = int(line.attrib['mb'])
    covered_branches = int(line.attrib['cb'])

    line_coverage = {
        'first': line_number,
        'last': line_number,
        'count': covered_instructions,
    }
    file_coverage['lines'].append(line_coverage)

    if missed_branches > 0 or covered_branches > 0:
      branch_coverage = {
          'line': line_number,
          'covered': covered_branches,
          'total': covered_branches + missed_branches,
      }
      file_coverage['branches'].append(branch_coverage)

  # Add coverage metrics per source file.
  file_coverage['summaries'] = get_coverage_metric_summaries(source_file)
  return file_coverage


def _get_files_coverage_data(src_path, root, source_dirs, diff_mapping,
                             source_files):
  """Gets the files coverage data based on Jacoco XML report.

  Args:
    src_path: Absolute path to the code checkout.
    root: The root element for the JaCoCo XML report ElementTree.
    source_dirs: A list of source directories of Java source files.
    diff_mapping: A json object that stores the diff mapping. Only meaningful to
      per-cl coverage.
    source_files: List of source files to generate coverage data for,
      paths relative to code checkout. Only meaningful to per-cl coverage.

  Returns:
    A list of files coverage data.
  """
  files_set = None
  if source_files:
    files_set = set(source_files)

  files_coverage_data = []
  for package in root.findall('package'):
    package_path = package.attrib['name']
    logging.info('Processing package %s', package_path)

    # Find package directory according to src root.
    package_source_dirs = []
    for source_dir in source_dirs:
      # Filter out 'out/...' source directories.
      if source_dir.startswith('out/'):
        continue
      # Find all matched source_dirs with package_path.
      if source_dir.endswith(package_path):
        package_source_dirs.append(source_dir)
    # TODO(crbug/966918): Skip auto-generated Java files/packages for now.
    if not package_source_dirs:
      logging.info('Cannot find package %s directory according to src root',
                   package_path)
      continue

    for source_file in package.findall('sourcefile'):
      source_file_name = source_file.attrib['name']
      package_source_dir = ''
      # Find the correct source_dir by the source_file_name.
      for candidate in package_source_dirs:
        if os.path.isfile(os.path.join(src_path, candidate, source_file_name)):
          package_source_dir = candidate
          break
      if not package_source_dir:
        logging.warning('Cannot find source file %s in code checkout',
                        source_file_name)
        continue
      file_path = os.path.join(package_source_dir, source_file_name)
      # Only process affected files for per-cl coverage.
      if diff_mapping and file_path not in files_set:
        continue

      logging.info('Processing file %s', '//' + file_path)
      file_coverage = _get_file_coverage_data(file_path, source_file,
                                              diff_mapping)
      if not file_coverage['lines']:
        logging.info('Skip file %s as no line instrumented', file_path)
        continue
      files_coverage_data.append(file_coverage)

  # Add git revision and timestamp per source file.
  if files_coverage_data and not diff_mapping:
    repository_util.AddGitRevisionsToCoverageFilesMetadata(
        files_coverage_data, src_path, 'DEPS')

  return files_coverage_data


def generate_json_coverage_metadata(
    src_path, root, source_dirs, component_mapping, diff_mapping, source_files):
  """Generates a JSON representation based on Jacoco XML report.

  JSON format conforms to the proto:
  //infra/appengine/findit/model/proto/code_coverage.proto

  Args:
    src_path: Absolute path to the code checkout.
    root: The root element for the JaCoCo XML report ElementTree.
    source_dirs: A list of source directories of Java source files.
    component_mapping: A JSON object that stores the mapping from dirs to
      monorail components. Only meaningful to full-repo coverage.
    diff_mapping: A json object that stores the diff mapping. Only meaningful to
      per-cl coverage.
    source_files: List of source files to generate coverage data for,
      paths relative to code checkout. Only meaningful to per-cl coverage.

  Returns:
    JSON format coverage metadata.
  """
  data = {}
  data['files'] = _get_files_coverage_data(src_path, root, source_dirs,
                                           diff_mapping, source_files)

  # Add per directory and component coverage data.
  if data['files'] and component_mapping:
    logging.info('Adding directories and components coverage data ...')

    per_directory_coverage_data, per_component_coverage_data = (
        aggregation_util.get_aggregated_coverage_data_from_files(
            data['files'], component_mapping))

    data['components'] = None
    data['dirs'] = None
    if per_component_coverage_data:
      data['components'] = per_component_coverage_data.values()
    if per_directory_coverage_data:
      data['dirs'] = per_directory_coverage_data.values()
      data['summaries'] = per_directory_coverage_data['//']['summaries']

  return data


def _parse_args(args):
  """Parses the arguments.

  Args:
    args: The passed arguments.

  Returns:
    The parsed arguments as parameters.
  """
  parser = argparse.ArgumentParser(
      description='Generate the Java coverage metadata')
  parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--output-dir',
      required=True,
      type=str,
      help='absolute path to the directory to write the metadata, must exist')
  parser.add_argument(
      '--coverage-dir',
      required=True,
      type=str,
      help='absolute path to the directory to traverse JaCoCo .exec files')
  parser.add_argument(
      '--sources-json-dir',
      required=True,
      type=str,
      help='absolute path to the directory to traverse'
      '*__jacoco_sources.json files')
  parser.add_argument(
      '--dir-metadata-path',
      type=str,
      help='absolute path to json file mapping dirs to metadata')
  parser.add_argument(
      '--source-files',
      nargs='*',
      type=str,
      help='a list of source files to generate coverage data for.'
      'path should be relative to the root of the code checkout.')
  parser.add_argument(
      '--diff-mapping-path',
      type=str,
      help='absolute path to the file that stores the diff mapping')
  params = parser.parse_args(args=args)

  if params.dir_metadata_path and not os.path.isfile(params.dir_metadata_path):
    parser.error('Dir metadata %s is missing' % params.dir_metadata_path)

  if params.diff_mapping_path and not os.path.isfile(params.diff_mapping_path):
    parser.error('Diff mapping %s is missing' % params.diff_mapping_path)

  return params


def main():
  params = _parse_args(sys.argv[1:])

  component_mapping = None
  if params.dir_metadata_path:
    with open(params.dir_metadata_path) as f:
      component_mapping = {
          d: md['monorail']['component']
          for d, md in json.load(f)['dirs'].iteritems()
          if 'monorail' in md and 'component' in md['monorail']
      }

  diff_mapping = None
  if params.diff_mapping_path:
    with open(params.diff_mapping_path) as f:
      diff_mapping = json.load(f)

  assert (component_mapping is None) != (diff_mapping is None), (
      'Either component_mapping (for full-repo coverage) or diff_mapping '
      '(for per-cl coverage) must be specified.')

  coverage_files = get_files_with_suffix(params.coverage_dir, '.exec')
  if not coverage_files:
    raise Exception('No coverage file found under %s' % params.coverage_dir)
  logging.info('Found coverage files: %s', str(coverage_files))

  class_files = []
  source_dirs = []
  sources_json_files = get_files_with_suffix(params.sources_json_dir,
                                             SOURCES_JSON_FILES_SUFFIX)
  for f in sources_json_files:
    with open(f) as json_file:
      json_file_data = json.load(json_file)
      class_files.extend(json_file_data['input_path'])
      source_dirs.extend(json_file_data['source_dirs'])

  if not class_files:
    logging.info('Skip processing data as no source file was affected in CL')
    return

  cmd = [
      'java', '-jar',
      os.path.join(params.src_path, 'third_party', 'jacoco', 'lib',
                   'jacococli.jar'), 'report'
  ] + coverage_files

  # JaCoCo XML report will be generated temporarily
  # then parsed to json metadata to --output-file.
  temp_dir = tempfile.mkdtemp()
  temp_device_xml = os.path.join(temp_dir, 'temp_device.xml')
  temp_host_xml = os.path.join(temp_dir, 'temp_host.xml')
  temp_combined_xml = os.path.join(temp_dir, 'combined_host.xml')
  try:
    device_cmd = cmd + _create_classfile_args(class_files,
                                              _DEVICE_CLASS_EXCLUDE_SUFFIX)
    device_cmd += ['--xml', temp_device_xml]
    host_cmd = cmd + _create_classfile_args(class_files,
                                            _HOST_CLASS_EXCLUDE_SUFFIX)
    host_cmd += ['--xml', temp_host_xml]

    cmd_output = subprocess.check_output(device_cmd)
    logging.info('JaCoCo device XML report generated: %r', cmd_output)
    cmd_output = subprocess.check_output(host_cmd)
    logging.info('JaCoCo host XML report generated: %r', cmd_output)
    combine_jacoco_reports.combine_xml_files(temp_combined_xml, temp_device_xml,
                                             temp_host_xml)

    # Command tends to exit with status 0 when it actually failed.
    if not os.path.isfile(temp_combined_xml):
      raise Exception('No JaCoCo XML report generated!')
    tree = ElementTree.parse(temp_combined_xml)
  finally:
    shutil.rmtree(temp_dir)

  root = tree.getroot()
  data = generate_json_coverage_metadata(params.src_path, root, source_dirs,
                                         component_mapping, diff_mapping,
                                         params.source_files)

  logging.info('Writing fulfilled Java coverage metadata to %s',
               params.output_dir)
  with open(os.path.join(params.output_dir, 'all.json.gz'), 'w') as f:
    f.write(zlib.compress(json.dumps(data)))


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
