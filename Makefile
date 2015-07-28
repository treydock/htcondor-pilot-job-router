prefix := /usr
sysconfdir := /etc
libexecdir := $(prefix)/libexec

_default:
	@echo "No default. Try 'make install'"

install:
	test -d $(DESTDIR)$(libexecdir)/htcondor-job-router || install -d $(DESTDIR)$(libexecdir)/htcondor-job-router
	install -m 0755 bin/pilot-translate.py $(DESTDIR)$(libexecdir)/htcondor-job-router/pilot-translate.py
	#install -m 0755 ext/CMSglideinWMSValidation/get_user_requests.py $(DESTDIR)$(libexecdir)/get_user_requests.py
	#test -d $(DESTDIR)$(sysconfdir)/cron.d || install -d $(DESTDIR)$(sysconfdir)/cron.d
	#install -m 0755 etc/gums-grid-mapfile-local.cron $(DESTDIR)$(sysconfdir)/cron.d/gums-grid-mapfile-local
	test -d $(DESTDIR)$(sysconfdir)/default || install -d $(DESTDIR)$(sysconfdir)/default
	install -m 0644 etc/htcondor-pilot-job-router.ini $(DESTDIR)$(sysconfdir)/default/htcondor-pilot-job-router.ini.example
