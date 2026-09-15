"""Modbus TCP `ConnectorPlugin`. Config shape follows Document 44 section 6's reference YAML:

```yaml
protocol: MODBUS_TCP
host: 10.0.0.20
port: 502
unit_id: 1
mappings:
  - address: 40010
    function: HOLDING
    length: 2
    data_type: FLOAT32
    byte_order: ABCD
    scale: 1.0
    mapping_id: TANK_LEVEL
    unit: L
```
"""

from __future__ import annotations

from plugins.common.driver_contracts import SourceAddress
from plugins.common.polling_plugin import PollingConnectorPlugin
from plugins.modbus.driver import ModbusDriver


class ModbusTcpPlugin(PollingConnectorPlugin):
    def _build_driver(self) -> ModbusDriver:
        return ModbusDriver(
            connector_id=self.connector_config.get("connector_id", "modbus-tcp"),
            connector_version=self.connector_config.get("connector_version", "1.0.0"),
            device_id=self.connector_config.get("device_id", "modbus-tcp-device"),
            variant="MODBUS_TCP",
        )

    def _build_addresses(self) -> list[SourceAddress]:
        return [
            SourceAddress(
                address=str(m["address"]), protocol="MODBUS_TCP", data_type=m.get("data_type"),
                extra={
                    "function": m.get("function", "HOLDING"), "length": m.get("length", 1),
                    "data_type": m.get("data_type", "UINT16"), "byte_order": m.get("byte_order", "ABCD"),
                    "scale": m.get("scale", 1.0), "unit_id": m.get("unit_id"),
                    "mapping_id": m.get("mapping_id", str(m["address"])), "unit": m.get("unit"),
                },
            )
            for m in self.connector_config.get("mappings", [])
        ]