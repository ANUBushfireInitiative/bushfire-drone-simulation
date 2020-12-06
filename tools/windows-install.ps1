# Update pip
py -3.8 -m pip install --upgrade pip setuptools wheel

# Install pre-commit
py -3.8 -m pip install pre-commit
# pre-commit install --install-hooks

# Install pylint
py -3.8 -m pip install pylint
# pylint --generate-rcfile > ~/.pylintrc

# Install sphinx for documentation
py -3.8 -m pip install sphinx
py -3.8 -m pip install sphinx-rtd-theme
py -3.8 -m pip install sphinx-autobuild
py -3.8 -m pip install sphinx-autodoc-typehints
mkdir docs/source/_static -Force

# Install bushfire_drone_simulation
py -3.8 -m pip install -e bushfire_drone_simulation

Write-Host "Congratulations! The ANU Bushfire Initiative Drone Simulation is now installed."
