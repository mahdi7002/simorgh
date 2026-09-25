"""
SIMORGH Mother package.

Important:
Do not eagerly import ReportEngine here.

core.llm_local imports submodules under core.mother.
Eagerly importing reports -> llm_local creates a circular import.

ReportEngine remains available through lazy attribute resolution.
"""

__all__ = ["ReportEngine"]


def __getattr__(name):
    if name == "ReportEngine":
        from .reports import ReportEngine
        return ReportEngine
    raise AttributeError(name)
