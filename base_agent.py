#!/usr/bin/env python
# UsageEngine Module - Class for usage calculations.
# -*- coding: utf-8 -*-
"""
 Base class for usage agents. 
 Author: BuongiornoTexas
 For more information see https://github.com/jasonacox/pypowerwall

"""

from typing import Any
from abc import ABC, abstractmethod
from pandas import DataFrame, Series  # type:ignore
from common import PDColName

# cspell: ignore metaton dataframe


class UsageAgent(ABC):
    """_summary_
    UsageAgent is the base class of all usage engine calculation classes.
    Note that:
    - The usage engine and usage agents are tightly linked.
    - The usage engine will create a usage agent instance for each unique usage plan,
      and will also use that agent across all disjoint calendar periods that the usage
      plan applies for.
    - If can_persist returns true, the usage engine will keeps agents alive for long
      periods -  either until the pypowerwall server is restarted or the user requests
      a reload of usage engine configuration. The usage agent is responsible for
      ensuring internal data consistency. If in doubt, set up agents to return
      False and recalculate internal data each time the instance is created. (However:
      if your usage agent needs to perform intensive calculations whose results could
      be stored, True is probably what you want in the long term).
      - The implementer is responsible for managing race conditions in agents
      if persistence is allowed.

    Persistence is useful in two places (at least). First, if your agent is stateless
    (e.g. the simple agent), then there is no requirement to tear down and rebuild
    agents.

    Second, if you have  something like a usage plan that is based
    on tiered consumption - instead of calculating the tier breaks on each call, you
    could calculate them on demand and store for future use (with the caveat that you
    will need to keep an eye on current/future generation as well).

    A specific example where this second type might be used: Metaton's plan here:
    https://github.com/jasonacox/Powerwall-Dashboard/discussions/68#discussioncomment-4616865.
    Each time the user agent encounters a new year, it could do the 600kWh transition
    and store it for future use (current generation year would require repeated
    calculations until transition). A similar approach could be applied to monthly
    tiered supply. Daily or shorter would probably be better recalculated each time.

    This is very untested! Right now, I only need a
    simple rate engine, so it's up to anyone who needs it to implement the appropriate
    agent. However, I've put in the hooks that I think might be needed for the future -
    these carry small overhead for agents that don't need them. So if they aren't ever
    used, delete in future? It may also make sense to push these stateful calcs back
    into influx?

    Repeating the warning above: agents are responsible for ensuring thread safety of
    instance data if can_persist is true.
    """

    # I did think about include pre- and post- process instance methods, but I don't
    # they add anything over the core usage method.

    def __init__(self, plan_json: dict[str, Any]) -> None:
        # Does nothing in the base class, as the default assumption is that agents are
        # stateless. However, if anyone wants to create a stateful agent, the derived
        # class should use information in provided in the jason to set up state
        # information.

        # Agent should treat plan_json as read only. This can be used to define
        # per agent/plan specific configuration data.

        pass

    @classmethod
    @abstractmethod
    def can_persist(cls) -> bool:
        # This should return true if the usage engine can maintain a persistent instance
        # of the usage agent. If can_persist is false, then the usage engine will
        # create new agent instances time the engine is instantiated. Otherwise,
        # the usage engine will maintain a persistent instance in its class variables.
        #
        # See module level notes for more details.
        # Even though it is declared as an abstractmethod, mypy can't check this as it
        # is also a class method, which is always available. So NotImplementedError is
        # required.
        raise NotImplementedError(
            f"Class {cls.__name__} has not implemented can_persist method (mandatory!)."
        )

    @abstractmethod
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
        # Must be implemented by all agents. Refer to SimpleAgent for an example
        # implementation. This implementation outlines mandatory elements of the
        # implementation.

        # This is a first pass argument list that is more than is needed for simple
        # agent. We may need to add more arguments in future. Not sure if will be best
        # done through explicit arguments that aren't used in all agents, or by a kwargs
        # approach. I've started with a kwargs approach as it is easy to implement, but
        # we can revisit as needed in future.

        # dataframe - The entire dataframe for the usage query.
        # tariff_idx - The index for the rows of the dataframe that
        # rates is a dict of column names and rates. Read only.
        # report_cols are the columns that will be returned to grafana.
        #   - The agent should append new columns on to this list if appropriate.
        #     E.g. The simple agent always adds a cost element if the energy element
        #     is already in report_cols.
        # kwargs - Additional keyword arguments used on a per agent basis.
        #
        # The agent can add new columns to the dataframe.
        # The agent can modify data in the rows specified by the tariff index.
        # The agent SHOULD NOT modify data in any other rows, with the exception
        # of providing default values in any added columns.

        pass
