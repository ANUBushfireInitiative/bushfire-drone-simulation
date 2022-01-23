# Update pip
py -3.8 -m pip install --upgrade pip setuptools wheel

# Install pre-commit
py -3.8 -m pip install --upgrade pre-commit
pre-commit install --install-hooks
pre-commit autoupdate

# Install pylint
py -3.8 -m pip install --upgrade pylint

# Install sphinx for documentation
py -3.8 -m pip install sphinx sphinx-rtd-theme sphinx-autobuild sphinx-autodoc-typehints
mkdir docs/source/_static -Force

# Install coverage for testing
py -3.8 -m pip install coverage

# Install bushfire_drone_simulation
py -3.8 -m pip install -e bushfire_drone_simulation

Write-Host "Congratulations! The ANU Bushfire Initiative Drone Simulation is now installed."
