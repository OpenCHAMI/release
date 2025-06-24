.PHONY: all clean

GIT     ?= $(shell command -v git 2>/dev/null)
TAG     ?= $(shell $(GIT) describe --tags --always --abbrev=0)
VERSION ?= $(patsubst v%,%,$(TAG))
RELEASE ?= 1
HOME    ?= $(shell echo ${HOME})

rwildcard = $(foreach d,$(wildcard $(1:=/*)),$(call rwildcard,$d,$2) $(filter $(subst *,%,$2),$d))

all: openchami.rpm

$(HOME)/rpmbuild:
	rpmdev-setuptree

$(HOME)/rpmbuild/SPECS/openchami.spec: openchami.spec $(HOME)/rpmbuild
	mkdir -p $(HOME)/rpmbuild/SPECS
	cp $< $@

	cp -r $< $@

$(HOME)/rpmbuild/SOURCES/openchami-$(VERSION).tar.gz: $(HOME)/rpmbuild $(call rwildcard,.,*)
	mkdir -p $(HOME)/rpmbuild/SOURCES
	rm -Rf $(HOME)/rpmbuild/SOURCES/openchami-$(VERSION).tar.gz
	tar czvf $@ --transform 's,^,openchami-$(VERSION)/,' *

$(HOME)/rpmbuild/RPMS/noarch/openchami-$(VERSION)-$(RELEASE).noarch.rpm: $(HOME)/rpmbuild/SPECS/openchami.spec $(HOME)/rpmbuild/SOURCES/openchami-$(VERSION).tar.gz
	rpmbuild -ba $(HOME)/rpmbuild/SPECS/openchami.spec --define 'version $(VERSION)' --define 'rel $(RELEASE)'

openchami.rpm: $(HOME)/rpmbuild/RPMS/noarch/openchami-$(VERSION)-$(RELEASE).noarch.rpm
	cp $< $@

clean:
	rm -rf $(HOME)/rpmbuild
	rm -f openchami.rpm
