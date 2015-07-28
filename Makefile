prefix := /usr
libexecdir := $(prefix)/libexec

_default:
	@echo "No default. Try 'make install'"

install:
	test -d $(DESTDIR)$(libexecdir)/htcondor-job-router || install -d $(DESTDIR)$(libexecdir)/htcondor-job-router
	install -m 0755 bin/pilot-translate.py $(DESTDIR)$(libexecdir)/htcondor-job-router/pilot-translate.py
