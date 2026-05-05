CC = cc
CFLAGS = -O2 -Wall -Wextra

all: field25519

field25519: field25519.c
	$(CC) $(CFLAGS) -o $@ $<

test: field25519
	./field25519

clean:
	rm -f field25519

.PHONY: all test clean
