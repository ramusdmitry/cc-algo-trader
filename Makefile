# Define the directories where your Python code is located
PYTHON_SRC := src

# Define the command to run the linters
FLAKE8 := flake8
BLACK := black
PYLINT := pylint
ISORT := isort
AUTOPEP8 := autopep8 --in-place --aggressive --aggressive

# Default target to run all linters
all: lint

# Target to run flake8
flake8:
	$(FLAKE8) $(PYTHON_SRC)

# Target to run black
black:
	$(BLACK) $(PYTHON_SRC)

black-check:
	${BLACK} --check ${PYTHON_SRC}

# Target to run pylint
pylint:
	$(PYLINT) $(PYTHON_SRC)

isort:
	$(ISORT) $(PYTHON_SRC)

isort-check:
	${ISORT} --check-only ${PYTHON_SRC}

#autopep8:
#	@awk '/\.py$$/{print $$4}' pylint.log | xargs $(AUTOPEP8)

# Combined target to run all linters
lint: flake8 black-check isort-check pylint

# Combined target to run all formatters
format: isort black # autopep8

.PHONY: all flake8 black pylint lint