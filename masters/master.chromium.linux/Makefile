# -*- makefile -*-

BUILDBOT_PATH = $(BUILDBOT8_PATH)
MASTERPATH := master.chromium.linux
include ../master-common.mk

ifeq ($(SHORT_HOSTNAME),master1)
start:
	@echo "#"
	@echo "# Chromium master does not run on master1."
	@echo "# See master1a instead."
	@echo "#"
endif
