# REDLINE

**Known · Unknown · Red line** — an uncertainty-aware Mars EVA planning tool built for NASA Space Apps 2026.

Map uncertainty is converted into a *return margin*: the red line shows how far a crew can safely go given what is known, what is not, and the current radiation environment. Robot observations update the plan, and a radiation event triggers re-planning.

*TR: Haritadaki belirsizlikler dönüş payına bağlanır; robot gözlemleri planı günceller, radyasyon olayı yeniden planlamayı tetikler.*

> **Status:** idea phase finished; implementation is at milestone **T0** (infrastructure). Nothing is marked done without observed test evidence — see [journal/PROGRESS.md](journal/PROGRESS.md).

## Repository layout

| Path | Contents |
|---|---|
| [docs/](docs/) | [Implementation spec (`proje.md`)](docs/proje.md), decisions, verification log, AI disclosure, pre-existing work |
| [journal/](journal/README.md) | Hackathon development log — progress per milestone and dated session notes |
| [research/](research/README.md) | Entire research & idea phase: concept evolution, data-source notes, metadata checks, council records |
| [python/](python/) | `redline_core` (core algorithms) and `redline_data` (data tooling) |
| [ros_ws/](ros_ws/) | ROS 2 workspace (`redline_msgs` interfaces) |
| [config/](config/), [scripts/](scripts/), [tools/](tools/) | Runtime defaults, bootstrap/test scripts, repo tooling |
| [.github/](.github/) | CI (pytest + colcon) |

## Build & test

Target: ROS 2 Jazzy, Python 3.12 (Ubuntu 24.04 / WSL).

```bash
bash scripts/bootstrap.sh   # isolated venv + dependencies
bash scripts/test.sh        # pytest + colcon build/test
```

## Honesty notes

- NASA/USGS measurements are kept separate from `DERIVED`, `SIMULATED` and `SCENARIO` data; provenance is preserved.
- Design documents in `research/` are not a working application.
- AI assistance is disclosed in [docs/AI_DISCLOSURE.md](docs/AI_DISCLOSURE.md); third-party material in [docs/PRE_EXISTING_WORK.md](docs/PRE_EXISTING_WORK.md).
- Visual design and 3D assets are developed together with the project owner and are not part of this stage.
