# Tablet and optional laboratory contract

15 November 2026 · Additive runtime interfaces; the frozen mission actions remain unchanged.

`/redline/rviz/image/compressed` is `sensor_msgs/CompressedImage`, lossless PNG,
at most 1 MiB and 2048² pixels, `header.frame_id=rviz`. Pixels come from an
owned actual RViz process on a private Xvfb display, not a redrawn map or the
user desktop. `/redline/rviz/status` is a bounded String JSON with schema
`redline.rviz.stream.v1`, source `rviz2/private-xvfb`, stream_id, sequence,
dimensions, capture_fresh/source_fresh, physics clock/odom ages and image stamp.
No robot command, TF or physics owner is created. Unreal masks stale images.

`AnalyzeSample.srv` is additive: request_id, sample_id, method, integration_s →
accepted, reason, operation_id. The endpoint is `/redline/science/analyze_sample`.
Method WCL_SCENARIO requires a persisted SIMULATED sample in RECORDED state,
a container, custody evidence, and a separate analysis location. Duplicate
requests cannot execute twice; changed payloads with the same ID are rejected.
The optional assay is independent of the 12-step campaign. It can be started
remotely after custody, and cannot collect/transport a sample remotely.

`/redline/science/lab_status` uses schema `redline.lab.status.v1`. Acceptance is
not completion. After a 10 s presentation the node revalidates unchanged custody,
persists a product JSON and PDS4-like XML, then publishes InstrumentProduct and
EvidenceRecord. The product integration is an authored 120 s model series; no
mission clock seek occurs. pH/conductivity are generated from the explicitly
authored config/lab_assays_BXW.yaml recipe and its seed, not from oxide assays.
The output is SIMULATED / UNCALIBRATED_SCENARIO, not a Gale or Phoenix measurement.
Recipe and custody hashes are input provenance. Real force/torque/weather
series remain absent until instrument data supplies them.
