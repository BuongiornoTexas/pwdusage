---
# cspell: ignore venv beautifulsoup tzdata numpy simplejson datasource
--- 

# Powerwall-Dashboard-usage-proxy

Usage (mainly time of use) proxy microservice for Powerwall-Dashboard

# Development notes for usage engine

Everything in this document is a temporary placeholder for development of the usage 
engine. Contents will be incorporated into the server README or deleted in future.

# Fixes required for final release

This is a TODO list for @BuongiornoTexas. Everyone else please ignore (unless you want 
to help with development ...). Sorry for putting
it here, but I need to keep this top of mind for implementation.

- Implement resampling/aggregation so that bar charts > 24h are meaningful. Should be 
quick (expect update in next few days).
- Fix `server.py` do_GET error response - right now do_GET always returns 200 even on
invalid page. So Json Data source will always return working even if it is not! 
I think this may also be eating some configuration error messages?
- Decide best approach for https server. Don't want to be carrying duplicate code base
if possible?
- Set up an environment variable for `usage.json` so it can be loaded from the docker
container?
- Address other changes needed to get code docker compatible.
- Reset time zone (America/Los_Angeles) and url in usage.json (localhost:8086).
- Maybes/future functions?:
  - Implement mechanism to dump data frame to file for debugging?
  - Add query payload to allow user to limit return to either cost or energy data only?
  - Add query payload to allow user to request summary data (totals) only?
  - Add query payload to allow user to request raw data without aggregation?

# Usage Engine for pypowerwall server

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

TODO: Assuming there is user support and enthusiasm for the usage engine, it should be
integrated into the main pypowerwall codebase. Until that time, users will either need 
to prepare a custom docker image, or follow the 
["Installation for test users"](#installation-for-test-users) instructions below to 
setup a stand alone pypowerwall server instance for running the usage engine.


# Configuration

Because there are so many different tariffs, configuration will require setting up a
`usage.json` file to define usage plans and calendars, and you will very likely also
need to do some customisation in grafana to get report out in the format you prefer.

While most of the heavy lifting is done in the `usage.json` file, this configuration 
file depends heavily on constants defined in `usage_common.py`. The next sections
details these constants, the structure of `usage.json`, and finally outlines grafana
customisation steps.

## Strings from usage_common.py

The strings defined in the `PDColName` Enum in `usage_common.py` are labels for key 
calculated data columns in the usage engine. You may choose to output any subset of the 
numeric calculations, and you can also change the default names of the outputs to
your preferred labels.

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
        "supplyPriority": [
            "GRID_SUPPLY",
            "PW_SUPPLY",
            "SOLAR_SUPPLY"
        ],
        "cost_unit": "$",
        "energy_unit": "kWh",
        "rename": {
            "GRID_SUPPLY": "Grid supply---",
            "GRID_EXPORT": "Grid export+++"
        }
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
defined in `usage_common.py`. If you want to have a new label string for the 
`"SOLAR_SUPPLY"`, you can go nuts. Be my guest. The boring example above adds multiple - 
and + signs to the strings for grid supply and grid export. 

Finally, `"supplyPriority"` is an **optional** entry that provides the order in which
supply is allocated to meet home demand for power. If specified, the entry **must** be a
three element list that states the order of `"GRID_SUPPLY"`, `"PW_SUPPLY"` and 
`"SOLAR_SUPPLY"`. If `"supplyPriority"` is omitted, it defaults to the list specified
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

Final note: The usage engine does not try to reconcile the energy balance (out of scope).

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
[`usage_common.py`](#strings-from-usage_commonpy) strings above. Note: a) you must specify 
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
  - Each entry is "< tariff start time in 24:00 notation>": "< tariff name>".
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
- [**required**] "plan": "< plan name>", where `<plan name>` is the plan that will be
active from the start date, and must correspond to one of the plans in the "plans"
section.
- [**required**] "season": "< season name>", where `season name` is the season of
`plan name` that will be active from the start date, and must match one of the seasons
in `plan name`.
- [**required**] "tariffs": < dictionary of tariff rate tables>. In the above example,
"Peak" and "Off-peak" rate tables specify cost and savings rates for various supplies
and exports - you can flip the sign of savings and costs if you prefer. Unfortunately, 
if you are not interested in cost data, you must still specify at least one tariff rate
table, but you can ignore cost output in your final dashboard. 

  Agent implementation note: Agents generally should report cost and savings for any 
  variable specified in the rate tables.

See the following section for a discussion of how the simple usage agent works and for a 
discussion of why I use the special variables `SELF_SOLAR_PLUS_RES` and 
`SELF_PW_NET_OF_GRID` in my savings calculations (if you don't like my logic, you can
use any of the other variables specified in `usage_common.py` instead).

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
If you know your way around python, you can follow the structure of `usage_simple.py` to
build your own agent (if not, let me know via an issue and I'll see if I can help built
an agent for your use case).

## Grafana setup

### JSON datasource

TODO add images to this section.

If you are using a test usage server, start it now. For a first time run, I'd suggest
using the default `usage.json`. 

From the general grafana configuration (bottom left):

- Select `Data sources`.
- Click `Add data source` and add a JSON data source.
- Give it a name - the example dash board uses `JSON Usage`. 
- Set the URL to: `http://<hostname>:<port>/usage_engine`. The default pypowerwall port
is 8675, but if you may have changed this if you are running a test server (you 
DEFINITELY should have changed this if you are running a test server on the same 
host as your main pypowerwall docker instance).
- Hit "Save and Test". You should see two green tick messages "Datasource updated" and 
"Data source is working".

### Dashboard setup

TODO write this section.

In the interim, I've provided example dashboard called `usage_example.json`. Import this
into grafana and have an explore.

# Installation for test users 

As I'm doing this development on a windows machine and don't want to deal with 
repeatedly creating multiple docker containers, I run a stand alone test server. Unless
you know python and docker well, I'd recommend you follow the same approach for your own
development and testing. The main steps are:

- You will need to be running python 3.11 or higher. 
- I strongly suggest using a test python environment. 

   `py -m venv usage_test`

- Activate your environment and install simplejson, pypowerwall, beautifulsoup4 (bs4, 
which is not installed with pypowerwall), and the influxdb Flux client (I'm running 
without the high efficiency c iso 8601 library for now). The `[extra]` also installs 
numpy and pandas.You may also need to install `tzdata` (I did on windows in the early 
stages, but haven't had trouble since - if you get errors about time zones, this is 
probably it). 

  `pip install simplejson`

  `pip install pypowerwall`

  `pip install beautifulsoup4`

  `pip install influxdb-client[extra]`

- Clone my (@BuongiornoTexas) pypowerwall repository to a working directory (you 
probably only need the proxy server directory - everything else you use should come from
the OG pypowerwall installed in the previous step). 

- Configure your test server, which duplicates the pypowerwall server used by the
dashboard. **VERY IMPORTANT**: If you are running on the same machine as your dashboard,
you need to override the default port (8675). For example, my vscode `launch.json` sets
up the powerwall login information and specifies port 9050 for the test server: 
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
                "PW_HOST": "powerwall.ip.address.xx",
                "PW_EMAIL": "xxx.xxx@xxxx.com",
                "PW_PASSWORD": "powerwall password",
                "PW_TIMEZONE": "Australia/Hobart",
                "PW_PORT": "9050"
            }
        }
    ]
}
```
- In the `usage.json` configuration file, modify `influx_url` to point at your influx
server (probably the same machine as your Powerwall-Dashboard) and set the correct 
`timezone`.
- At this point, you should be able to run `server.py` from the @Buongiorno repo - for 
me, `py proxy\server.py` works. You should then check that the usage engine is 
responding by pointing a web browser at `http://server.address:<port>/usage_engine`. 
- If everything is as it should be, you should see a page containing the message:

```
Usage Engine Status	"Engine OK, tariffs (re)loaded"
```
If you don't see this, please check that you are using the unmodified `usage.json`. If 
you still have problems, let us know on the dev issue thread to see if we can trouble 
shoot.