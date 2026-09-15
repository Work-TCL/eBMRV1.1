# Document 43 EDGE-FR-029 ("Reference deployment supports signed container images/systemd/container
# runtime with restart policy and health probes") and section 10 ("rootless container where practical",
# "least-privilege OS account"). Built and signed by the release pipeline (Document 68/DEP-FR-002 SBOM +
# signature), not by this image definition itself.

FROM python:3.12-slim AS runtime

RUN groupadd --system edge && useradd --system --gid edge --home-dir /var/lib/edge-gateway --shell /usr/sbin/nologin edge

WORKDIR /opt/edge-gateway
COPY pyproject.toml ./
COPY runtime ./runtime
COPY plugins ./plugins
COPY storage ./storage
COPY contracts ./contracts
COPY migrations ./migrations
COPY cli ./cli

RUN pip install --no-cache-dir .

RUN mkdir -p /var/lib/edge-gateway && chown -R edge:edge /var/lib/edge-gateway
VOLUME ["/var/lib/edge-gateway"]

USER edge
ENV PYTHONPATH=/opt/edge-gateway

# EDGE-FR-029 "health probes": `status` exits non-zero when unenrolled/unhealthy so an orchestrator
# (docker/podman/k8s liveness) can restart per its own configured restart policy.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-m", "cli.main", "--state-dir", "/var/lib/edge-gateway", "status"]

ENTRYPOINT ["python", "-m", "cli.main", "--state-dir", "/var/lib/edge-gateway"]
CMD ["status"]