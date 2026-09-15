"""Shared helpers used by more than one protocol/peripheral plugin.

`driver_contracts.py`/`polling_plugin.py` are Document 44 (SPEC-EDGE-002) protocol-driver shared code:
each protocol subpackage (`plugins/opcua`, `plugins/modbus`, `plugins/mqtt`, `plugins/snmp`,
`plugins/serial`, `plugins/rest`, `plugins/file`) implements `EdgeDriver` from `driver_contracts.py` with
a real client for that protocol, wrapped in a `ConnectorPlugin` (Document 43's fixed adapter interface,
`plugins/base.py`) whose `poll()` calls the driver's `read_once()` (or drains a subscription queue).

`file_ingest.py` is Document 46 (SPEC-EDGE-004) peripheral shared code used by more than one peripheral
plugin. Nothing in this package is protocol- or peripheral-specific to any one subpackage.
"""
