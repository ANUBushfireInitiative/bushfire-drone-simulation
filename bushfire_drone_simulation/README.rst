Bushfire Drone Simulation
=========================

This is a python application that allows the simulation of drones for fast lightning strike investigation and potential suppression by a fleet of water bombers.
The main application can be run using the command ``bushfire_drone_simulation run-simulation``:

.. code-block:: bash

    Usage: bushfire_drone_simulation run-simulation [OPTIONS]

        Run bushfire drone simulation.

    Options:
        --help  Show this message and exit.


Required Input
--------------

Several input files are required to run the bushfire drone simulation. Most importantly is the parameters file,
detailing most of the parameters for the simulation. The program additionally utilises a number of csv files to specify
details such as times, locations and capacities or to run the simulation varying specific parameters to create multiple scenarios.

**Parameters File**

The parameters file is a JSON file containing all information (or paths to files containing information)
required to run the Bushfire Drone Simulation. The path to the parameters file from the current working directory
is taken as input to the run-simulation command. The default parameters filename (if none is specified) is 'parameters.json'.

The JSON parameters file should contain the following information formatted as indicated
(note that the ordering of these parameters does not matter however the nesting does):


*  The paths to the following csv files relative to the JSON parameter file:

    .. code-block:: json

        "water_bomber_bases_filename": "path_to_file",
        "uav_bases_filename": "path_to_file",
        "water_tanks_filename": "path_to_file",
        "lightning_filename": "path_to_file"

    The information provided in these files and the correct formatting is discussed below.

*  The path to a folder where the output of the simulation will be written to

    .. code-block:: json

        "output_folder_name": "path_to_output_folder"

    If this folder already exists and is not empty, the user will be prompted as to whether they wish to
    overwrite the current contents of the folder or respecify the output destination.

*  The following generic variables:

    .. code-block:: json

        "ignition_probability": "the probability a given lightning strike will ignite"


*  A dictionary containing the following information about UAVs

    .. code-block:: json

        "uavs": {
            "spawn_loc_file": "path_to_file",
            "attributes": {
                "flight_speed": "flight speed of uav in km/hr",
                "fuel_refill_time": "fuel refill time of uav in min",
                "range": "total range of uav traveling at 'flight_speed' with a full tank in km"
            }
        }

*  And a dictionary containing the following information about water bombers

.. code-block:: json

    "water_bombers": {
        "water_bomber_type_1": {
            "spawn_loc_file": "path_to_file",
            "attributes": {
                "flight_speed": "flight speed of water bomber in km/hr",
                "bombing_time": "bombing time of water bomber in min",
                "water_refill_time": "water refill time of water bomber in min",
                "fuel_refill_time": "fuel refill time of water bomber in min",
                "water_per_delivery": "water required for each suppression in L",
                "range_empty": "range of empty water bomber in km",
                "range_under_load": "range of loaded water bomber in km",
                "water_capacity": "water capacity of water bomber in L"
            }
        },
        "water_bomber_type_2": {
            "Same attribute structure as above"
        },
        "Additional water bombers can be added using the same structure shown above"
    }



**CSV File formats**

The paths to csv files specified above should contain the following information and format requirements:

*  water_bomber_bases_filename

    This file should specify the location of each water bomber base as well as the fuel capacity of each and
    what types of water bombers can refill there. This information should be formatted as follows:


    .. csv-table::
        :header: "latitude", "longitude", "capacity", "all", "water_bomber_type_1", "water_bomber_type_2"
        :widths: 7, 7, 7, 10, 10, 10

        -37.81,144.97,10000, 1, "", ""
        -38.068,147.06,20000, "", 1, ""


    The location and fuel capacity of the water base should be indicated in the first three columns.
    To denote an infinite capacity please enter "inf" rather than a number.
    To indicate the which types of water bombers the base can refill, the following columns should be
    labelled 'all' followed by the names of the water bombers (defined in the water bomber dictionary above).
    If the base can be accessed by any water bomber, a '1' should be placed in the 'all' column. To specify
    bases only being accessible by certain water bombers, the remaining columns should be used (placing a
    '1' to indicate that the base can be used and leaving blank otherwise).

    For example, in the table above, the base in the first row can be accessed by both types of
    water bomber whereas the base in the second row can only be accessed by the first.

*  uav_bases_filename

    This file should specify the location and capacity of each UAV base, it is assumed that all UAVs
    can access all UAV bases. This should be formatted as follows:

    .. csv-table::
        :header: "latitude", "longitude", "capacity"
        :widths: 7, 7, 7

        -37.81,144.97,10000

    With the location of the base indicated in the first two columns and the capacity (in L) indicated in the
    third, again using "inf" to indicate an infinite capacity.

*  water_tanks_filename

    Should be formatted exactly as the uav_bases_filename is formatted.

* lightning_filename

    The lighning file should contain the location and time of each lightning strike (not necessarily in
    chronological order). This should be formatted as follows:

    .. csv-table::
        :header: "latitude", "longitude", "time"
        :widths: 7, 7, 7

        -37.81,144.97,2020/12/13/10/20/30

    Note that the time should be of the form YYYY*MM*DD*HH*MM*SS where "*" represents any character,
    e.g. 2033-11/03D12*00?12 would be accepted.

*  spawn_loc_file

    The spawn locations file, required for each type of aircraft, designates the initial location of each
    aircraft. The should all be formatted as follows

    .. csv-table::
        :header: "latitude", "longitude"
        :widths: 7, 7

        -37.81,144.97


**Multiple Simulations**

In order to run multiple simulations at once from the same csv file, a few alterations to the above format
may be made. Firstly, any variables (including csv files) that would like to be varied between simulations
should be replaced with a "?" in the JSON parameters file.
The values of these variables should be recorded in a csv file. The title of each column of this csv
file should indicate the variable altered. Each row that follows contains a scenario to be run,
each of the parameters in the file should be specified for each scenario. The path to this file
(relative to the JSON parameter file) should be recorded in the JSON parameter file as follows

.. code-block:: json

    "scenario_parameters_filename": "path_to_file"

For example, the JSON parameters file

.. code-block:: json

    "scenario_parameters_filename": "scenario_parameters.csv"
    "ignition_probability": "?"

    "uavs": {
        "spawn_loc_file": "uav_spawn_locations.csv",
        "attributes": {
            "flight_speed": "?",
            "fuel_refill_time": 30,
            "range": 650
        }
    }

would require the file scenario_parameters.csv to be formatted as follows

.. csv-table::
    :header: "ignition_probability","uavs/attributes/fuel_refill_time"
    :widths: 7, 7

    "0.07", "30"
    "0.2", "25"
    "0.5", "20"

Note that all aircraft have a fuel_refill_time attribute so to distinguish between them the
nesting of the dictionary is used with '/' in between each nesting.

Optionally, the user may also select which scenarios they would like to run. This can be done by
adding an additional parameter to the parameters JSON file as follows:

.. code-block:: json

    "scenarios_to_run": [0, 2]

The indexes of the scenarios that will be run should be provided in the list, note that these
are 0 indexed. If all scenarios would like to be run then the list can be replaced by "all" or the
field can be excluded entirely.


**Example Input**

Finally, please see the following parameter file for example input to the simulation. To also view the csv files
required please see bushfire_drone_simulation/tests/input_data.

.. code-block:: json

    {
        "water_bomber_bases_filename": "base_locations.csv",
        "uav_bases_filename": "uav_base_locations.csv",
        "water_tanks_filename": "water_tank_locations.csv",
        "lightning_filename": "lightning.csv",
        "scenario_parameters_filename": "scenario_parameters.csv",
        "output_folder_name": "output",
        "scenarios_to_run": "all",
        "ignition_probability": 0.072,
        "uavs": {
            "spawn_loc_file": "uav_spawn_locations.csv",
            "attributes": {
                "flight_speed": "?",
                "fuel_refill_time": 30,
                "range": 650
            }
        },
        "water_bombers": {
            "helicopter": {
                "spawn_loc_file": "helicopter_spawn_locations.csv",
                "attributes": {
                    "flight_speed": 235,
                    "bombing_time": 1,
                    "water_refill_time": 30,
                    "fuel_refill_time": 30,
                    "water_per_delivery": 2875,
                    "range_empty": 650,
                    "range_under_load": 650,
                    "water_capacity": 11500
                }
            },
            "c130": {
                "spawn_loc_file": "helicopter_spawn_locations.csv",
                "attributes": {
                    "flight_speed": 235,
                    "bombing_time": 1,
                    "water_refill_time": 30,
                    "fuel_refill_time": 30,
                    "water_per_delivery": 2875,
                    "range_empty": 650,
                    "range_under_load": 650,
                    "water_capacity": 11500
                }
            }
        }
    }
