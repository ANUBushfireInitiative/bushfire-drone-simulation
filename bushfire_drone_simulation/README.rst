Bushfire Drone Simulation
=========================

This is a python application that allows the simulation of drones for fast lightning strike investigation and potential suppression by a fleet of water bombers.

The main application can be run using the command ``bushfire_drone_simulation``. It can be operated via either a command line or graphical interface. The graphical interface can be started with the command ``bushfire_drone_simulation gui`` or alternatively the simulation can be run via the command line using ``bushfire_drone_simulation run-simulation [PARAMATERS_FILENAME]``

Required Input
--------------

Several input files are required to run the bushfire drone simulation. The primary input is the parameters file,
which details most of the parameters for the simulation in json format. The program additionally utilises several csv files to specify
details such as the times and locations of strikes and the capacities of water reservoirs.

Parameters File
~~~~~~~~~~~~~~~

The parameters file is a JSON file containing all of the information required to run the Bushfire Drone Simulation. The path to the parameters file is taken as input to the run-simulation command or can be selected via ``File -> New Simulation`` in the GUI. The default parameters filename (if none is specified) is 'parameters.json'.

The JSON parameters file should contain the following information formatted as indicated
(note that following the JSON specification the ordering of these parameters does not matter however the nesting does):

*  The paths to each of the csv files relative to the parameter file:

    .. code-block:: json

        {
            "water_bomber_bases_filename": "path_to_file",
            "uav_bases_filename": "path_to_file",
            "water_tanks_filename": "path_to_file",
            "lightning_filename": "path_to_file"
        }

    The information required in these files and the correct formatting is discussed below.

*  The path to a folder to write the output of the simulation

    .. code-block:: json

        {
            "output_folder_name": "path_to_output_folder"
        }

    If this folder already exists and is not empty, the user will be prompted as to whether they wish to
    overwrite the current contents of the folder.

*  The coordinator type for the UAVs and water bombers

    .. code-block:: json

        {
            "uav_coordinator": "Name of uav coordinator class",
            "wb_coordinator": "Name of water bomber coordinator class"
        }

    Several coordinators are provided with the application which prioritise strikes differently. The different coordinators are stored in two dictionaries in simulator.py as follows:

    .. code-block:: python

        UAV_COORDINATORS: Dict[str, Union[Type[UAVCoordinator]]] = {
            "SimpleUAVCoordinator": SimpleUAVCoordinator,
            "InsertionUAVCoordinator": InsertionUAVCoordinator,
            "MinimiseMeanTimeUAVCoordinator": MinimiseMeanTimeUAVCoordinator,
            "ReprocessMaxTimeUAVCoordinator": ReprocessMaxTimeUAVCoordinator,
        }

        WB_COORDINATORS: Dict[str, Union[Type[WBCoordinator]]] = {
            "SimpleWBCoordinator": SimpleWBCoordinator,
            "InsertionWBCoordinator": InsertionWBCoordinator,
            "MinimiseMeanTimeWBCoordinator": MinimiseMeanTimeWBCoordinator,
            "ReprocessMaxTimeWBCoordinator": ReprocessMaxTimeWBCoordinator,
        }

    The provided name of the coordinator in the JSON file should be the key to the desired coordinator
    in the appropriate dictionary.

    The currently implemented coordinators are described below:

    - **SimpleUAVCoordinator**: Equivalent of the original matlab implementation. This simply assigns each lightning strike as it occurs to the UAV which will get to it the fastest when appended to it's queue of tasks.
    - **SimpleWBCoordinator**: Water bomber equivalent of SimpleUAVCoordinator.
    - **InsertionUAVCoordinator**: This is an improvement on the SimpleUAVCoordinator that allows the lightning strike to be inserted anywhere into the queue of tasks of each aircraft.
    - **InsertionWBCoordinator**: Water bomber equivalent of InsertionUAVCoordinator.
    - **MinimiseMeanTimeUAVCoordinator**: This is an improvement on the InsertionUAVCoordinator that minimizes the total increase in the average inspection time given an insertion into the UAV task queue.
    - **MinimiseMeanTimeWBCoordinator**: Water bomber equivalent of MinimiseMeanTimeUAVCoordinator.
    - **ReprocessMaxTimeUAVCoordinator**: This is an extension to the MinimiseMeanTimeUAVCoordinator that aims to reduce the maximum inspection time by reprocessing the strike with the largest inspection time.
    - **ReprocessMaxTimeWBCoordinator**: Water bomber equivalent of ReprocessMaxTimeUAVCoordinator.

*  The following configuration variables:

    .. code-block:: json

        {
            "uav_mean_time_power": 1,
            "wb_mean_time_power": 1,
            "target_maximum_inspection_time": 1,
            "target_maximum_suppression_time": 1,
            "ignition_probability": "the probability a given lightning strike will ignite"
        }

    ``uav_mean_time_power`` and ``wb_mean_time_power`` are only required when using the MinimiseMeanTimeUAVCoordinator and MinimiseMeanTimeWBCoordinator respectively. They control the power of the time that the program tries to minimize, e.g. a value of 1 will try to minimize the mean time whereas a value of 2 will try to minimize the mean (time^2).

    ``target_maximum_inspection_time`` and ``target_maximum_suppression_time`` (in hours) are similarly only required when using the MinimiseMeanTimeUAVCoordinator or MinimiseMeanTimeWBCoordinator. They will try to avoid the coordinator reallocating aircraft such that the inspection/supression times
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
                    "inspection_time": "time spent inspecting strike in min"
                }
                "prioritisation_function": "how uavs should prioritise lightning strikes, see below."
            }
        }

*  A dictionary containing the following information about water bombers

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
                "spawn_loc_file": "path_to_file",
                "attributes": {
                    "Same attribute structure as above"
                }
            },
            "Additional water bombers can be added using the same structure shown above"
        }
    }

*  And an optional dictionary containing the following information about how the coordinator should treat unassigned drones.

    If this dictionary is included in the parameters file, then at the end of every time interval dt,
    the unassigned aircraft will move according to the following instructions:
    they will be attracted to any targets provided in the target file (details specified below),
    and repelled from all other unassigned aircraft and the closest point on the boundary (given in the boundary
    polygon file, details below). These attractions and repulsions are definied by the following formula

    .. math::

        const \times (dist\ from\ unassigned\ aircraft\ to\ position) ^ {power}

    where the const and power are defined in the parameters file.


    If these instructions tell a drone to leave the boundary, it will
    ignore these instrctions and remain stationary (hovering). If an aircraft is found outside the boundary
    it will fly towards the provided centre coordinates.

.. code-block :: json

    {
        "unassigned_drones": {
            "targets_filename": "input_data/targets.csv",
            "boundary_polygon_filename": "input_data/boundary_polygon.csv",
            "dt": "time in seconds between unassigned aircraft updates",
            "uav_repulsion_const": "uav repulsion coefficient (positive for repulsion)",
            "uav_repulsion_power": "uav repulsion power (adviced to be negative)",
            "target_attraction_const": "target attraction coefficient (positive for attraction)",
            "target_attraction_power": "target attraction power (adviced to be negative)",
            "boundary_repulsion_const": "boundary repulsion coefficient (positive for repulsion)",
            "boundary_repulsion_power": "boundary repulsion power (adviced to be negative)",
            "centre_lat": "centre latitude for drones outside boundary to return to",
            "centre_lon": "centre longitude for drones outside boundary to return to",
            "output_plots": "Optional. If 'true' will output plots in the specified output folder, otherwise will not."
        }
    }


CSV File formats
~~~~~~~~~~~~~~~~

The paths to csv files specified above should contain the following information and formatting.
Note that the column headers must follow the same naming conventions however the data that follows
is just sample input.

*  water_bomber_bases_filename

    This file should specify the location of each water bomber base as well as what types of water
    bombers can refill there. It is assumed all water bomber bases have an infinite capacity.
    This information should be formatted as follows:


    .. csv-table::
        :header: "latitude", "longitude", "all", "water_bomber_type_1", "water_bomber_type_2"
        :widths: 7, 7, 7, 10, 10, 10

        -37.81,144.97, 1, "", ""
        -38.068,147.06, "", 1, ""


    The location of the water bomber base should be indicated in the first two columns.
    To indicate which types of water bombers the base can refill, the following columns should be
    labelled 'all' followed by the names of the water bombers (defined in the water bomber dictionary above).
    If the base can be accessed by any water bomber, a '1' should be placed in the 'all' column. To specify
    bases only being accessible by certain water bombers, the remaining columns should be used (placing a
    '1' to indicate that the base can be used and leaving blank otherwise).

    For example, in the table above, the base in the first row can be accessed by both types of
    water bomber whereas the base in the second row can only be accessed by the first.

*  uav_bases_filename

    This file should specify the location of each UAV base. It is assumed that all UAVs
    can access all UAV bases and all bases have an infinite capacity. This should be formatted as follows:

    .. csv-table::
        :header: "latitude", "longitude"

        -37.81,144.97


*  water_tanks_filename

This file should specify the location and capacity of each water tank. It is assumed that all water bombers can access all water tanks. This should be formatted as follows:

    .. csv-table::
        :header: "latitude", "longitude", "capacity"

        -37.81,144.97,10000

With the location of the water tank indicated in the first two columns and the capacity (in litres) indicated in the third.
Alternatively inf" can be used to indicate an infinite capacity.

* lightning_filename

    The lightning file should contain the location and time of each lightning strike (not necessarily in
    chronological order) and optionally a risk rating. This should be formatted as follows:

    .. csv-table::
        :header: "latitude", "longitude", "time", "risk_rating"

        -37.81,144.97,2020/12/13/10/20/30,0.5

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
    aircraft as well as it's inital conditions. This should be formatted as follows

    .. csv-table::
        :header: "latitude", "longitude", "starting at base", "inital fuel"

        -37.81,144.97,True,0.9

    Where starting at base indicates whether the aircraft should start hovering at time 0 or not (indicated
    by a boolean, see above for accepted boolean input) and inital fuel a decimal between 0 and 1
    indicating the percentage capacity of the fuel tank the aircraft begins with.

*  target_file

    The optional targets file designates the locations and active duration of various targets that
    aircraft should travel towards when unassigned. Note that this file does not have to be specified
    even if an unassigned_drones dictionary is included.

    .. csv-table::
        :header: "latitude", "longitude", start time,finish time

        -37.81,144.97,0,80000

    Note that it is possible to enter "inf" to indicate an infinite end time.

* boundary_polygon_file

    The optional boundary polygon file, required if the unassigned_drones dictionary is included,
    designates the verticies of a boundary polygon for the simulation area.

    .. csv-table::
        :header: "latitude", "longitude"

        -37.81,144.97


Multiple Simulation Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run multiple simulations at once from the same csv file, a few alterations to the above format
can be made. Firstly, any variables (including csv files) that would like to be varied between simulations
should be replaced with a "?" in the JSON parameters file.
The values of these variables should be recorded in a csv file. The title of each column of this csv
file should match the variable being altered. Each row that follows contains a scenario to be run.
All of the parameters in the file should be specified for each scenario. The name of the scenario should be
indicated in the first column of the file which will be used in the output to distinguish between scenarios.
The path to this file (relative to the parameter file) should be recorded in the JSON parameter file
with an additional variable as follows:

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

    "Senario 1", "0.07", "30"
    "Scenario 2", "0.2", "25"
    "Scenario 3", "0.5", "20"

Note that all aircraft have a fuel_refill_time attribute so to distinguish between them the nesting is indicated with '/'.


Example Input
~~~~~~~~~~~~~

The following is a full example of the contents for the paramaters JSON file.
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
        "uav_coordinator": "SimpleUAVCoordinator",
        "wb_coordinator": "SimpleWBCoordinator",
        "uav_mean_time_power": 1,
        "wb_mean_time_power": 1,
        "target_maximum_inspection_time": 0.5,
        "target_maximum_suppression_time": 1,
        "ignition_probability": 0.072,
        "uavs": {
            "spawn_loc_file": "uav_spawn_locations.csv",
            "attributes": {
                "flight_speed": "?",
                "fuel_refill_time": 30,
                "range": 650,
                "inspection_time": 1
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

The output from the simulation consists of 4 files for each scenario, a simulation input folder, and a gui.json file which contains the required information to open the simulation output in the GUI.
All of these outputs can be found in the output folder specified. The files and folder are denoted with their associated
scenario name (specified in the scenario parameters file, see Required Input) and then a name describing
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

This csv file contains the ID number, position, spawn time, inspection time and supression time
of every strike from the scenario. If a strike was not inspected or suppressed (either because it
did not ignite or there were no water bombers available), the inspected or suppression time will be
denoted 'N/A'.

UAV Event Updates
~~~~~~~~~~~~~~~~~

The UAV event updates csv file contains all movements of the UAVs throughout the entire simulation.
These updates are listed in chronological order so if a particular drones movements would like to
be analysed it is recommended that a filter function is used to filter out the desired data.
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

GUI
---

The bushfire drone simulation also comes with a graphical user interface for viewing the simulation overlayed on a map (thanks to `OpenStreetMap <https://www.openstreetmap.org/>`_). To run the GUI use the command ``bushfire_drone_simulation gui``. You can then select to open a previously run simulation with ``File -> Open`` and then selecting the ``gui.json`` file in the output or you can run a new simulation with ``File -> New Simulation`` and then selecting the parameters JSON file for the simulation you would like to run.
