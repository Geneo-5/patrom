EXTERNDIR       := $(CURDIR)/extern
DEPENDSDIR      := $(EXTERNDIR)/depends
BUILDDIR        := $(CURDIR)/build
DESTDIR         := $(CURDIR)/out
VENV            := $(DESTDIR)
PYTHON          := $(VENV)/bin/python3

export EBUILDDIR

tests := hello base
tests_out := $(patsubst %,$(BUILDDIR)/test-%/test,$(tests))

src   := $(wildcard $(CURDIR)/src/**/*)

define run_test
@echo ====== RUN $(strip $(1)); \
$(BUILDDIR)/test-$(strip $(1))/test $(CURDIR)/tests/$(strip $(1)).json | tee >(cmp --verbose - $(CURDIR)/tests/$(strip $(1)).expect)
endef

.PHONY: test
test: $(tests_out)
	$(foreach t,$(tests),$(call run_test,$t)$(newline))

$(addsuffix .c,$(tests_out)): PATH:=$(VENV)/bin:$(PATH)
$(addsuffix .c,$(tests_out)): $(BUILDDIR)/test-%/test.c : $(CURDIR)/tests/%.tmpl $(src) \
                            | $(BUILDDIR)/test-% $(VENV)/bin/patrom
	@echo ====== GEN $@
	@patrom $< $@

$(tests_out): % : %.c $(CURDIR)/tests/test.c
	@echo ====== CC $<
	@$(CC) $< $(CURDIR)/tests/test.c -ljson-c -o $@

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

define newline


endef

