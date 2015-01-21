# -*- makefile -*-

BUILDBOT_PATH = $(BUILDBOT8_PATH)
MASTERPATH := master.chromiumos
include ../master-common.mk

public_html/auto-builder.js: master.cfg
	./process_cfg.py
process: public_html/auto-builder.js
	./process_cfg.py

start: public_html/auto-builder.js
