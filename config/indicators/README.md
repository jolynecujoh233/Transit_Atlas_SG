# Registered additional indicators

This directory holds manifests created by `analysis/register_indicator.py`.
Each manifest names a project-local, prepared 1,597-grid CSV and records its
SHA-256 hash, source, year, unit, direction and calculation method. The
research agent reads these manifests as available indicators; the scenario
runner verifies the source hash before joining the data. No extra indicator
is registered by default.
