"""Modbus RTU `ConnectorPlugin`. Config shape follows Document 44 section 6 (RTU variant, DRV-FR-008):

```yaml
protocol: MODBUS_RTU
port: /dev/ttyUSB0
baudrate: 19200
parity: N
stopbits: 1
bytesize: 8
unit_id: 3
mappings: [... same shape as Modbus TCP ...]
```
"""

from __future__ import annotations

from plugins.common.driver_contracts import SourceAddress
from plugins.common.polling_plugin import PollingConnectorPlugin
from plugins.modbus.driver import ModbusDriver


class ModbusRtuPlugin(PollingConnectorPlugin):
    def _build_driver(self) -> ModbusDriver:
        return ModbusDriver(
            connector_id=self.connector_config.get("connector_id", "modbus-rtu"),
            connector_version=self.connector_config.get("connector_version", "1.0.0"),
            device_id=self.connector_config.get("device_id", "modbus-rtu-device"),
            variant="MODBUS_RTU",
        )

    def _build_addresses(self) -> list[SourceAddress]:
        return [
            SourceAddress(
                address=str(m["address"]), protocol="MODBUS_RTU", data_type=m.get("data_type"),
                extra={
                    "function": m.get("function", "HOLDING"), "length": m.get("length", 1),
                    "data_type": m.get("data_type", "UINT16"), "byte_order": m.get("byte_order", "ABCD"),
                    "scale": m.get("scale", 1.0), "unit_id": m.get("unit_id"),
                    "mapping_id": m.get("mapping_id", str(m["address"])), "unit": m.get("unit"),
                },
            )
            for m in self.connector_config.get("mappings", [])
        ]