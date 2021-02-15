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

Parameters File
~~~~~~~~~~~~~~~

The parameters file is a JSON file containing all information (or paths to files containing information)
required to run the Bushfire Drone Simulation. The path to the parameters file from the current working directory
is taken as input to the run-simulation command. The default parameters filename (if none is specified) is 'parameters.json'.
To change the current working directory to the directory containing the parameters file, use the following
commands from the terminal:

.. code-block::

    cd directory_name
    ls

To either change or list sub directories respectively until the desired directory is reached.
Alternatively, specify the path to the JSON parameters file from the current working directory.

The JSON parameters file should contain the following information formatted as indicated
(note that the ordering of these parameters does not matter however the nesting does):


*  The paths to the following csv files relative to the JSON parameter file:

    .. code-block:: json

        {
            "water_bomber_bases_filename": "path_to_file",
            "uav_bases_filename": "path_to_file",
            "water_tanks_filename": "path_to_file",
            "lightning_filename": "path_to_file"
        }

    The information provided in these files and the correct formatting is discussed below.

*  The path to a folder where the output of the simulation will be written to

    .. code-block:: json

        {
            "output_folder_name": "path_to_output_folder"
        }

    If this folder already exists and is not empty, the user will be prompted as to whether they wish to
    overwrite the current contents of the folder or respecify the output destination.

*  The coordinator class of the UAVs and water bombers

    .. code-block:: json

        {
            "uav_coordinator": "Name of uav coordinator class",
            "wb_coordinator": "Name of water bomber coordinator class"
        }

    The coordinators are stored in two dictionaries in main.py which are as follows:

    .. code-block:: python

        UAV_COORDINATORS = {
            "MatlabUAVCoordinator": MatlabUAVCoordinator,
            "NewStrikesFirstUAVCoordinator": NewStrikesFirstUAVCoordinator,
            "InsertionUAVCoordinator": InsertionUAVCoordinator,
            "MinimiseMeanTimeUAVCoordinator": MinimiseMeanTimeUAVCoordinator,
        }

        WB_COORDINATORS = {
            "MatlabWBCoordinator": MatlabWBCoordinator,
            "NewStrikesFirstWBCoordinator": NewStrikesFirstWBCoordinator,
            "InsertionWBCoordinator": InsertionWBCoordinator,
            "MinimiseMeanTimeWBCoordinator": MinimiseMeanTimeWBCoordinator,
        }

    The provided name of the coordinator in the JSON file should be the key to the desired coordinator
    in the appropriate dictionary.

    The currently implemented coordinators are described below:

    - **MatlabUAVCoordinator**: Equivalent of the original matlab implementation. This simply assigns each lighning strike as it occurs to the UAV which will get to it the fastest when appended to it's queue of tasks.
    - **MatlabWBCoordinator**: Water bomber equivalent of MatlabUAVCoordinator.
    - **InsertionUAVCoordinator**: This is an improvement on the MatlabUAVCoordinator that allows the lighning strike to be inserted anywhere into the queue of tasks.
    - **InsertionWBCoordinator**: Water bomber equivalent of InsertionUAVCoordinator.
    - **MinimiseMeanTimeUAVCoordinator**: This is an improvement on the InsertionUAVCoordinator that minimizes the total increase in the average inspection time given an insertion into the UAV task queue.
    - **MinimiseMeanTimeWBCoordinator**: Water bomber equivalent of MinimiseMeanTimeUAVCoordinator.
    - **NewStrikesFirstUAVCoordinator**: This coordinator assigns each new lighning strike to the UAV that would currently be able to get there the fastest and then reassigns the lightning strikes that were assigned to that UAV prior. WARNING: This is very slow, and does not appear to improve on the basic matlab coordinator.
    - **NewStrikesFirstWBCoordinator**: Water bomber equivalent of NewStrikesFirstUAVCoordinator.

*  The following generic variables:

    .. code-block:: json

        {
            "uav_mean_time_power": 1,
            "wb_mean_time_power": 1,
            "target_maximum_inspection_time": 1,
            "target_maximum_suppression_time": 1,
            "ignition_probability": "the probability a given lightning strike will ignite"
        }

    ``uav_mean_time_power`` and ``wb_mean_time_power`` are only required when using the MinimiseMeanTimeUAVCoordinator and MinimiseMeanTimeWBCoordinator respectively. They control the power of the time that the program tries to minimize, e.g. a value of 1 will try to minimize the mean time whereas a value of 2 will try to minimize the mean(time^2).

    ``target_maximum_inspection_time`` and ``target_maximum_suppression_time`` (in hours) are similarly only required when using the MinimiseMeanTimeUAVCoordinator or MinimiseMeanTimeWBCoordinator.    They will try to avoid the coordinator reallocating aircraft such that the inspection/supression times
    exceed the target maximum provided. However if it is not possible for the coordinator to reallocate
    such that this is the case then the coordinator will select the allocation that minimises the mean time
    (to a given power as discussed above).

    ``ignition_probability`` is the probability of each strike igniting if not specified in the lightning input file.

*  A dictionary containing the following information about UAVs

    .. code-block:: json

        {
            "uavs": {
                "spawn_loc_file": "path_to_file",
                "attributes": {
                    "flight_speed": "flight speed of uav in km/hr",
                    "fuel_refill_time": "fuel refill time of uav in min",
                    "range": "total range of uav traveling at 'flight_speed' with a full tank in km"
                }
            }
        }

*  And a dictionary containing the following information about water bombers

.. code-block:: json

    {
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
    }


CSV File formats
~~~~~~~~~~~~~~~~

The paths to csv files specified above should contain the following information and format requirements.
Note that the column headers must follow the same naming conventions however the data that follows
is just sample input.

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

        -37.81,144.97,2020/12/13/10/20/30

    Note that the time can either be in the form YYYY*MM*DD*HH*MM*SS where "*" represents any character
    (e.g. 2033-11/03D12*00?12 would be accepted) or in minutes from time 0.
    Standardly the simulation would be run with randomised ignitions but if these would like to be
    specified by the user an additional column should be added containing a boolean for each strike
    indicating whether or not it ignited as follows:

    .. csv-table::
        :header: "latitude", "longitude", "time", "ignited"

        -37.81,144.97,2020/12/13/10/20/30,True

    Note that accepted boolean inputs are as follows:

    .. csv-table::
        :header: "Boolean", "Accepted Input"

        True, "1, 1.0, t, true, yes, y"
        False, "0, 0.0, f, false, no, n"

    With any capitalisations. False can also be indicated with an empty cell.

*  spawn_loc_file

    The spawn locations file, required for each type of aircraft, designates the initial location of each
    aircraft as well as it's inital conditions. The should all be formatted as follows

    .. csv-table::
        :header: "latitude", "longitude", "starting at base", "inital fuel"

        -37.81,144.97,True,0.9

    Where starting at base indicates whether the aircraft should start hovering at time 0 or not (indicated
    by a boolean, see above for accepted boolean input) and inital fuel a decimal between 0 and 1
    indicating the percentage capacity of the fuel tank the aircraft begins with.


Multiple Simulations
~~~~~~~~~~~~~~~~~~~~

In order to run multiple simulations at once from the same csv file, a few alterations to the above format
may be made. Firstly, any variables (including csv files) that would like to be varied between simulations
should be replaced with a "?" in the JSON parameters file.
The values of these variables should be recorded in a csv file. The title of each column of this csv
file should indicate the variable altered. Each row that follows contains a scenario to be run,
each of the parameters in the file should be specified for each scenario. The name of the scenario should be
indicated in the first column of the file which will be used in the output to distinguish between scenarios.
The path to this file (relative to the JSON parameter file) should be recorded in the JSON parameter file
as follows:

.. code-block:: json

    {
        "scenario_parameters_filename": "path_to_file"
    }

For example, the following portion of a JSON parameters file

.. code-block:: json

    {
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
    }

would require the file scenario_parameters.csv to be formatted as follows

.. csv-table::
    :header: "scenario_name","ignition_probability","uavs/attributes/fuel_refill_time"

    "s1", "0.07", "30"
    "s2", "0.2", "25"
    "s3", "0.5", "20"

Note that all aircraft have a fuel_refill_time attribute so to distinguish between them the
nesting of the dictionary is used with '/' in between each nesting.



Example Input
~~~~~~~~~~~~~

Finally, please see the following parameter file for example input to the simulation.
To also view the csv files required and examples for how to run multiple simulations,
please see bushfire_drone_simulation/example_input.

.. code-block:: json

    {
        "water_bomber_bases_filename": "base_locations.csv",
        "uav_bases_filename": "uav_base_locations.csv",
        "water_tanks_filename": "water_tank_locations.csv",
        "lightning_filename": "lightning.csv",
        "scenario_parameters_filename": "scenario_parameters.csv",
        "output_folder_name": "output",
        "uav_coordinator": "MatlabUAVCoordinator",
        "wb_coordinator": "MatlabWBCoordinator",
        "uav_mean_time_power": 1,
        "wb_mean_time_power": 1,
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



Simulation Output
-----------------

The output from the simulation consits of 4 files and a simulation input folder for each scenario
which can be found in the output folder. The files and folder are denoted with their associated
scenario name (specified in the scenario parameters file (see Required Input)) and then a name describing
the output they contain. The contents of the 4 files and simulation input folder are described below.

Simulation Input Folder
~~~~~~~~~~~~~~~~~~~~~~~

The simulation input folder contins the JSON parameters file used to run the simulation as well as all
relavent csv files. Relavent csv files include all those referred to in JSON parameters as well as any
additional files referred to in the scenario parameters csv file (for example if different scenarios
used different UAV spawn locations).

The purpose of this folder is for the user to recall the input data that returned
the output of the simulation, not for ease of running the simulation again with these parameters.
Therefore, the csv files are placed in the same level directory as the JSON parameters file,
that is, any sub directories that previously existed in the input data will not be included. This means
that the paths specified in the JSON parameters may no longer be correct so in order to run the simulation
again the user will need to correct these paths.

Inspection Times Plot
~~~~~~~~~~~~~~~~~~~~~
This png file contains 4 plots which are as follows:

* Histogram of UAV inspection times
    This plot as the name describes simply presents a histogram of the inspection times for each strike
    in the specified csv file. Note that if a strike was not inspected it is not included in this plot
    (rather an error message is presented on the terminal alterting the user to this fact).

* Histogram of suppression times
    Similarly to the inspection times plot, this plot presents a histogram of the suppression times for each
    strike not including any strikes that did not ignite or that did ignite but were not suppressed
    (again a error will be displayed on the terminal if this is the case).

* Lightning strikes inspected per water bomber
    Another histogram indicating how many strikes each water bomber inspected.

* Water tank levels after suppression
    This histogram depicts both the intial capacity and the final capacity after the simulation is complete
    of all water tanks specified in the input data. Note that if the water tanks have an infinite
    capacity these are not displayed on the histogram.


Simulation Output
~~~~~~~~~~~~~~~~~

This csv file simply contains the ID number, position, spawn time, inspection time and supression time
of every strike from the scenario. If a strike was not inspected or suppressed (either because it
did not ignite or there were no water bombers avalible), the inspected or suppression time will be
denoted 'N/A'.

UAV Event Updates
~~~~~~~~~~~~~~~~~

The UAV event updates csv file contains all movements of the UAVs throughout the entire simulation.
These updates are listed in chronological order so if a particular drones movements would like to
be analysed it is recommened that a filter function is used to filter out the desired data.
Each movement update of the UAV contains the following information:

* **UAV ID** - the UAV in question
* **Latitude** - the latitude from which the UAV is departing from
* **Longitude** - the longitude from which the UAV is departing from
* **Time** (min) - the absolute time (relative to 0) of departure
* **Distance travelled** (km) - the distance travelled since the previous update
* **Distance hovered** (km) - the distance hovered since the previous update
* **Fuel capacity** (%) - the fuel capacity upon departure
* **Current range** (km) - the range of the aircraft upon departure
* **Status** - what the aircraft is now doing
* **Next updates** - what the aircraft will do in future if the coordinator does not tell it otherwise

Water Bomber Event Updates
~~~~~~~~~~~~~~~~~~~~~~~~~~

The water bomber event updates are structed exactly as the UAV updates however they include one
additional column:

* **Water capacity** (L): the water on board of the aircraft upon departure
