"""PoroTomo induced-seismicity agent: the porotomo-is-tuned blueprint for clio-agent 0.9.7.x."""

from clio_agent.sdk import Agent


class PorotomoIS(Agent):
    """One agent, no delegation: porotomo_report for run results, porotomo_h5_layout for HDF5 records, shell for PBS, read-only HDF5 tools for data values."""

    id = "porotomo-is"
    version = "0.5.0"
    name = "PoroTomo IS"
    role = (
        "an induced-seismicity analyst for the PoroTomo DAS data from Brady Hot Springs "
        "(March 2016)"
    )
    description = (
        "Answers questions about anomalies and Pohang-like (Mw >= 5.5) hazard in the PoroTomo "
        "DAS runs: the porotomo_report tool for run results, PBS jobs on Aurora for new runs, and clio-kit's "
        "HDF5 MCP server for the records. Port of the porotomo-is-tuned blueprint."
    )
    # core + memory from Agent; no web, documents, delegation or orchestration.
    plugins = Agent.plugins + ["shell", "hdf5", "porotomo-is"]
