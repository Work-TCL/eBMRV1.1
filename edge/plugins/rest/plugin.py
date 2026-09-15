"""REST-polling `ConnectorPlugin`. Config shape:

```yaml
protocol: REST
base_url: https://instrument.local:8443
auth: {type: bearer, token: "..."}       # or {type: basic, username, password} or omitted
mappings:
  - path: /api/v1/tank/level
    value_field: data.value
    unit_field: data.unit
    mapping_id: TANK_LEVEL
```

Fits `PollingConnectorPlugin`'s "read N fixed addresses once per cycle" shape exactly -- unlike MQTT/the
generic serial adapter, a REST GET is a self-contained request/response with no persistent streaming
session to interleave, so no bespoke poll loop is needed here.
"""

from __future__ import annotations

from plugins.common.driver_contracts import SourceAddress
from plugins.common.polling_plugin import PollingConnectorPlugin
from plugins.rest.driver import RestPollingDriver


class RestPlugin(PollingConnectorPlugin):
    def _build_driver(self) -> RestPollingDriver:
        return RestPollingDriver(
            connector_id=self.connector_config.get("connector_id", "rest"),
            connector_version=self.connector_config.get("connector_version", "1.0.0"),
            device_id=self.connector_config.get("device_id", "rest-device"),
        )

    def _build_addresses(self) -> list[SourceAddress]:
        mappings = self.connector_config.get("mappings") or [{
            "path": self.connector_config["path"],
            "value_field": self.connector_config["value_field"],
            "unit_field": self.connector_config.get("unit_field"),
            "mapping_id": self.connector_config.get("mapping_id"),
            "unit": self.connector_config.get("unit"),
        }]
        return [
            SourceAddress(address=m["path"], protocol="REST", extra={
                "value_field": m["value_field"], "unit_field": m.get("unit_field"),
                "mapping_id": m.get("mapping_id", m["path"]), "unit": m.get("unit"),
            })
            for m in mappings
        ]
