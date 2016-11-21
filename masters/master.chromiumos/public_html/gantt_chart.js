// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
google.charts.load('current', {'packages':['gantt']});

/**
 * reconcileSwarmingSteps reconciles a Swarming step's "trigger" step with
 * it's subsequent "collect results" step.
 *
 * Swarming steps in BuildBot create two steps - one to trigger the work
 * on swarming, and a later step to collect the results.
 *
 * The two steps have the same name, except the trigger step has "[trigger] "
 * prepended to the name.
 *
 * This function consolidates the two steps into one by using the start
 * time from the trigger step and the end time from the "collect results"
 * step.
 *
 * This function assumes that a trigger step will be found before the
 * corresponding "collect results" step in the list of steps.
 * @param {Array<Object>} steps List of step objects. Each step object
 *     has the following properties: name {string}, start {Date}, end {Date}
 */
function reconcileSwarmingSteps(steps) {
  let reconciledSteps = [];
  let triggerSteps = {};

  for (let s of steps) {
    // trigger steps have names like "[trigger] TheRestOfTheNameGoesHere..."
    let isTriggerStep = /\[trigger\] (.*)/.exec(s.name);
    if (isTriggerStep) {
      triggerSteps[isTriggerStep[1]] = s;
    } else {
      if (triggerSteps[s.name]) {
        s.start = triggerSteps[s.name].start;
      }
      reconciledSteps.push(s);
    }
  }

  return reconciledSteps;
};

function drawChart(steps) {
  let data = new google.visualization.DataTable();
  data.addColumn('string', 'Task ID');
  data.addColumn('string', 'Task Name');
  data.addColumn('string', 'Resource');
  data.addColumn('date', 'Start Date');
  data.addColumn('date', 'End Date');
  data.addColumn('number', 'Duration');
  data.addColumn('number', 'Percent Complete');
  data.addColumn('string', 'Dependencies');

  for (s of steps) {
    data.addRow([s.name, s.name, null, s.start, s.end, null, 100, null]);
  }

  let trackHeight = 25;
  let options = {
    height: data.getNumberOfRows() * trackHeight,
    gantt: {
      trackHeight: trackHeight,
      barHeight: trackHeight * 0.8,
      labelMaxWidth: 500,
    }
  };

  let chart = new google.visualization.Gantt(
      document.getElementById('chart_div'));
  chart.draw(data, options);
}

let chartVisible = false;
function toggleChart(rawSteps) {
  if (chartVisible) {
    document.getElementById('chart_div').style.display = 'none';
    chartVisible = false;
  } else {
    document.getElementById('chart_div').style.display = 'block';
    let steps = reconcileSwarmingSteps(rawSteps);
    drawChart(steps);
    chartVisible = true;
  }
}
