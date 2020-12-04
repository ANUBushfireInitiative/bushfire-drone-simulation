# ANU Bushfire Initiative - Drone Simulation

This is a python application that allows the simulation of Drones for fast lightning strike investigation and potential suppression by a fleet of water bombers.

## Installation

This application requires a unix style operating system or terminal. On windows systems, this can be achieved using the windows subsystem for linux (WSL). The windows subsystem for linux can be installed by following the steps detailed [here](https://docs.microsoft.com/en-us/windows/wsl/install-win10).

### Setting up Python Environment

The python code in this application requires python 3.8 or greater. To maintain the integrity of other python applications on your system, it is highly recommended to use a separate python environment for the bushfire drone simulation, however it can also be installed directly if your python version meets the requirements.

__Installing a python environment__

To set up a separate python environment (recommended), we will use [pyenv](https://github.com/pyenv/pyenv) which allows us to isolate the bushfire drone simulation development environment and python version. To install pyenv, please follow the instructions detailed [here](https://realpython.com/intro-to-pyenv/). During this installation, you will get the warning

```bash
WARNING: seems you still have not added 'pyenv' to the load path.
# Load pyenv automatically by adding
# the following to ~/.bashrc:
```

To add this text to ~./bashrc, first copy the text, then run the command

```bash
echo '<copied_text>' >> ~./bashrc

To create a pyenv environment for this application, run the commands

```bash
pyenv install 3.8.5
pyenv virtualenv 3.8.5 <environment_name>
```

replacing ```[environment_name]``` with a name for the python environment (e.g. ```bushfires```). Then, prior to following the installation steps below and before each time using the ```bushfire_drone_simulation``` application, you will need to enter the python environment using the command

```pyenv activate <environment_name>```

You can now skip the section on *Installing with python directly* if you have successfully set up a pyenv environment.

__Installing with python directly__

To install the application directly without a separate python environment, the python and pip commands must reference a python installation with version at least 3.8. If python is not yet installed, this can likely be achieved with the following set of commands

```bash
sudo apt-get update
sudo apt-get install python3
sudo apt-get install python-is-python3
sudo apt-get install python3-pip
alias pip=pip3
```

To check your python version meets the requirements, please run the command ```python --version``` to confirm it is at least version 3.8. You may also have to run the command ```sudo -s``` prior to the installation command given below.

### Installing the Development Environment

To download the source code and install the application, please open a terminal, navigate to the folder in which you would like to perform the installation and run the commands

```bash
git clone https://github.com/ryanstocks00/anu-bushfire-initiative-simulation
cd anu-bushfire-initiative-simulation
source tools/install-dev-env
```

Congratulations! The ANU Bushfire Initiative's Drone Simulation is now succesfully installed and can be run using the command

```bash
bushfire_drone_simulation --help
```

## Documentation

The documentation for this application is a combination of manual and automatically generated components, primarily contained within the [docs/source](docs/source) directory. This consists of some graphical components which rely on the graphviz application which can be installed using the command

```bash
sudo apt-get install graphviz
```

After installing the development environment above, you can start a local documentation server by running the command

```bash
python tools/doc_server start_server
```

from within the root folder of the project. By default, this will host the documentation at http://localhost:8000. For more information about the application, contributing, or testing, please see this documentation.
