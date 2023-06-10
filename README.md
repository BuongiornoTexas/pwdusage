<!---
# cspell: ignore venv beautifulsoup tzdata numpy simplejson datasource pypi pwdusage
---> 

![Usage detail 7d](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/f2a014e6-4f17-437e-8ab0-409f5126ea7f)

# Change Log

I'm tracking progress towards v1.0 at: 
https://github.com/BuongiornoTexas/pwdusage/issues/1.

From v0.9.4, the python/microservice is feature complete. Releases up to v1.0 will 
address bug fixes and documentation (and incorporate any new agent contributions). 

## Breaking

This section notes any breaking changes, from newest to oldest.

- **v0.9.4**. 
  - Project renamed to pwdusage to give a shorter name for pypi package.
  - Separated python component from dashboard components. In the interim, the latter can
  be found at:
  https://github.com/BuongiornoTexas/Powerwall-Dashboard/tree/main/tools/usage-service,
  and should be integrated into the main tree after beta phase.
  - First release of python package from pypi, new install procedure.
- **v0.9.1**. "supplyPriority" in `usage.json` renamed to "supply_priority" to improve
naming consistency.

## New Features

**v1.0.0** 
- Documentation for building and testing docker image, instructions for adding
the docker container to the Powerwall-Dashboard stack. 
- Documentation for grafana configuration.
- Sample dashboards added to the Powerwall-Dashboard repo.

**v0.9.1**
- Resampling to more useful periods for bar charts.
- Payload features implemented. You can now turn resampling on/off, request summary 
reports, and select year to date or month to date reporting (which ignore the grafana
range).
- Month anchor for annual reporting, weekday anchor for monthly reporting by week.
- CLI interface to dump out csv format files for debugging.

# pwdusage

Usage (mainly time of use) proxy microservice for Powerwall-Dashboard

The following dot points outline key elements of the usage engine:

- The usage engine provides a framework for time of use energy and cost reporting.
- The framework assumes that a utility's supply agreement/contract can be broken into: a 
usage plan that describes the mostly-constant elements of the contract, and a calendar
that specifies which usage plan should be active at any time and the variable parameters
of the plan, such as supply costs, feed in tariffs and savings rates.
- The engine can handle multiple usage plans, where each plan is broken into a number
of seasons, and specifies the usage agent that will be used to calculate energy costs
and savings. 
- Each season is specified as:
    - Repeating groups of week days in a season. For example, weekday and weekends.
    - Repeating tariff periods within each day of the group, where each tariff is active
    for a portion of that day. For example, Peak, 
    Off-Peak, Shoulder, Super-Peak.
- A calendar which specifies when each usage plan/season is active, and provides 
cost/savings rate data that should be used while the calendar entry is active. The 
calendar mechanism is designed to allow compact changes of seasons and rate tables.
- It provides a default simple agent that calculates costs and savings based on energy 
use in each tariff period.
- **Very importantly:** It provides hooks for implementing other usage plans, such as 
tariffs based on tiered consumption. I'm happy to provide assistance in putting these
together, but I'm hoping most of the work will be done by the people on those usage
plans.

## Implementation

The usage engine is implemented as proxy layer between InfluxDB and grafana. This 
approach the following benefits:

1) The usage engine does not modify data in InfluxDB.
2) It is relatively easy to implement multiple usage plan types.
3) It can be configured via a json file and reset/restarted without needing to restart
the pypowerwall server or influx instance (not applicable while developing new usage
agents).
4) It's easy to test the effects of different tariff types on historical data (albeit,
the historical data may not reflect optimisation for the tariff).

# Setup

This section details setup for end users. Developers and users who wish to use the CLI
components should refer to 
["Installation for development/testing"](#installation-for-developmenttesting), which
details setting up a local server instance running under python.

All of the script and configuration files referred to in this document can be found in
the `tool/usage-service` subfolder of the 
[`Powerwall-Dashboard` repo](https://github.com/jasonacox/Powerwall-Dashboard). (As 
they belong with the Dashboard rather the python service.)

(If you can't find files that this document refers to, it is possible that this
version of `pwdusage` contains files that have not yet been committed to the main
repository - check https://github.com/BuongiornoTexas/Powerwall-Dashboard for work in
progress).

## Open firewall port

Decide which port the usage micro-service will use and make the changes required to
allow your grafana host to access this port (and any other machine that might need 
access). For example, I'm using ufw on my local network:
```
ufw allow from 192.168.xxx.0/24 to any port 9050 proto tcp
```

## Build Docker Image

I have provided utility scripts to build the docker image for your local machine. 
Depending on demand, this may become a distributed image in the future. 

Open a terminal and navigate to the `tools/usage-service` sub-folder of 
`Powerwall-Dashboard`. In this folder generate the image using:
```
bash build.sh
```
Note for developers: This script will delete any existing `pwdusage` images and 
containers (if you are a normal end user, this is most likely what you want to happen).

## Test Docker Image

This is an optional step which may be useful for trouble shooting. The test process
is as follows:

- Navigate to the `tools/usage-service` sub-folder of `Powerwall-Dashboard`.
- Copy the `example_usage.json` file to `usage.json` in the `usage-service` folder.
- Edit `usage.json` so that file  so that `influx_url` points at your influx server
(probably the same machine as your Powerwall-Dashboard) and, optionally, set the correct
 `timezone` for your region.
- Run a test script which performs the following actions:
  - Stops and deletes the `pwdusage` container.
  - Creates and start a new `pwdusage` container configured by the test `usage.json`.
  - Pauses while you check the server status.
  
  The test script command is:
  ```
  bash test_service.sh
  ```

- Check that the usage server is responding by pointing a web browser at
`http://server.address:<port>/usage_engine`. If everything is as it should be, you
 should see a page containing the message:

  ```
  Usage Engine Status	"Engine OK, tariffs (re)loaded"
  ```
- Return to the terminal running the test script and hit enter. This will clean up the
test by stopping and deleting the container (but keeps the image you created in the
previous section). 

The next sections details adding the usage service to your 
`Powerwall-Dashboard` stack.

## Add `pwdusage` to `Powerwall-Dashboard`

This step assumes you have set up a `usage.json` configuration file in the 
`tools/usage-service` subfolder of Powerwall-Dashboard. See the previous section for
using the example file, and the following section for details on setting it up to
match your own usage plan.

The `pwdusage` install steps are:

- If `powerwall.extend.yml` exists in your `Powerwall-Dashboard` folder, then copy the 
contents of the `pwdusage.extend.yml` file starting from the line `pwdusage:` into 
`powerwall.extend.yml` (this should be in the services section).
- Otherwise, copy `pwdusage.extend.yml` into the `Powerwall-Dashboard` folder and rename
it to `powerwall.extend.yml`.
- Edit `powerwall.extend.yml` to reflect your user id and any changes you may have made
to the default port and `USAGE_JSON` file path.

Finally, restart the Powerwall-Dashboard services:
```
./compose-dash.sh stop
./compose-dash.sh up -d
```

# `pwdusage` Configuration

Because there are so many different usage plans, `pwdusage` requires a JSON
configuration file to define *your* usage plans and calendars. This section discusses
the layout of this file and the how usage engine locates this file. You will very likely
also need to do some customisation in grafana to get report out in the format you
prefer, which the next section covers.

The project documentation assumes this file will be named  `usage.json` file. However,
you can use any name you like in conjunction with the `USAGE_JSON` environment variable
(see below).

The `tools/usage-service` folder in Powerwall-Dashboard repository contains a file named `example_usage.json` that you can use to build your own `usage.json`. The recommended
default location for your `usage.json` is the `tools/usage-service` folder. (As a 
convenience for developers, this example file is also duplicated in the `pwdusage` usage repostory.)

## Loading `usage.json`

The usage engine will look for the configuration files in the following locations:
- You can use the environment variable `USAGE_JSON` to specify the (optional) path and
the file name for the configuration file. You **must** use this method for running a
usage server in a **docker container** (most users). See the `pwdusage.extend.yml` and 
`test_service.sh` files in the previous sections for examples of mapping a local copy of
`usage.json` to a docker container volume.  
- If the environment variable is not specified, the enginer will try to load 
`usage.json` from the working directory. 
- If you are running the engine in CLI mode to dump csv files, you **must** specify the
location of the configuration file (optional path + file name) using the `--config`
argument. `USAGE_JSON` is ignored in this mode.

Note: if you have followed the steps for adding `pwdusage` to the Powerwall-Dashboard
docker stack and your `usage.json` is in the recommended location, everything should run
out of the box. 

## Strings from `common.py`

While most of the heavy lifting is done in the `usage.json` file, this configuration 
file depends heavily on constants defined in `common.py`. This section outlines these
constants.

The strings defined in the `PDColName` Enum in `common.py` are labels for key calculated
data columns in the usage engine. You may choose to output any subset of the numeric
calculations, and you can also change the default names of the outputs to your
preferred labels.

The following table summarises the strings available as at 13 May 2023. This set may be
extended in future.

| String        | Default string  | Description and Notes                             |
|---------------|-----------------|---------------------------------------------------|
| GRID_SUPPLY   | Grid supply     | Power from grid, grid import.                     |
| GRID_EXPORT   | Grid export     | Power from home to grid, grid export.             |
| PW_SUPPLY     | PW supply       | Output from powerwall (total).                    |
| HOME_DEMAND   | Home Demand     | Home power usage.                                 |
| SOLAR_SUPPLY  | Solar supply    | Solar generation (total).                         |
| GRID_TO_HOME  | Grid to Home    | Grid supply allocated to home demand.             |
| PW_TO_HOME    | PW to Home      | Powerwall output allocated to home demand.        |
| SOLAR_TO_HOME | Solar to Home   | Solar generation allocated to home demand.        |
| GRID_CHARGING | Grid charging   | Grid supply used to charge powerwall (allocated). |
| RESIDUAL_DEMAND_1 | Home demand ex supply 1 | See next section for priorities and residuals. |
| RESIDUAL_DEMAND_2 | Home demand ex supply 1+2 | See next section for priorities and residuals. |
| RESIDUAL_DEMAND_FINAL | Home demand ex supplies | See next section for priorities and residuals (should be zero, but don't rely on it, because Tesla.). | 
| SELF_PW_NET_OF_GRID | PW to home-grid charge | Power supply to home less grid charging of powerwall. See next section for discussion. |
| SELF_SOLAR_PLUS_RES | Solar to home+residual | Power supply to home plus any unaccounted residual demand. See next section for discussion. |
| SELF_TOTAL    | Self consumption | Total self consumption. SELF_PW_TO_HOME + SELF_SOLAR_PLUS_RES. |
| SUPPLY_CHARGE | Supply Charge | If specified in calendar rate table, will add 1 unit of supply charge to cost output for each data point. Ignored if specified in usage_plans variable report list. |
| TARIFF        | Tariff | String used internally. Not intended for end users. |
| TIME          | _time  | String used internally. Not intended for end users. |

## `usage.json` structure

Most of the usage engine setup is via the `usage.json` configuration file. As always
with JSON, it's finicky on exact syntax, and the server can be opaque with
error messages, so if you have trouble with setting up the usage engine, the first step
should be to check this file for syntax errors and typos. 

In the following sections, the various elements of the configuration file are identified
as either **required** or **optional**. Required elements must be supplied, while 
optional elements typically have standard defaults, or may repeat previously specified
input. Both required and optional elements can have additional qualifiers that apply to
that input.

The high level structure of the json file is:

```
{
  "settings": { ... dictionary of settings ...},
  "plans": [
    <usage plan 1>,
    <usage plan 2>,
    <usage plan 3>,
    ...
  ],
  "calendar": {
    "<effective date>": {<calendar data dictionary>},
    "<effective date>": {<calendar data dictionary>},
    "<effective date>": {<calendar data dictionary>},
    ...    
  }
}
```
The settings, plans, and calendar sections are all **required**.


### Settings Section

The structure of the settings dictionary is:
```
"settings": {
        "influx_url": "http://<hostname>:8086",
        "bucket": "powerwall/kwh",
        "timezone": "Australia/Hobart",
        "supply_priority": [
            "GRID_SUPPLY",
            "PW_SUPPLY",
            "SOLAR_SUPPLY"
        ],
        "cost_unit": "$",
        "energy_unit": "kWh",
        "rename": {
            "GRID_SUPPLY": "Grid supply---",
            "GRID_EXPORT": "Grid export+++"
        },
        "resample": true,
        "week_anchor": "MONTH",
        "year_anchor": "JAN"
    },
```

The dictionary entries are:
- [**required**] `influx_url` points at the influx database service, which is typically
the hostname or address of the Powerwall Dashboard host, with a port of 8086.
- [**required**] `bucket` is the name of the influx continuous query that supplies data
for the usage engine. This should have the same fields as the `powerwall/kwh` CQ (the 
default, which provides data on an hourly basis).
- [**required**] `timezone` - This should be set to your local timezone.
- `cost_unit` and `energy_unit` - **optional** string appended to the series labels 
for usage cost and energy data. Default to "$" and "kWh".
- `rename` - An **optional** dictionary that allows replacement of the default strings 
defined in `common.py`. If you want to have a new label string for the `"SOLAR_SUPPLY"`,
you can go nuts. Be my guest. The boring example above adds multiple - and + signs to
the strings for grid supply and grid export.
- `resample` - An **optional** setting which specifies if data should be downsampled,
with a default of true (true or false). This can also be set by a grafana payload. See
[JSON Payload](#json-payload) for discussion on resampling implementation and how to
configure the payload.
- `week_anchor` - An **optional** setting with default value of "MONTH". This specifies
the first day of the week used in data resampling. The default is to anchor the week
start to the first day of the month, but you can lock it to a fixed day of the week
using one of: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]. 
- `year_anchor` - An **optional** setting with default value of "JAN". This specifies
the first month of the year for annual reporting (provided in case anyone wants to run
reports that line up with local financial years). You can modify using any three day
month abbreviation ["JAN", "FEB", "MAR", ... , "DEC"]. Note: the first day of the 
reporting year corresponds to the first day of the specified month - e.g. 1st July for 
"JUL".

Finally, `"supply_priority"` is an **optional** entry that provides the order in which
supply is allocated to meet home demand for power. If specified, the entry **must** be a
three element list that states the order of `"GRID_SUPPLY"`, `"PW_SUPPLY"` and 
`"SOLAR_SUPPLY"`. If `"supply_priority"` is omitted, it defaults to the list specified
above (grid, powerwall, and then solar).

This list is used to allocate supply to demand as follows:

- Power from the first supply (e.g. grid supply) is allocated to `HOME_DEMAND`. 
  - If this supply exceeds demand (`GRID_SUPPLY > HOME_DEMAND`), then all home demand
  is met from this supply and remaining demand after the first supply is set to zero 
  (`RESIDUAL_DEMAND_1 = 0`). 
  - Otherwise, home demand consumes all of the available supply and the residual 
  demand is calculated from the difference between demand and supply - for our example, 
  it is `RESIDUAL_DEMAND_1 = HOME_DEMAND - GRID_SUPPLY`.
  - Finally, the total power allocated from the first supply to the home is the 
  difference between the home demand and the first residual - for our example:
  `GRID_TO_HOME = HOME_DEMAND - RESIDUAL_DEMAND_1`. 
- We apply the same process to the second supply (e.g. PW supply) to residual demand 1.
In summary for this case:
  - If `PW_SUPPLY > RESIDUAL_DEMAND_1`, then `RESIDUAL_DEMAND_2 = 0`, otherwise 
  `RESIDUAL_DEMAND_2 = RESIDUAL_DEMAND_2 - PW_SUPPLY`.
  - Power allocated from the second supply to home: `PW_TO_HOME = RESIDUAL_DEMAND_1 - 
  RESIDUAL_DEMAND_2`.
- And we apply the same process a third time to calculate `RESIDUAL_DEMAND_FINAL` and 
the third supply allocation to the home `SOLAR_TO_HOME`.

Note that the Tesla and/or InfluxDB data is not always to internally consistent. As
a result it is possible for `RESIDUAL_FINAL_DEMAND` to be non-zero (it can't be 
physically, but rounding, calculation errors and some Tesla oddities result it in 
happening from time to time - it is zero most of the time). Consequently, all of the
residual values are available for reporting if you want to see what is happening. 
(Aside: Sometimes the energy balance doesn't work at all - more energy coming in than
going out/being consumed or vice versa - the usage engine ignores this situation as it
is a) infrequent and b) there is no practical method to address it.)

The way I have chosen to address this is to assume that any positive non-zero residual 
demand must have been met by internal generation (erring on the thinking positive side),
and I have also assumed this is under-reported solar generation. So I have also included
a corrected solar self consumption variable which is defined as:
  ```
  SELF_SOLAR_PLUS_RES = SOLAR_TO_HOME + RESIDUAL_DEMAND_FINAL
  ```
(This may lead to infrequent small solar consumption being reported in the middle of
the night).

The example `usage.json` file uses this variable, but you can use `SOLAR_TO_HOME` 
instead if you don't want to use my assumption. Note total self consumption also 
includes this residual:
  ```
  SELF_TOTAL = PW_TO_HOME + SELF_SOLAR_PLUS_RES
  ```
If you don't want to include the final residual in total self consumption, you will need
to create a custom agent or report `SOLAR_TO_HOME` and `PW_TO_HOME` and then sum these
in grafana to obtain a total self consumption.

Finally with the calculations above in place, the usage engine calculates two more 
utility variables:
- `GRID_CHARGING = GRID_SUPPLY - GRID_TO_HOME`, where I assume any grid supply in excess
of that allocated to home demand is used to charge the powerwall.
- `SELF_PW_NET_OF_GRID = PW_TO_HOME - GRID_CHARGING`, which is the powerwall supply to 
home less any grid charging of the powerwall in the reporting period. See discussion on
powerwall savings in the calendar section for the reason for this variable and its
(optional) usage.

Final note: The usage engine does not try to reconcile the energy balance (out of
scope).

### Plans section

The plans section **must** contain at least one usage plan, and can contain an any 
number of usage plans. 

```
  "plans": [
    <usage plan 1>,
    <usage plan 2>,
    <usage plan 3>,
    ...
  ]
```

Each plan uses the following structure, with user specified names in <>:

 ```
 {
  "name": "<plan name - for example Utility XYZ>",
  "report": [
      "GRID_SUPPLY",
      "GRID_EXPORT",
      "SELF_PW_NET_OF_GRID",
      "SELF_SOLAR_PLUS_RES"
  ],
  "agent": "Simple",
  "seasons": {
      "<season name - e.g. Summer DST>": [
          {
              "schedule": "<e.g. Weekday> ",
              "days": [
                  0,
                  1,
                  2,
                  3,
                  4
              ],
              "periods": {
                  "22:00": "Off-Peak",
                  "08:00": "Peak",
                  "11:00": "Off-Peak",
                  "17:00": "Peak"
              }
          },
          {
              "schedule": "<e.g. Weekend>",
              "days": [
                  5,
                  6
              ],
              "periods": {
                  "00:00": "Off-Peak"
              }
          }
      ],
      "<season name - e.g. Winter WST>": [
          {
              "schedule": "<e.g. Weekday>",
              "periods": {
                  "21:00": "Off-Peak",
                  "07:00": "Peak",
                  "10:00": "Off-Peak",
                  "16:00": "Peak"
              }
          }
      ]
  }
}
```
The following points provide more detail on these elements:

- [**required**] "name" is a unique identifier for the usage plan. For example: 
"Aurora-TAS-ToU" for the Tasmanian Aurora time of use plan. 
- [**required**] "report" lists the energy variables that you want reported to grafana
for the plan. Available variables are defined in 
[`common.py`](#strings-from-commonpy) strings above. Note: a) you must specify 
at least one report variable even if you do not plan to use these variables, and b)
Cost/savings variables are specified in the calendar section.
- [**required**] "agent" specifies the usage agent for calculating costs. Right now, 
only the "Simple" agent is available.
- [**required**] "seasons". Each plan **must** contain at least one season, and can 
contain an arbitrary number of seasons. All seasons in the plan have share the same 
basic tariff schedule structure, but the timing detail of the tariff schedules varies 
between seasons (the explanation below makes this clearer). Season timings are defined 
in the calendar section (and ARE NOT tied to physical seasons).
The rules for seasons are:
  - [**required**] Each season **must** have a "name". 
  - [**required**] The first season must fully define **all** of the tariff schedules
  used in the plan. In the example above the "summer" season defines a "Weekday" and a 
  "Weekend" schedule. 
  - [**optional**] The second season can replace one or more of the tariff schedules 
  named in the first season (technically, it can also add new tariff schedules - I'd
  advise against this though - outcomes will be unpredictable). In our example above,
  the "Weekend" schedule is the same in summer and winter, so it is not replaced.
  However, the timing of the "Weekday" schedule does change, so we replace that. 
  - The third applies the same replacement logic, but to the second season, and so on.

  This process is intended to simplify dealing with multi-tariff usage plans where not
  too much changes between seasons - the alternative is to require definition of every
  tariff in every season (if users prefer, it would not be hard to switch to this mode). 
- Finally, each tariff schedule specifies tariff timings for a group of weekdays. The
rules for tariff schedules are:
  - [**required**] They must have a unique "schedule" name in the plan (you can re-use
  the schedule name in other plans). The name is required in the first season (initial
  definition) and future seasons (to identify which tariff schedule will be replaced).
  - [**required**] When they are first defined in the first season of the plan, you
  **must** specify:
    - The week days the schedule will apply with a "days" list (0 = Monday, 
    6 = Sunday).
    - The start times for each tariff during the day with a "periods" dictionary.
  - [**optional** When schedules are defined in any season after the first, they 
  **must** have the same name as the one of the schedules in the first season and
  **must** define either "days" and "periods" (and **may** define both), which will 
  replace the relevant elements of the tariff schedule in the preceding season.


  See the example above for the structure of these entries. 

  Specific notes on "periods" and "days":
  - At least one day **must** be specified in "days".
  - At least one period **must** be specified in "periods".
  - Each entry is "[tariff start time in 24:00 notation]": "[tariff name]".
  - Tariffs must appear in chronological order! The usage engine calculates the tariff
  active duration as the difference between two entries.
  - You can pick any period to start the list (but to keep your head in one piece, it 
  makes most sense to start with the first one after midnight and end with the last one
  before midnight).
  - The usage engine automatically rolls around between the last and first entries, and
  handles midnight crossover (so you don't have to think about start and end of day
  issues).
  - The schedule replacement mechanism replaces the entire "days" and "periods" entries
  (you can't modify a single day or period entry - you must fully respecify day groups
  and periods within the day).

### Calendar section

The calendar section is a dictionary of calendar entry dictionaries, where each entry 
dictionary has the following structure:

```
"2022-10-06": {
    "plan": "Aurora-TAS-ToU",
    "season": "Summer",
    "tariffs": {
        "Peak": {
            "GRID_SUPPLY": -0.33399,
            "GRID_EXPORT": 0.08883,
            "SELF_PW_NET_OF_GRID": 0.33399,
            "SELF_SOLAR_PLUS_RES": 0.33399,
            "SUPPLY_CHARGE": -0.04579291666
        },
        "Off-Peak": {
            "GRID_SUPPLY": -0.15551,
            "GRID_EXPORT": 0.08883,
            "SELF_PW_NET_OF_GRID": 0.15551,
            "SELF_SOLAR_PLUS_RES": 0.15551,
            "SUPPLY_CHARGE": -0.04579291666
        }
    }
},
```

[**required**] The date key specifies the starting date for the calendar entry. The
first entry in date order **must** contain the following sub-elements:
- [**required**] "plan": "[plan name]", where `plan name` is the plan that will be
active from the start date, and must correspond to one of the plans in the "plans"
section.
- [**required**] "season": "[season name]", where `season name` is the season of
`plan name` that will be active from the start date, and must match one of the seasons
in `plan name`.
- [**required**] "tariffs": [dictionary of tariff rate tables]. In the above example,
"Peak" and "Off-peak" rate tables specify cost and savings rates for various supplies
and exports - you can flip the sign of savings and costs if you prefer. Unfortunately, 
if you are not interested in cost data, you must still specify at least one tariff rate
table, but you can ignore cost output in your final dashboard. 

  Agent implementation note: Agents generally should report cost and savings for any 
  variable specified in the rate tables.

See the following section for a discussion of how the simple usage agent works and for a 
discussion of why I use the special variables `SELF_SOLAR_PLUS_RES` and 
`SELF_PW_NET_OF_GRID` in my savings calculations (if you don't like my logic, you can
use any of the other variables specified in `common.py` instead).

The second and following calendar entries operate by difference to the previous entry in
calendar order. You may specify any or all of the elements required for the first entry,
and these will then replace the values used in the the previous entry. In the following
example, the plan and tariffs remain the same as the previous entry, but the season is
changed to Winter.
```
"2023-04-02": {
    "season": "Winter"
}
```
## Simple usage agent

The simple usage agent is very straight forward. For each energy variable in the rate 
table, it calculates the cost/saving as `Variable value x variable rate`, and performs 
this calculation for each time interval record returned from the influx database.

As noted previously, I use two special variables in my savings calculations:

- `SELF_SOLAR_PLUS_RES`, which is the total solar energy allocated for home use plus
any residual from the demand allocation calculations. I do this based on the following
reasoning:
  - As noted previously, the final residual may be non-zero either due calculation 
  methods (integration, rounding, etc) or Tesla's caprice.
  - I'm arbitrarily assuming that Tesla's calculation of household demand and grid
  supply is correct. Hence, any residual demand is real and should be supplied by the
  solar system or the powerwall. I've arbitrarily assumed the solar system supplies 
  this residual. 

  If you don't like this assumption, I suggest you use `SOLAR_TO_HOME` instead and 
  ignore the residual.

- `SELF_PW_NET_OF_GRID`, which is energy supplied to the house less energy used to 
charge the powerwall, where I value the powerwall savings rate as the negative of the 
grid supply cost at the time (e.g. peak/off peak grid supply of -$0.30/-$0.20 results in 
a powerwall saving of $0.30/$0.20). The argument here is a bit more subtle than the
previous case - in effect the powerwall saving is the sum of two effects:
  - Total powerwall supply to home `X` generates a saving of `X * r` in a given period. 
  - If we charge the powerwall with an amount `Y` from the grid in the same period (e.g. 
  the battery breaks an hour into 40 minutes powering the home, 10 minutes charging from
  the grid, 10 minutes idle), we   don't get a home supply benefit from that grid power
  until it discharges to the home. So we  allocate a **negative** saving of `-Y * r`.
  - Taken together, we get the "savings" from the power wall of `(X - Y) * r`, or 
  powerwall supply to home net of grid charging to powerwall for that period.

  This approach has two benefits:
  - First, it deals with the potential problem of valuing energy use twice: once when
  buying from the grid to charge the battery, and again when discharging the same energy
  from the battery for use by the house. For example, if I take an example of spending
  40c to charge the battery with 2kWh at night and then using that 2kWH the next day at
  the same rate of 20c/kWh, then
    - Using a simple model, I pay 40c to fill the battery, and then recover 40c in 
    savings when I use the grid power. Which results in free electricity. To fix this 
    simple model requires tracking both solar and grid energy in the battery (which I'm
    too lazy to contemplate), or doing some complicated math with savings rates (again,
    too lazy).
    - Using the net of grid model, the battery in effect pays 40c for the grid charge 
    energy and then recovers that 40c when it discharges the energy, resulting in zero
    saving associated with the grid energy in and out of the powerwall and the correct
    charge of 40c for the original supply of grid power (more or less how we'd like the
    math to work).
  - Secondly, and more importantly, it automatically handles grid supply at one tariff
  and discharge at another. For example, if we charge the battery with 2kWh at an off 
  peak tariff of 20c and our peak tariff is 30c, then:
    - We pay 40c for the grid supply.
    - The battery has a savings reduction of 40c at the time of supply. 
    - If we use the energy at off peak time, the battery generates savings of 40c (net
    0c).
    - But, if we use the energy at peak time, the battery generates a savings of 60c 
    (net 20c). This effect would reverse for charging on peak (net savings reduction of
    20c).
  
As can be seen from this, the net of grid charging approach provides a relatively 
elegant (if not perfectly accurate) method for accounting for grid supply arbitrage 
using the battery.

The main disadvantage of this approach is that it doesn't account correctly for round
trip efficiency on the grid energy. But to do this, we'd need to build an agent that 
tracks supply and discharge from solar and grid and do a continuous allocation
calculation as to which supply is going via the powerwall to the home. This problem
promptly went into my 
"this-is-too-hard-and-the-current-approximation-is-good-enough" basket.

If you don't like this approach, you can use `PW_TO_HOME` instead. But note that you
will need to adjust your savings rate to manage the double dipping effect above, and it 
doesn't address the issue of charging at one tariff and discharging at another. A final
alternative is to implement a better usage agent yourself (offers welcomed!).

## Other usage agents

Right now, I have only implemented the simple usage agent detailed in the previous 
section. However, the system provides hooks for extension with additional usage agents. 
If you know your way around python, you can follow the structure of `simple_agent.py` to
build your own agent (if not, let me know via an issue and I'll see if I can help built
an agent for your use case).

# Grafana setup

This section assumes you have already got a 
[docker](#add-pwdusage-to-powerwall-dashboard) or [stand alone](#installation-for-developmenttesting) `pwdusage` server up and running, and you know 
the hostname/host address and port for the server.

## JSON datasource

From the general grafana configuration (cog wheel icon, bottom left):

- Select `Data sources`.
- Click `Add data source` and add a JSON data source.
- Give it a name - the example dash board uses `JSON Usage`. 
- Set the URL to: `http://<hostname>:<port>/usage_engine`. The default usage engine port
is 9050, but you can override this via the docker `.yml` configuration or via 
`USAGE_PORT` for a stand alone server.

  ![image](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/2bfe1062-b7b1-40a4-8870-32ca474a9421)

- Hit "Save and Test". You should see two green tick messages "Datasource updated" and 
"Data source is working". 

### Datasource troubleshooting

If the usage engine service has not started properly, the second message will show a 
green "Testing ..." for a while, followed by a red/pink "Gateway Timeout".

If the datasource url is incorrect, the second message will read: "Not Found". 

If the server has started and the url is correct, but there is problem with the usage
engine configuration, the second message will read: "status code 599". In this case,
try:

- Using a web browser to open `http://<hostname>:<port>/usage_engine`. The page may 
give some hints.
- Check the server log (if you are running docker, check the docker log).
- If none of this helps, raise an issue at: 
  `https://github.com/BuongiornoTexas/pwdusage/issues`.

## Grafana Dashboard setup

This section outlines the basics of setting up grafana dashboards based on usage 
queries. It refers to the example dashboards in the `tools/usage-service` folder, and
these also provide useful starting points for developing your own dashboard. The two
sample dashboards are: 
- A usage detail dashboard (the image at the top of this README), which uses
hourly data generated from the example `usage.json`.
- A month to date summary dash which presents summary statistics for the month to date
using the `summary` and `month_to_date` payload entries detailed in the following
section. The output is shown in the following image and is similar to that presented
in the detailed dashboard. 

![Usage mtd](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/e344ec31-afea-4027-9a73-4d93756aceb4)

The `usage-service` folder also includes an example drop in replacment panel for the
main dashboard savings panel - again built around month to date reporting and the
sample `usage.json` (you'll need to tweak it to match your utility). This panel 
loads a little slower than most dashboard elements, but still faster than the Tesla
power flow animation. 

![Savings panel](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/3c89e711-b775-4139-ba9b-11b17e222de6)

Note that I have not spent too much time on colors, layout or performance optimisation,
as each user will need to customise these reports to match their utility and their own reporting needs. (I know I've still got a bit of work to do on my own!) However, the
example dashboards do provide a reasonable idea of what you can do with the usage data
and how you can manipulate it. I also note that the transforms used in these panels
are SLOW on first load (a consequence of many panels and transforms). If you want
aster performance, use fewer panels for your own reporting (I'm pretty sure that 
careful use of transforms could reduce the number of panels in the summary dashboard 
from 7 to 2 or even 1 - watch this space). 

The main thing to be aware of when setting up a usage dashboard is that the usage 
datasource returns **all** time of use data in a **single table**. You should then
**duplicate** this data to other panels and **filter** the panel data using transforms
to get the data that you want to present in each panel - this process is outlined below.
You could also run a separate usage query for each panel, but I suspect the 
computational overhead will make this even slower than duplicating and filtering (If 
anybody wants to do some benchmarking, can you please report your results as any
issue? It seems I'm running out of energy to do this myself).

The process for setting up usage panels is:
- Choose a **hero** panel which you will use as your main data source. In
the "Usage Detail" example dashboard, the "Grid Import" panel is the hero panel. Set
the Data source to match your JSON pwdusage data source ("JSON Usage" in the examples)
and set the metric to "Usage".
  
  ![Datasource](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/327c6f36-e0bd-4a9c-9c65-7b8104379dee)

- For all other usage panels in the dashboard, set the data source to "-- Dashboard --"
and set the *Use results from panel* field to the name of your hero panel ("Grid 
Import").

  ![Duplicate data source](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/8492531b-4577-4a6a-a4f5-c68cee864267) 

- For each panel, apply a "Filter by Name" transform to select the variables you want
to present in the panel. You can either select the variables individually, or you
can use a regex. Either way, if you want to plot against time, you must select "_time"
or you will get "No data" errors (ask me how I know ...). An example of regexp that
selects all grid export power and time is "_time|(Grid export).*\(kWh\)".

- The "Add field from calculation" transform is useful for creating subtotals and 
totals, and the "Organise fields" transform can be useful for hiding intermediate
values and arranging fields. To see examples of these transforms, check the "Self 
Consumption Value" summary stat table in the "Usage Detail" example dashboard.

## JSON payload

The usage datasource supports a `payload` dictionary, which can be specified in the 
grafana query configuration, as shown in the following image.

![JSON Payload](https://github.com/BuongiornoTexas/pwdusage/assets/48264358/4bf4d2ee-5575-4dbc-87b4-b6c9db7b7597)

The supported payload entries are:

```
{
  "summary": [true | false], 
  "month_to_date": [true | false], 
  "year_to_date": [true | false], 
  "resample": [true | false] 
}
```
1) Note that `true` and `false` are both uncapitalised and unquoted.

2) If `summary` is `true` (default `false`), the values for each variable over the 
reporting range are summed to give total power and total costs, and the resulting totals
are returned (per interval values are not reported/discarded). Note that transforms
can be used in grafana to get the same result if you want to work with both time series
and summary values (use `false` in this case). 

3) Setting `month_to_date` to `true` (default `false`), the report time range is 
replaced with the current calendar month (utility for dashboard reporting). Both 
`summary` and `resample` apply normally. 

4) Setting `year_to_date` to `true` (default `false`), the report time range is 
replaced with the current year based on the `year_anchor` setting (utility for dashboard
reporting). Both `summary` and `resample` apply normally. If `month_to_date` and 
`year_to_date` are both true, `year_to_date` takes priority and is reported.

5) If `resample` is `true` (default), the usage data is resampled
   according to the following rules: 

    | Query time range | Resampling |
    |------------------|------------|
    | Within a single day    | Hourly     |
    | Within a single month  | Weekly     |
    | Within a single year   | Monthly    |
    | Larger intervals       | Yearly     |

    In this context within a single day means the query interval is for one calendar day
    maximum, and so on for the other intervals. If resample is set to false, the data is 
    not resampled and output is returned at the raw influx database query intervals. 

    The default resampling is `true`, and this can also be over-ridden in `usage.json`.
    If `summary` is `true`, `resample` is ignored.

# Installation for development/testing 

## Testing pwdusage

As of version 0.9.4, `pwdusage` is available as a pypi package, and it and its 
dependencies can be installed using pip. This is the recommended method if you want to
test the service and don't want to set up the docker container or do any development.

Optional, but strongly recommended: set up a python virtual environment for installing
and running `pwdusage` (please refer to the python documentation for details). To 
install:
```
pip install pwdusage
```

After installation, you can run the server with:
```
py -m pwdusage.server
```
If you want to generate .csv dumps for testing/debugging, the CLI help is available
from:
```
py -m pwdusage.engine -h
```

## Debugging and Development

If you are debugging the current code or developing new usage agents, this section 
outlines my approach to setting up a test/development environment (based on my fairly
limited python experience - if you know what you are doing, this section can be
ignored).

The main steps are:

- You will need to be running python 3.11 or higher. 
- I strongly suggest using a separate python virtual environment for development. 

   `py -m venv usage_test`

- Activate your environment (refer python docs) and install simplejson, and the
influxdb Flux client (I'm running without the high efficiency c iso 8601 library for 
now). The `[extra]` also installs numpy and pandas. 

  `pip install simplejson`

  `pip install influxdb-client[extra]`

- Clone my (@BuongiornoTexas) usage engine repository to a working directory. 

- Use pip to create an editable install from the working directory:

  `pip install --editable .`

  (When you are done, you can uninstall with `pip uninstall pwdusage`)

- Configure your usage proxy server. You can specify environment variables for the
JSON configuration file, server bind address, debugging, server port and HTTPS mode
[TODO - https is not working at the moment] (`USAGE_JSON, USAGE_BIND_ADDRESS,
USAGE_DEBUG, USAGE_PORT, USAGE_HTTPS`). For example, my vscode `launch.json`
specifies port 9050 (the default) for the test server and the location of the
configuration file: 
```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "USAGE_PORT": "9050",
                "USAGE_JSON": "C:/users/xxxx/yyy/usage.json"
            }
        }
    ]
}
```
- For initial testing, create a `usage.json` configuration file as detailed in 
[Test Docker Image](#test-docker-image).
- Set the `USAGE_JSON` environment variable to point at this `usage.json`.
- At this point, you should be able to run the server using: 
  ```
  py -m pwdusage.server
  ```
  You should then check that the usage server is responding by pointing a web browser at
  `http://server.address:<port>/usage_engine`. 
- If everything is as it should be, you should see a page containing the message:

  ```
  Usage Engine Status	"Engine OK, tariffs (re)loaded"
  ```
If you don't see this, please check that `usage.json` matches the description in 
[Test Docker Image](#test-docker-image). If 
you still have problems, let us know on the dev issue thread to see if we can trouble 
shoot.

If you do get the expected response, you can now modify the `usage.json` file to
reflect your own tariff structure [`pwdusage` Configuration](#pwdusage-configuration).

Finally, you can run the engine in cli mode to generate .csv dump files for debugging.
For this, use `py -m pwdusage.engine [arguments]`, with help available from 
`py pwdusage.engine -h`.
