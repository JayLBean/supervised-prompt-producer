"""Runnable substrate for /spp-loop and /spp-finalize execution.

Four scripts: split, inference, eval, discrepancy. Each is invokable as
a CLI (``python -m <name>``) and importable (``from spp_scripts import
<primitive>``).

Schemas come from /spp-baseline.md §4 step 9 and /spp-loop.md §4
steps 6-8. The scripts are mechanical implementations; methodology
lives in the agent / command / sub-skill docs.
"""
