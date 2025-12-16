EXTERNDIR       := $(CURDIR)/extern
DEPENDSDIR      := $(EXTERNDIR)/depends
BUILDDIR        := $(CURDIR)/build
DESTDIR         := $(CURDIR)/out
VENV            := $(DESTDIR)
PYTHON          := $(VENV)/bin/python3

export EBUILDDIR

all: test-base

export PATH := $(VENV)/bin:$(PATH)

test-%: tests/test-%.tmpl | $(BUILDDIR)/test-%
	@echo ====== Test $*
	@patrom $< $(BUILDDIR)/test-$*

install: venv

clean:
	@rm -rf $(BUILDDIR)/test-*

clobber:
	@rm -rf $(EXTERNDIR)
	@rm -rf $(BUILDDIR)
	@rm -rf $(DESTDIR)

$(EXTERNDIR) $(DEPENDSDIR):
	@mkdir -p $@

$(BUILDDIR)/% $(DESTDIR)/%:
	@mkdir -p $@

#################### VENV

$(VENV)/bin/python3:
	@echo ===== Make python venv
	@python3 -m venv $(VENV)

$(VENV)/bin/patrom: $(VENV)/bin/python3
	@echo ===== Install editable patrom
	@$(PYTHON) -m pip install -e .

venv: $(VENV)/bin/patrom

.PHONY: pip-download
pip-download: | $(DEPENDSDIR)
	@echo ===== Download troer depends
	@cd $(DEPENDSDIR); $(PYTHON) -m pip download $(CURDIR)
	@cd $(DEPENDSDIR); $(PYTHON) -m pip download -r $(CURDIR)/install-depends.txt

.PHONY: all install clobber clean
