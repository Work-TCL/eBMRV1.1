"""OPC UA `ConnectorPlugin` -- wraps `OpcUaDriver` behind Document 43's fixed poll-based adapter
interface. Config shape follows Document 44 section 5's reference YAML exactly:

```yaml
protocol: OPCUA
endpoint_url: opc.tcp://10.0.0.10:4840
security_mode: SignAndEncrypt
security_policy: <approved policy>
client_certificate_path: /path/to/cert.der
client_key_path: /path/to/key.pem
trust_store: /var/lib/edge/opcua/trusted
auth: {type: username_password, username: ..., password: ...}
mappings:
  - node_id: "ns=4;s=Line1.Filler.Pressure"
    expected_data_type: Double
    mapping_id: FILL_PRESSURE
    unit: bar
```
"""

from __future__ import annotations

from plugins.common.driver_contracts import SourceAddress
from plugins.common.polling_plugin import PollingConnectorPlugin
from plugins.opcua.driver import OpcUaDriver


class OpcUaPlugin(PollingConnectorPlugin):
    def _build_driver(self) -> OpcUaDriver:
        return OpcUaDriver(
            connector_id=self.connector_config.get("connector_id", "opcua"),
            connector_version=self.connector_config.get("connector_version", "1.0.0"),
            device_id=self.connector_config.get("device_id", "opcua-device"),
        )

    def _build_addresses(self) -> list[SourceAddress]:
        return [
            SourceAddress(
                address=m["node_id"],
                protocol="OPCUA",
                data_type=m.get("expected_data_type"),
                extra={"mapping_id": m.get("mapping_id", m["node_id"]), "unit": m.get("unit")},
            )
            for m in self.connector_config.get("mappings", [])
        ]