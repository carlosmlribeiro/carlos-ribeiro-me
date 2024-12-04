# Variables
APP_NAME = app/app.py
VENV_DIR = venv
PYTHON = python3
PIP = $(VENV_DIR)/bin/pip
STREAMLIT = $(VENV_DIR)/bin/streamlit
PYTEST = $(VENV_DIR)/bin/pytest

# Ensure virtual environment exists and dependencies are installed
$(VENV_DIR)/bin/activate: requirements.txt
	$(PYTHON) -m venv $(VENV_DIR)
	. $(VENV_DIR)/bin/activate && $(PIP) install --upgrade pip
	. $(VENV_DIR)/bin/activate && $(PIP) install -r requirements.txt
	. $(VENV_DIR)/bin/activate && $(PIP) install -e .
	touch $(VENV_DIR)/bin/activate

# Create a virtual environment and install dependencies
.PHONY: build
build: $(VENV_DIR)/bin/activate

# Run the Streamlit app
.PHONY: run
run: build
	. $(VENV_DIR)/bin/activate && $(STREAMLIT) run $(APP_NAME)

# Run tests
.PHONY: test
test: build
	. $(VENV_DIR)/bin/activate && PYTHONPATH=. $(PYTEST) tests/ -v

# Clean up the virtual environment
.PHONY: clean
clean:
	rm -rf $(VENV_DIR)
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf app/__pycache__
	rm -rf tests/__pycache__