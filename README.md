[![ANU Bushfire Initiative Drone Logo](docs/source/drone_simulation_logo_with_title.png)](https://github.com/ryanstocks00/anu-bushfire-initiative-simulation)

This is a python application that allows the simulation of drones for fast lightning strike investigation and potential suppression by a fleet of water bombers.

# Installation

This application has been designed to run on either a windows or a unix style operating system or terminal. The windows installation will be sufficient if active development is not required, however active development will be much easier on a unix style system. On windows systems, this can be achieved using the windows subsystem for linux (WSL). The windows subsystem for linux can be installed by following the steps detailed [here](https://docs.microsoft.com/en-us/windows/wsl/install-win10).

## Windows Installation Instructions

On a windows system, we will install the drone simulation application in Windows PowerShell. To open Windows PowerShell as an administrator, right-click the windows start button and select ```Windows PowerShell (Admin)``` and then select "Yes" when prompted.

### Installing Chocolatey

We will use the package manager Chocolatey to install the correct versions of python. To install Chocolatey, open Windows PowerShell as an administrator and run the command:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force;
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072;
iwr https://chocolatey.org/install.ps1 -UseBasicParsing | iex
```

You may need to reopen PowerShell before using choco (Chocolatey) in the next step.

### Installing Python

As this is a python application, we first need to install python. We will use Chocolatey to install version 3.8.5. Open Windows PowerShell as an administrator and run the command:

```powershell
choco install -y python3 --version=3.8.5 --force
```

If the installation is successful, python 3.8 can then be accessed using the command ```py -3.8``` (and exited using the command ```exit()```).

### Installing Git

By default, Windows PowerShell does not come with the useful version control system git. Hence if git is not installed on your system (this can be checked using the command ```git --version``` in PowerShell, if PowerShell displays a version of git this indicates git is already installed), please install it using the following command:

```powershell
choco install -y git.install --params "/GitAndUnixToolsOnPath /SChannel /NoAutoCrlf"
```

### Setting the Execution Policy

We also need to change the PowerShell execution policy to allow us to run external scripts by running the following command in PowerShell (with admin):

```powershell
set-executionpolicy remotesigned
```

### Downloading and Installing the Bushfire Simulation

Now that we have python and git installed, open a PowerShell window in the folder that you would like to download the bushfire simulation application. This can be done by opening File Explorer, navigating to the folder in which you want to start PowerShell, then typing powershell into the address bar and hitting enter. Alternately, you can start WindowsPowershell as before and then navigating to the target folder using ```cd``` (change directory). You can now run the following commands to download and install the application:

1. ```git clone https://github.com/ryanstocks00/anu-bushfire-initiative-simulation```
2. ```cd anu-bushfire-initiative-simulation```
3. ```.\tools\windows-install.ps1```

Congratulations! The ANU Bushfire Initiative's Drone Simulation is now (hopefully) successfully installed and can be run using the command

```powershell
bushfire_drone_simulation --help
```

You can also now start a documentation server by following the documentation instructions below.

## Unix installation instructions (Including WSL)

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

### Downloading and Installing the Bushfire Simulation

To download the source code and install the application, please open a terminal, navigate to the folder in which you would like to perform the installation and run the commands

1. ```git clone https://github.com/ryanstocks00/anu-bushfire-initiative-simulation```
2. ```cd anu-bushfire-initiative-simulation```
3. ```source tools/install-dev-env```

Congratulations! The ANU Bushfire Initiative's Drone Simulation is now (hopefully) successfully installed and can be run using the command

```bash
bushfire_drone_simulation --help
```

## Documentation

The documentation for this application is a combination of manual and automatically generated components, primarily contained within the [docs/source](docs/source) directory. This consists of some graphical components which rely on the graphviz application. This is often preinstalled but on a unix system it may need to be installed using the command

```bash
sudo apt-get install graphviz
```

You can now start a local documentation server by running the command

**Windows:**
```bash
py -3.8 tools/doc_server.py start-server
```

**Unix:**
```bash
python tools/doc_server.py start-server
```

from within the root folder of the project. By default, this will host the documentation at http://localhost:8000. For more information about the application, contributing, or testing, please see this documentation.



# Input Files Format
Follows is a overview of how inputs to the program should be structred.
## Parameters File
The parameters file is a JSON file containing the following information (note that the ordering of these parameters does not matter however the nesting does):
The paths to the following files (the formatting of which is outlined below) named as indicated:
```json
    {"water_bomber_bases_filename": "path_to_file",
    "uav_bases_filename": "path_to_file",
    "water_tanks_filename": "path_to_file",
    }
    ```
The following generic variables:
```json
    {"ignition_probability": 0.072,
    }
    ```
A dictionary containing the following information about UAVs
```json
    {"uavs":
        {"spawn_loc_file": "csv_data/uav_spawn_locations.csv",
        "attributes": {
            "flight_speed": 235,
            "fuel_refill_time": 30,
            "range": 650
        }
    }
    }
```
