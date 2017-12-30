PYTHON = python3.6
VENV_PATH = ./venv
ACTIVATE = . $(VENV_PATH)/bin/activate;

clean:
	rm -rf $(VENV_PATH)

setup: deps

run:
	$(ACTIVATE) python billing.py

$(VENV_PATH):
	$(PYTHON) -m venv $(VENV_PATH)

deps: $(VENV_PATH)
	$(ACTIVATE) pip install -q -r requirements.txt -c constraints.txt

freeze: clean setup
	$(ACTIVATE) pip freeze > constraints.txt
