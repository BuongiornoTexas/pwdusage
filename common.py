#!/usr/bin/env python
# UsageEngine Module - Class for usage calculations.
# -*- coding: utf-8 -*-
"""
 Enum of all usage strings/pandas columns/values available for export to grafana.
 Utility class method for testing if a string is a valid enum name or string, 
 which returns the enum value.
 Author: BuongiornoTexas
 For more information see https://github.com/jasonacox/pypowerwall

"""
# cspell: ignore dataframe

from typing import Optional
from enum import StrEnum, unique

# These are friendly versions of static pandas column names.
# Some new column names may also be derived from these (e.g. cost columns in
# usage agents).
# I've tried to go with the following naming convention "<source> <destination>" and
# "<demand> <demand modifier>".
# In general, if you plan to read a column name from an input file or add a calculated
# column to the pandas dataframe, you probably want to add the string to this enum and
# validate using cls.from_str().
#
# The exceptions to this rule are per tariff column names for energy and costs. These
# are be created dynamically from the calculated column name by the usage engine.


@unique
class PDColName(StrEnum):
    # This group is renamed core data from influx.
    GRID_SUPPLY = "Grid supply"  # from_grid, AKA grid import!
    GRID_EXPORT = "Grid export"  # to_grid
    PW_SUPPLY = "PW supply"  # from_pw
    HOME_DEMAND = "Home Demand"  # home
    SOLAR_SUPPLY = "Solar supply"  # solar

    # Core elements calculated in usage engine.
    # Supply breakdown
    GRID_TO_HOME = "Grid to Home"
    PW_TO_HOME = "PW to Home"
    SOLAR_TO_HOME = "Solar to Home"
    # Define grid charging as any grid supply not used by house.
    GRID_CHARGING = "Grid charging"

    # Home residual demand after allocating supplies, calculated in engine.py
    RESIDUAL_DEMAND_1 = "Home demand ex supply 1"
    RESIDUAL_DEMAND_2 = "Home demand ex supply 1+2"
    RESIDUAL_DEMAND_FINAL = "Home demand ex supplies"  # SHOULD be zero! But Tesla.

    # Convenience self consumption groups, calculated in usage engine.
    SELF_PW_NET_OF_GRID = "PW to home-grid charge"
    SELF_SOLAR_PLUS_RES = "Solar to home+residual"
    SELF_TOTAL = "Self consumption"

    # This a special case that only works if the influx data is on constant intervals
    # (e.g hourly). For this variable, the supply cost should match the interval.
    # E.g. daily supply charge with hourly data in the bucket requires charge/24.
    SUPPLY_CHARGE = "Supply Charge"

    TARIFF = "Tariff"

    TIME = "_time"

    @classmethod
    def from_str(cls, str_v: str) -> Optional["PDColName"]:
        # String must the name!
        ret_val = None
        try:
            ret_val = cls[str_v]
        except:
            # So it's not the name.
            pass

        return ret_val

    def value_with_override(self, override: dict["PDColName", str]) -> str:
        # Returns value unless override dict provides an alternative string.
        # Allows user override of names.
        if self in override:
            return override[self]

        return self.value
