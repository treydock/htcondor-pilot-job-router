prefix := /usr
sysconfdir := /etc
libexecdir := $(prefix)/libexec

.PHONY: help

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "	all                       to run all install targets"
	@echo "	install-scripts           to install scripts"
	@echo "	install-gridmap-cron      to install grid-mapfile cron"

_default: help

bin/chown_iwd: bin/chown_iwd.c
	#gcc bin/chown_iwd.c -o bin/chown_iwd

install-base:
	test -d $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router || install -d $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router
	test -d $(DESTDIR)$(sysconfdir)/cron.d || install -d $(DESTDIR)$(sysconfdir)/cron.d

install-scripts: install-base bin/chown_iwd
	#install -m 4755 bin/chown_iwd $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router/chown_iwd
	install -m 0755 bin/pilot-translate.py $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router/pilot-translate.py
	install -m 0755 ext/CMSglideinWMSValidation/get_user_requests.py $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router/get_user_requests.py
	install -m 0755 bin/gums-grid-mapfile-local.sh $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router/gums-grid-mapfile-local
	install -m 0755 bin/get-cms-user-requests.sh $(DESTDIR)$(libexecdir)/htcondor-pilot-job-router/get-cms-user-requests
	install -m 0644 etc/htcondor-pilot-job-router.ini $(DESTDIR)$(sysconfdir)/default/htcondor-pilot-job-router.ini.example
	install -m 0644 etc/get-cms-user-requests.cron $(DESTDIR)$(sysconfdir)/cron.d/get-cms-user-requests

install-gridmap-cron: install-base
	install -m 0644 etc/gums-grid-mapfile-local.cron $(DESTDIR)$(sysconfdir)/cron.d/gums-grid-mapfile-local

all: install-scripts install-gridmap-cron
