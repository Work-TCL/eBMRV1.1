"""SNMPv3-polling `ConnectorPlugin`. Config shape:

```yaml
protocol: SNMP
host: 10.0.0.40
port: 161
username: monitor
auth_protocol: SHA        # NONE|MD5|SHA|SHA224|SHA256|SHA384|SHA512
auth_key: "authpassword123"
priv_protocol: AES128     # NONE|DES|3DES|AES128|AES192|AES256
priv_key: "privpassword123"
mappings:
  - oid: "1.3.6.1.2.1.1.3.0"
    mapping_id: SYS_UPTIME
    unit: ticks
```

Fits `PollingConnectorPlugin`'s "read N fixed addresses once per cycle" shape -- one SNMP GET per
configured OID per poll, same shape as Modbus/OPC UA/REST.
"""

from __future__ import annotations

from plugins.common.driver_contracts import SourceAddress
from plugins.common.polling_plugin import PollingConnectorPlugin
from plugins.snmp.driver import SnmpDriver


class SnmpPlugin(PollingConnectorPlugin):
    def _build_driver(self) -> SnmpDriver:
        return SnmpDriver(
            connector_id=self.connector_config.get("connector_id", "snmp"),
            connector_version=self.connector_config.get("connector_version", "1.0.0"),
            device_id=self.connector_config.get("device_id", "snmp-device"),
        )

    def _build_addresses(self) -> list[SourceAddress]:
        return [
            SourceAddress(address=m["oid"], protocol="SNMP", extra={"mapping_id": m.get("mapping_id", m["oid"]), "unit": m.get("unit")})
            for m in self.connector_config.get("mappings", [])
        ]
