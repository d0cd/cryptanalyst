all: point

point: point.rs
	rustc -O -o $@ $<

test: point
	./point

clean:
	rm -f point

.PHONY: all test clean
