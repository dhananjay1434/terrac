# Host build for the PURE domain layer only (no ESP-IDF). Any C compiler works.
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Isrc/domain
BUILD := build

.PHONY: test clean
test: $(BUILD)/test_canonical
	$(BUILD)/test_canonical

$(BUILD)/test_canonical: src/domain/canonical.c test/test_canonical.c | $(BUILD)
	$(CC) $(CFLAGS) $^ -o $@

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)
