APP ?= app.py
PYTHON ?= python

.PHONY: test run

test:
	$(PYTHON) -m pytest

run:
	streamlit run $(APP)
