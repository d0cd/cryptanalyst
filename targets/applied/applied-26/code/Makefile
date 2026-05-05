all: scalar

scalar: scalar.rs
	rustc -O -o $@ $<

test: scalar
	./scalar

clean:
	rm -f scalar

.PHONY: all test clean
