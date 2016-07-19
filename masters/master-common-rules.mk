# -*- makefile -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This should be included by a makefile which lives in a buildmaster/buildslave
# directory (next to the buildbot.tac file). That including makefile *must*
# define MASTERPATH.

# The 'start' and 'stop' targets start and stop the buildbot master.
# The 'reconfig' target will tell a buildmaster to reload its config file.

# Note that a relative PYTHONPATH entry is relative to the current directory.

# Confirm that MASTERPATH has been defined.
ifeq ($(MASTERPATH),)
  $(error MASTERPATH not defined.)
endif

# Use the puppet-managed infra-python CIPD deployment (which all masters have).
INFRA_RUNPY = /opt/infra-python/run.py

# Get the current host's short hostname.  We may use this in Makefiles that
# include this file.
SHORT_HOSTNAME := $(shell hostname -s)
CURRENT_DIR = $(shell pwd)

# Where we expect flock to live.
FLOCK = /usr/bin/flock

# Per-master lockfile.
LOCKFILE = master_start.lock

printstep:
ifndef NO_REVISION_AUDIT
	@echo "**  `python -c 'import datetime; print datetime.datetime.utcnow().isoformat() + "Z"'`	make $(MAKECMDGOALS)" >> actions.log
	@pstree --show-parents $$$$ --ascii --arguments --show-pids >> actions.log
endif

notify:
	@if (hostname -f | grep -q '^master.*\.chromium\.org'); then \
		/bin/echo ; \
		/bin/echo -e "\033[1;31m***"; \
		/bin/echo "Are you manually restarting a master? This master is most likely"; \
		/bin/echo "being managed by master manager. Check out 'Issuing a restart' at"; \
		/bin/echo -e "\033[1;34mgo/master-manager\033[1;31m for more details."; \
		/bin/echo -e "***\033[0m"; \
		/bin/echo ; \
	fi

start: notify printstep bootstrap
ifndef NO_REVISION_AUDIT
	@if [ ! -f "$(GCLIENT)" ]; then \
	    echo "gclient not found.  Add depot_tools to PATH or use DEPS checkout."; \
	    exit 2; \
	fi
	$(GCLIENT) revinfo -a | tee revinfo.log >> actions.log || true
	$(GCLIENT) diff >> actions.log || true
	@($(INFRA_RUNPY) infra.tools.send_monitoring_event \
                   --service-event-revinfo=$(CURRENT_DIR)/revinfo.log \
                   --service-event-type=START \
                   --event-mon-run-type=prod \
                   --event-mon-service-name \
                   buildbot/master/$(MASTERPATH) \
   || echo 'Running send_monitoring_event failed, skipping sending events.' \
  ) 2>&1 | tee -a actions.log
endif
ifneq ($(wildcard $(FLOCK)),)
	PYTHONPATH=$(PYTHONPATH) \
	SCRIPTS_DIR=$(SCRIPTS_DIR) \
	TOPLEVEL_DIR=$(TOPLEVEL_DIR) \
	$(FLOCK) -n $(LOCKFILE) \
	$(TOPLEVEL_DIR)/build/masters/start_master.sh || ( \
	echo "Failure to start master. Check to see if a master is running and" \
	     "holding the lock on $(LOCKFILE)."; exit 1)
else
	PYTHONPATH=$(PYTHONPATH) \
	SCRIPTS_DIR=$(SCRIPTS_DIR) \
	TOPLEVEL_DIR=$(TOPLEVEL_DIR) \
	$(TOPLEVEL_DIR)/build/masters/start_master.sh
endif


start-prof: bootstrap
	TWISTD_PROFILE=1 PYTHONPATH=$(PYTHONPATH) \
	python $(SCRIPTS_DIR)/common/twistd -y $(TOPLEVEL_DIR)/build/masters/buildbot.tac

stop: notify printstep
ifndef NO_REVISION_AUDIT
	@($(INFRA_RUNPY) infra.tools.send_monitoring_event \
                   --service-event-type=STOP \
                   --event-mon-run-type=prod \
                   --event-mon-service-name \
                   buildbot/master/$(MASTERPATH) \
   || echo 'Running send_monitoring_event failed, skipping sending events' \
  ) 2>&1 | tee -a actions.log
endif

	if `test -f twistd.pid`; then kill -TERM -$$(ps h -o pgid= $$(cat twistd.pid) | awk '{print $$1}'); fi;

kill: notify printstep
	if `test -f twistd.pid`; then kill -KILL -$$(ps h -o pgid= $$(cat twistd.pid) | awk '{print $$1}'); fi;

reconfig: printstep
	kill -HUP `cat twistd.pid`

no-new-builds: notify printstep
	kill -USR1 `cat twistd.pid`

log:
	tail -F twistd.log

exceptions:
# Searches for exception in the last 11 log files.
	grep -A 10 "exception caught here" twistd.log twistd.log.?

last-restart:
	@if `test -f twistd.pid`; then stat -c %y `readlink -f twistd.pid` | \
	    cut -d "." -f1; fi;
	@ls -t -1 twistd.log* | while read f; do tac $$f | grep -m 1 \
	    "Creating BuildMaster"; done | head -n 1

wait:
	while `test -f twistd.pid`; do sleep 1; done;

waitforstart:
	while `test ! -f twistd.pid`; do sleep 1; done;

restart: notify stop wait start log

restart-prof: stop wait start-prof log

bootstrap: printstep
	@[ -e '.dbconfig' ] || [ -e 'state.sqlite' ] || \
	PYTHONPATH=$(PYTHONPATH) python $(TOPLEVEL_DIR)/build/masters/buildbot \
	upgrade-master .

setup:
	@echo export PYTHONPATH=$(PYTHONPATH)
