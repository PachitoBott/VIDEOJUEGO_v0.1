"""Lowercase compatibility shim for the Enemy module.

Some environments import the module as ``enemy`` instead of ``Enemy``.
This wrapper simply re-exports everything from the canonical ``Enemy``
module so either casing works without import errors.
"""
from Enemy import *  # noqa: F401,F403
