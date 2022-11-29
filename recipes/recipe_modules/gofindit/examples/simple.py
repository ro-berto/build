# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import LogEquals, StepCommandRE, DropExpectation
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
    'gofindit',
]


def RunSteps(api):
  api.gofindit.send_result_to_luci_bisection("send_result_to_luci_bisection",
                                             123, common_pb.SUCCESS,
                                             "luci-bisection.appspot.com")
  api.gofindit.send_result_to_luci_bisection("send_result_to_luci_bisection1",
                                             123, common_pb.FAILURE,
                                             "luci-bisection.appspot.com")
  api.gofindit.send_result_to_luci_bisection("send_result_to_luci_bisection2",
                                             123, common_pb.INFRA_FAILURE,
                                             "luci-bisection.appspot.com")
  api.gofindit.send_result_to_luci_bisection("send_result_to_luci_bisection3",
                                             123, common_pb.STATUS_UNSPECIFIED,
                                             "luci-bisection.appspot.com")


def GenTests(api):
  yield api.test(
      'success',
      api.post_process(StepCommandRE, "send_result_to_luci_bisection", [
          "prpc", "call", "luci-bisection.appspot.com",
          "gofindit.GoFinditBotService.UpdateAnalysisProgress"
      ]),
      api.post_process(
          LogEquals, "send_result_to_luci_bisection", "input",
          '{\n  "analysisId": 123, \n  "bbid": "0", \n  "botId": "fake-bot-id", \n  "gitilesCommit": {\n    "host": "", \n    "id": "", \n    "project": "", \n    "ref": ""\n  }, \n  "rerunResult": {\n    "rerunStatus": "RERUN_STATUS_PASSED"\n  }\n}'
      ),
      api.post_process(DropExpectation),
  )
  yield api.test(
      'failure',
      api.post_process(StepCommandRE, "send_result_to_luci_bisection1", [
          "prpc", "call", "luci-bisection.appspot.com",
          "gofindit.GoFinditBotService.UpdateAnalysisProgress"
      ]),
      api.post_process(
          LogEquals, "send_result_to_luci_bisection1", "input",
          '{\n  "analysisId": 123, \n  "bbid": "0", \n  "botId": "fake-bot-id", \n  "gitilesCommit": {\n    "host": "", \n    "id": "", \n    "project": "", \n    "ref": ""\n  }, \n  "rerunResult": {\n    "rerunStatus": "RERUN_STATUS_FAILED"\n  }\n}'
      ),
      api.post_process(DropExpectation),
  )
  yield api.test(
      'infra_failed',
      api.post_process(StepCommandRE, "send_result_to_luci_bisection2", [
          "prpc", "call", "luci-bisection.appspot.com",
          "gofindit.GoFinditBotService.UpdateAnalysisProgress"
      ]),
      api.post_process(
          LogEquals, "send_result_to_luci_bisection2", "input",
          '{\n  "analysisId": 123, \n  "bbid": "0", \n  "botId": "fake-bot-id", \n  "gitilesCommit": {\n    "host": "", \n    "id": "", \n    "project": "", \n    "ref": ""\n  }, \n  "rerunResult": {\n    "rerunStatus": "RERUN_STATUS_INFRA_FAILED"\n  }\n}'
      ),
      api.post_process(DropExpectation),
  )
  yield api.test(
      'other',
      api.post_process(StepCommandRE, "send_result_to_luci_bisection3", [
          "prpc", "call", "luci-bisection.appspot.com",
          "gofindit.GoFinditBotService.UpdateAnalysisProgress"
      ]),
      api.post_process(
          LogEquals, "send_result_to_luci_bisection3", "input",
          '{\n  "analysisId": 123, \n  "bbid": "0", \n  "botId": "fake-bot-id", \n  "gitilesCommit": {\n    "host": "", \n    "id": "", \n    "project": "", \n    "ref": ""\n  }, \n  "rerunResult": {\n    "rerunStatus": "RERUN_STATUS_UNSPECIFIED"\n  }\n}'
      ),
      api.post_process(DropExpectation),
  )
