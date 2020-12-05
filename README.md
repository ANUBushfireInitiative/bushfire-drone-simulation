[![ANU Bushfire Initiative Drone Logo](docs/source/drone_simulation_logo_with_title.png)](https://github.com/ryanstocks00/anu-bushfire-initiative-simulation)

This is a python application that allows the simulation of drones for fast lightning strike investigation and potential suppression by a fleet of water bombers.

## Installation

This application has been designed to run on either a windows or a unix style operating system or terminal. On windows systems, this can be achieved using the windows subsystem for linux (WSL). The windows subsystem for linux can be installed by following the steps detailed [here](https://docs.microsoft.com/en-us/windows/wsl/install-win10). We recommend installing one of the Ubuntu versions.

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
echo '<copied_text>' >> ~/.bashrc
```

To create a pyenv environment called bushfires for this application, run the commands

1. ```pyenv install 3.8.5```
2. ```pyenv virtualenv 3.8.5 bushfires```

Then, prior to following the installation steps below and before each time using the ```bushfire_drone_simulation``` application, you will need to enter the bushfires python environment using the command

```pyenv activate bushfires```

You can now skip the section on *Installing with python directly* if you have successfully set up a pyenv environment.

__Installing with python directly__

To install the application directly without a separate python environment, the python and pip commands must reference a python installation with version at least 3.8. If python is not yet installed, this can likely be achieved with the following set of commands

1. ```sudo apt-get update```
2. ```sudo apt-get install python3```
3. ```sudo apt-get install python-is-python3```
4. ```sudo apt-get install python3-pip```
5. ```alias pip=pip3```

To check your python version meets the requirements, please run the command ```python --version``` to confirm it is at least version 3.8. You may also have to run the command ```sudo -s``` prior to the installation command given below.

### Installing the Development Environment

To download the source code and install the application, please open a terminal, navigate to the folder in which you would like to perform the installation and run the commands

1. ```git clone https://github.com/ryanstocks00/anu-bushfire-initiative-simulation```
2. ```cd anu-bushfire-initiative-simulation```
3. ```source tools/install-dev-env```

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
python tools/doc_server.py start-server
```

from within the root folder of the project. By default, this will host the documentation at http://localhost:8000. For more information about the application, contributing, or testing, please see this documentation.


## Windows Installation Instructions

On a windows system, we will install the drone simulation application using Windows PowerShell. You can open Windows PowerShell by opening File Explorer, navigating to the folder in which you want to start PowerShell, then typing powershell into the address bar and hitting enter. Alternately, you can start WindowsPowershell as an administrator by right-clicking the windows start button and selecting ```Windows PowerShell (Admin)``` and then navigating to the target folder using ```cd``` (change directory).

### Installing Chocolatey

```bash
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iwr https://chocolatey.org/install.ps1 -UseBasicParsing | iex
```

### Installing python with chocolatey

```choco install python3 --version=3.8.5```

### Installing pyenv

```
choco install pyenv-win
```

then start a new Powershell

1. ```pyenv install 3.8.5```
2. ```pyenv local 3.8.5```

### Installing python

```set-executionpolicy RemoteSigned```

Open a Windows PowerShell as administrator and check the version of python that is installed using the command ```python --version```. If python is not installed or the version is below 3.8, we will need to install a newer version of python. Likewise if any of the following steps do not work, it may be because python is incorrectly installed (There appear to be some bugs in numpy for python 3.9 in particular), in which case uninstall all existing versions of python and then follow these installation instructions. To install python version 3.8.5, first download the relevant python installer from [here](https://www.python.org/downloads/release/python-385/) (likely [Windows x86-64 executable installer](https://www.python.org/ftp/python/3.8.5/python-3.8.5-amd64.exe)). Then run the installer, selecting custom installation ensuring to select both *install for all users*, *add python to PATH* and *add python to environment variables*.

## Installing Git

```choco install git.install```

By default, Windows PowerShell does not come with the useful version control system git. Hence if git is not installed on your system (this can be checked using the command ```git --version``` in PowerShell), please install it by following the instructions [here](https://phoenixnap.com/kb/how-to-install-git-windows).

## Downloading and Installing the Bushfire Simulation

Now that we have python and git installed, open a PowerShell window in the folder that you would like to download the bushfire simulation application and run the following commands:

1. ```git clone https://github.com/ryanstocks00/anu-bushfire-initiative-simulation```
2. ```cd anu-bushfire-initiative-simulation```

#

Update pip (python -m pip install --upgrade pip setuptools wheel)
install with pip install -e



3. ```source tools/install-dev-env```
