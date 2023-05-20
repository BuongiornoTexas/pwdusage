#!/usr/bin/env python
# UsageEngine Module - Class for usage calculations.
# -*- coding: utf-8 -*-
"""
Agent implementing a simple usage-rate calculation. Massive overkill here, but the
agent approach allows for more complex usage models.

This agent is stateless, so __init__ is not required.

 Author: BuongiornoTexas
 For more information see https://github.com/jasonacox/pypowerwall


"""
# cspell: ignore

from typing import Any
from pandas import DataFrame, Series  # type: ignore
from base_agent import UsageAgent
from common import PDColName


class SimpleAgent(UsageAgent):
    @classmethod
    def can_persist(cls) -> bool:
        # Simple agent is stateless, so can be persistent.
        return True

    def usage(
        self,
        frame: DataFrame,
        tariff: str,
        tariff_idx: Series,
        rates: dict[PDColName, float],
        cost_unit: str,
        report_cols: dict[str, str],
        col_override: dict[PDColName, str],
        **kwargs: Any,
    ) -> None:
        # It really is a simple agent. With a *lot* of arguments.
        for energy_column, rate in rates.items():
            full_name = energy_column.value_with_override(col_override)
            full_name = f"{tariff} {full_name} ({cost_unit})"            
            if full_name not in report_cols:
                report_cols[full_name] = "number"

            # Special cases.
            if energy_column is PDColName.SUPPLY_CHARGE:
                # Each time block incurs 1 unit of supply charge.
                # Make a reporting copy of the column data.
                frame.loc[tariff_idx, full_name] = rate
                continue

            elif energy_column.value not in frame.columns:
                # Column name has already been validated - if this happens, something
                # has gone badly wrong.
                raise KeyError(
                    f"SimpleAgent called for non-existent column {energy_column.value}."
                )
            
            # Make a reporting copy of the column data.
            frame.loc[tariff_idx, full_name] = frame.loc[
                tariff_idx, energy_column.value
            ] * rate
