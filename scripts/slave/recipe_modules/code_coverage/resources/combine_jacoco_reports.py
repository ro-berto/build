#!/usr/bin/env python

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Aggregates Jacoco coverage files to produce output."""

from __future__ import print_function

import argparse
import sys
from xml.dom import minidom

# Conforms to JaCoCo coverage counter types:
# https://www.jacoco.org/jacoco/trunk/doc/counters.html
JAVA_COVERAGE_METRICS = [
    'instruction', 'branch', 'line', 'complexity', 'method', 'class'
]


def _add_missing_nodes(device_dict, host_dict, root_node, attribute):
  # Adds any node in host that are not in device.
  for key in host_dict:
    node_attribute = host_dict[key].getAttribute(attribute)
    if node_attribute not in device_dict:
      added_node = root_node.appendChild(host_dict[key])
      device_dict[node_attribute] = added_node


def _create_attribute_to_object_dict(element_list, attrib):
  return {e.getAttribute(attrib): e for e in element_list}


def _create_counter_map(counter_list):
  """Creates a map of counter types to the counter nodes.

  Args:
    counter_list: A list of counters
  Returns:
    A map of counter types to counter nodes.
  """
  counter_map = {
      counter.getAttribute('type').lower(): counter for counter in counter_list
  }

  return counter_map


def _create_total_dicts():
  total_dicts = {}
  for metric in JAVA_COVERAGE_METRICS:
    new_dict = {'covered': 0, 'missed': 0}
    total_dicts[metric] = new_dict

  return total_dicts


def _get_covered_and_missed_from_counter(counter):
  return (counter.getAttribute('covered'), counter.getAttribute('missed'))


def _get_dict_for_each_element(device_node, host_node, children_tag,
                               attribute_tag):
  # Returns dictionaries mapping the attribute tag to the node's children.
  device_children = device_node.getElementsByTagName(children_tag)
  host_children = host_node.getElementsByTagName(children_tag)
  device_mapping_dict = _create_attribute_to_object_dict(
      device_children, attribute_tag)
  host_mapping_dict = _create_attribute_to_object_dict(host_children,
                                                       attribute_tag)
  return (device_mapping_dict, host_mapping_dict)


def _get_counters_list(root_node):
  return [node for node in root_node.childNodes if node.tagName == 'counter']


def _get_counter_totals_for_tag_name(root_node, tag_name):
  # Gets a diciontary of the totals of the counters in the children's counters.
  total_dicts = _create_total_dicts()
  # Cannot just use getElementByTagName as that will go more than one layer
  # deep. Want to avoid double counting the counters.
  nodes = [node for node in root_node.childNodes if node.tagName == tag_name]
  for node in nodes:
    for counter in _get_counters_list(node):
      covered_lines, missed_lines = _get_covered_and_missed_from_counter(
          counter)
      counter_type = counter.getAttribute('type').lower()
      total_dicts[counter_type]['covered'] += int(covered_lines)
      total_dicts[counter_type]['missed'] += int(missed_lines)

  return total_dicts


def _set_higher_counter(device_counter, host_counter):
  # Ideally would use min/max on covered and missed, but want to make sure
  # to use the variables from the same counter.
  if int(device_counter.getAttribute('covered')) >= int(
      host_counter.getAttribute('covered')):
    chosen_counter = device_counter
  else:
    chosen_counter = host_counter

  covered, missed = _get_covered_and_missed_from_counter(chosen_counter)
  device_counter.setAttribute('covered', covered)
  device_counter.setAttribute('missed', missed)


def _set_higher_method_coverage(device_method_dict, host_method_dict):
  for method_key in device_method_dict:
    device_method = device_method_dict[method_key]
    if method_key not in host_method_dict:
      continue

    device_counter_map = _create_counter_map(
        device_method.getElementsByTagName('counter'))
    host_counter_map = _create_counter_map(
        host_method_dict[method_key].getElementsByTagName('counter'))
    for metric in device_counter_map:
      if metric in host_counter_map:
        _set_higher_counter(device_counter_map[metric],
                            host_counter_map[metric])


def _update_all_nodes_to_higher_coverage(device_package_dict,
                                         host_package_dict):
  # Go to every package, then every class in the package, then every method
  # in the class and choose the coverage that is higher.
  for key in device_package_dict:
    device_package = device_package_dict[key]
    if key not in host_package_dict:
      continue
    host_package = host_package_dict[key]
    device_class_dict, host_class_dict = _get_dict_for_each_element(
        device_package, host_package, 'class', 'name')
    _add_missing_nodes(device_class_dict, host_class_dict, device_package,
                       'name')
    for class_key in device_class_dict:
      device_class = device_class_dict[class_key]
      if class_key not in host_class_dict:
        continue
      host_class = host_class_dict[class_key]
      device_method_dict, host_method_dict = _get_dict_for_each_element(
          device_class, host_class, 'method', 'line')
      _add_missing_nodes(device_method_dict, host_method_dict, device_class,
                         'line')
      # Rewrite the values in method coverage based on which is higher.
      # Then update the counter at the class level.
      _set_higher_method_coverage(device_method_dict, host_method_dict)
      _update_children_counters(device_class, 'method')

    _update_package_source_files(device_package, host_package)
    _update_children_counters(device_package, 'sourcefile')


def _update_children_counters(root_node, tag_name):
  # Updates the children (not deeper, ie grandchildren) of the node. This is to
  # avoid double counting counters (as a class's total counter is the summation
  # of the method counters.)
  counters = _get_counters_list(root_node)
  total_dicts = _get_counter_totals_for_tag_name(root_node, tag_name)
  _update_counters_from_total(counters, total_dicts)


def _update_counters_from_total(counter_nodes, total_dicts):
  for counter in counter_nodes:
    counter_type = counter.getAttribute('type').lower()
    counter.setAttribute('covered', str(total_dicts[counter_type]['covered']))
    counter.setAttribute('missed', str(total_dicts[counter_type]['missed']))


def _update_line_code_coverage_nodes(device_dict, host_dict, device_source_node,
                                     host_source_node):
  # Gets the nodes that are in the host_tree and not in the device_tree.
  # If the node exists in both trees, choose the one that higher
  # covered instructions (ci).
  instruction_list = ['ci', 'cb', 'mi', 'mb']
  total_dict = {inst: 0 for inst in instruction_list}

  # Add any nodes that are in host, that aren't in dict. This adds the entry
  # to device_dict.
  _add_missing_nodes(device_dict, host_dict, device_source_node, 'nr')

  # Check all the lines that are the same. Set the device_node to have the
  # fields that are higher.
  for key in device_dict:
    device_line = device_dict[key]
    if key not in host_dict:
      continue

    host_line = host_dict[key]
    host_line_ci = int(host_line.getAttribute('ci'))
    device_line_ci = int(device_line.getAttribute('ci'))
    # We'll take all the data from the host line if ci is better.
    if device_line_ci < host_line_ci:
      for inst in instruction_list:
        device_line.setAttribute(inst, host_line.getAttribute(inst))

  # Sum up all the coverage numbers.
  for key in device_dict:
    device_line = device_dict[key]
    for inst in instruction_list:
      total_dict[inst] += int(device_line.getAttribute(inst))

  _update_source_file_counters(device_source_node, host_source_node, total_dict)


def _update_package_source_files(device_package, host_package):
  # Adds any source files in the host_tree that are not in the device_tree.
  # One the source file that are the same, combine the source files
  # based on "nr"(line number)
  device_sources = device_package.getElementsByTagName('sourcefile')
  host_sources = host_package.getElementsByTagName('sourcefile')

  device_name_to_sources_dict = _create_attribute_to_object_dict(
      device_sources, 'name')
  host_name_to_sources_dict = _create_attribute_to_object_dict(
      host_sources, 'name')

  # Adds any source files that are in the host package that
  # are not in the device package.
  _add_missing_nodes(device_name_to_sources_dict, host_name_to_sources_dict,
                     device_package, 'name')

  for key in device_name_to_sources_dict:
    device_source_node = device_name_to_sources_dict[key]
    host_source_node = host_name_to_sources_dict[key]
    device_line_dict = _create_attribute_to_object_dict(
        device_source_node.getElementsByTagName('line'), 'nr')
    host_line_dict = _create_attribute_to_object_dict(
        host_source_node.getElementsByTagName('line'), 'nr')
    # Takes all the "lines" in the source file, then compares them and chooses
    # the "line" that has higher coverage.
    _update_line_code_coverage_nodes(device_line_dict, host_line_dict,
                                     device_source_node, host_source_node)


def _update_source_file_counters(device_source_node, host_source_node,
                                 total_dict):
  # Update the counter nodes of the source file.
  device_counter_dict = _create_attribute_to_object_dict(
      device_source_node.getElementsByTagName('counter'), 'type')
  host_counter_dict = _create_attribute_to_object_dict(
      host_source_node.getElementsByTagName('counter'), 'type')
  for inst in device_counter_dict:
    device_counter = device_counter_dict[inst]
    if inst == 'INSTRUCTION':
      device_counter.setAttribute('covered', str(total_dict['ci']))
      device_counter.setAttribute('missed', str(total_dict['mi']))
    elif inst == 'BRANCH':
      device_counter.setAttribute('covered', str(total_dict['cb']))
      device_counter.setAttribute('missed', str(total_dict['mb']))
    else:
      covered_val = max(
          int(device_counter.getAttribute('covered')),
          int(host_counter_dict[inst].getAttribute('covered')))
      missed_val = min(
          int(device_counter.getAttribute('missed')),
          int(host_counter_dict[inst].getAttribute('missed')))
      device_counter.setAttribute('covered', str(covered_val))
      device_counter.setAttribute('missed', str(missed_val))


def combine_xml_files(combined_file_path, device_file_path, host_file_path):
  """Combines two xml jacoco report files into one.

  Expected input is two jacoco coverage report xml files.
  The report is composed of a tree of nodes, the root node is the "report" node
  which contains counters and packages.
  -The package nodes contain class nodes, sourcefile nodes, and counters.
  -The sourcefile nodes contain the file name, line nodes, and counters
  -The class nodes contain the class's name, method nodes, and counters
  -The method nodes contain the method's name and counters.
  -The line nodes contain 4 attributes,
    nr=line number corresponding to the physical line in the sourcefile.
    mi=missed instructions for the line
    ci=covered instructiosn for the line
    mb=missed branch for the line
    cb=covered branch for the line

  The counters contain an instruction type as found in JAVA_COVERAGE_METRICS
  and the total number of "covered" or "missed" items on that metric in that
  node. So a class node's counters contain the sum of counters in the methods.
  The package node's counters contain the sum total of the counters in the
  sourcefile nodes. The sourcefile nodes contain the sum total of the counters
  in the line node.

  The code walks down to each method in the device report and finds
  the matching method in the host_report. It then chooses to use the coverage
  data from whichever node is higher. This is not perfect as device can have
  10 covered and 10 missed, and host can have 15 covered and 5 missed, so
  maybe it should be 20 covered and 0 missed if the coverage overlaps properly.
  If a method/class/package is in the host report and not in the device report,
  it adds it into hte device_report.

  The code then walks down the sourcefiles and adds to device_report any lines
  that are in host_report and not already present. It then compares every line
  in device_report to host_report and chooses to use the line that has higher
  ci. It then calculates a new sum for the counters in sourcefile and packages
  and reports (not classes and methods).

  Args:
    combined_file_path: Where to write the combined report file to.
    device_file_path: The location of the device coverage report.
    host_file_path: The location of the device coverage report.

  Returns:
    Results are written to combined_file_path
  """
  device_tree = minidom.parse(device_file_path)
  host_tree = minidom.parse(host_file_path)
  device_report_node = device_tree.getElementsByTagName('report')[0]
  device_packages = device_tree.getElementsByTagName('package')
  host_packages = host_tree.getElementsByTagName('package')
  device_name_to_package_dict = _create_attribute_to_object_dict(
      device_packages, 'name')
  host_name_to_package_dict = _create_attribute_to_object_dict(
      host_packages, 'name')

  _update_all_nodes_to_higher_coverage(device_name_to_package_dict,
                                       host_name_to_package_dict)
  _add_missing_nodes(device_name_to_package_dict, host_name_to_package_dict,
                     device_report_node, 'name')

  # Only updates one layer of counters, ie doesn't do grandchildren.
  _update_children_counters(device_report_node, 'package')

  with open(combined_file_path, 'w') as xmlfile:
    device_tree.writexml(xmlfile)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--device-xml', required=True, help='Path to the xml coverage report.')
  parser.add_argument(
      '--host-xml', required=True, help='Path to the xml coverage report.')
  parser.add_argument(
      '--combined-xml',
      required=True,
      help='Destination path to write the combined xml coverage report.')
  args = parser.parse_args()
  combine_xml_files(args.combined_xml, args.device_xml, args.host_xml)


if __name__ == '__main__':
  sys.exit(main())
