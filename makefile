# Variables
APP_NAME = app/app.py
VENV_DIR = venv
PYTHON = python3
PIP = $(VENV_DIR)/bin/pip
STREAMLIT = $(VENV_DIR)/bin/streamlit
PYTEST = $(VENV_DIR)/bin/pytest

# Ensure virtual environment exists and dependencies are installed
# Check Python version at the top of the file
MIN_PYTHON_VERSION = 3.8
PYTHON_VERSION_CHECK = $(shell $(PYTHON) -c "import sys; exit(0) if sys.version_info >= ($(MIN_PYTHON_VERSION),) else exit(1)" 2>/dev/null || echo fail)

$(VENV_DIR)/bin/activate: requirements.txt
ifneq ($(PYTHON_VERSION_CHECK),fail)
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -e .
	touch $(VENV_DIR)/bin/activate
else
	$(error "Python $(MIN_PYTHON_VERSION) or later is required.")
endif

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