"""Export presentation figures from recorded REDLINE products without rerunning models.

Run with a Python environment containing Matplotlib, NumPy and Pillow. All
values are read from preserved products; nothing is inferred from Unreal shots.
The scientific-visualization skill informed export/provenance checks; see the
generated README for its attribution. This script is new REDLINE work.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RUN = "20261115T091829Z-BXW_CAMPAIGN-15"
LAB_RUN = "20261115T075634Z-BXW_CAMPAIGN-15"
BG, FG, MUTED, COPPER, GREEN = "#f4f0e8", "#282725", "#595650", "#9b4c21", "#31604c"
records = []
sources = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(relative):
    path = ROOT / relative
    sources[str(relative).replace("\\", "/")] = sha(path)
    return json.loads(path.read_text(encoding="utf-8"))


def product(prefix, run=RUN):
    matches = sorted((ROOT / "data/products" / run).glob(f"sim-{prefix}-*.json"))
    if len(matches) != 1:
        raise ValueError(f"Expected one preserved {prefix} product, found {len(matches)}")
    relative = matches[0].relative_to(ROOT)
    data = load(relative)
    if data["provenance_status"] != "SIMULATED":
        raise ValueError("These captions require explicit SIMULATED source products")
    if data["measurement"]["noise_calibration"] != "UNCALIBRATED_SCENARIO":
        raise ValueError("Unexpected calibration status")
    return data, relative


def base(title, subtitle, note):
    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=BG)
    fig.text(.06, .925, title, fontsize=26, weight="bold", color=FG)
    fig.text(.06, .873, subtitle, fontsize=15, color=MUTED)
    wrapped = "\n".join(line for paragraph in note.splitlines() for line in textwrap.wrap(paragraph, width=132))
    fig.text(.06, .065, wrapped, fontsize=12, color=MUTED, linespacing=1.5)
    fig.text(.94, .025, "REDLINE  /  15 KASIM 2026", ha="right", fontsize=10, color=MUTED)
    return fig


def axes(fig, rect=(.09, .20, .84, .59)):
    ax = fig.add_axes(rect, facecolor=BG)
    ax.spines[["right", "top"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=FG, labelsize=13)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    return ax


def table(out, name, header, rows):
    path = out / "data" / f"{name}.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
    return str(path.relative_to(out))


def save(fig, out, name, caption, alt, source_paths, transformations, data_file):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for text in fig.texts:
        bounds = text.get_window_extent(renderer)
        if bounds.x0 < 0 or bounds.x1 > 1920 or bounds.y0 < 0 or bounds.y1 > 1080:
            raise ValueError(f"Clipped figure text in {name}: {text.get_text()}")
    paths = []
    for ext in ("png", "svg"):
        path = out / f"{name}.{ext}"
        fig.savefig(path, dpi=120, facecolor=BG, transparent=False, bbox_inches=None)
        paths.append({"path": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    plt.close(fig)
    with Image.open(out / f"{name}.png") as image:
        if image.size != (1920, 1080):
            raise ValueError("Unexpected figure export dimensions")
        dimensions = image.size
    record = {"id": name, "caption": caption, "alt_text": alt,
              "sources": [str(p).replace("\\", "/") for p in source_paths],
              "transformations": transformations, "data": data_file,
              "image_size_px": dimensions, "outputs": paths,
              "destination": "16:9 presentation/video insert; no journal submission standard claimed"}
    records.append(record)
    return record


def chemistry(out, prefix, title):
    data, path = product(prefix)
    m = data["measurement"]
    labels, values, sigma = m["labels"], m["values"], m["sigma"]
    if not (len(labels) == len(values) == len(sigma)):
        raise ValueError("Mismatched chemistry arrays")
    fig = base(title, "BXW_RIDGE_A  ·  Tek model ürünü  ·  Entegrasyon: 20 s",
               "SIMULATED / UNCALIBRATED_SCENARIO  ·  Hata çubukları: modelin ±1σ gürültü parametresi (1,4 yüzde puanı).\n"
               "Bağımsız tekrar yok; güven aralığı veya NASA kimyasal analizi değildir. Gösterilen oksitler %100'e tamamlanmaz.")
    ax = axes(fig, (.13, .23, .78, .55))
    y = np.arange(len(labels))
    ax.errorbar(values, y, xerr=sigma, fmt="o", color=COPPER, ecolor=FG,
                markersize=10, capsize=6, linewidth=2)
    for x, row in zip(values, y):
        ax.text(x + 2.2, row, f"{x:.2f}", va="center", fontsize=16, color=FG)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(v + s for v, s in zip(values, sigma)) * 1.18)
    ax.set_xlabel("Kütle oranı (%) / SCENARIO", labelpad=12, fontsize=16)
    ax.grid(axis="x", color="#d4cec4", linewidth=.7)
    name = f"{prefix}_bilesim"
    data_file = table(out, name, ("oxide", "mass_percent_SCENARIO", "model_sigma_percentage_points"), zip(labels, values, sigma))
    return save(fig, out, name,
                f"{data['instrument']} authored scenario composition for {data['target_id']}; one model product, not a measured spectrum. Error bars are Gaussian model-noise sigma, not confidence intervals. No normalization or closure to 100%.",
                "Yatay nokta grafiğinde Al2O3, CaO, FeO, MgO ve SiO2 oranları model gürültü çubuklarıyla gösterilir; SiO2 en yüksek değerdir.",
                [path], ["Exact recorded labels/values/sigma; no filtering, averaging, normalization or interpolation"], data_file)


def lab(out):
    verified = load(Path("test-results/tablet-lab-flow/verification.json"))
    if not verified["passed"] or not all(verified["checks"].values()):
        raise ValueError("Laboratory acceptance record is not passing")
    data, path = product("wcl_scenario", LAB_RUN)
    m = data["measurement"]
    if data["product_id"] != verified["product"]["product_id"] or m["series"] != verified["product"]["summary"]["series"]:
        raise ValueError("Product differs from verified lab series")
    t, ph, ec = (m["series"][k] for k in ("time_s", "ph", "conductivity_ms_cm"))
    if not (len(t) == len(ph) == len(ec) == 31):
        raise ValueError("Expected recorded 31-point lab series")
    fig = base("Numune laboratuvarı / pH ve iletkenlik", "31 kayıtlı model noktası  ·  0–120 s model entegrasyonu  ·  Tek numune",
               "SIMULATED / UNCALIBRATED_SCENARIO  ·  Gale veya Phoenix ölçümü değildir; oksitlerden pH çıkarılmadı.\n"
               "Çizgiler kayıtlı model noktalarını birleştirir; yumuşatma yok. pH model σ = 0,12; seri noktaları bağımsız deney tekrarı değildir.")
    a = axes(fig, (.09, .54, .84, .25))
    b = axes(fig, (.09, .22, .84, .23))
    a.plot(t, ph, "o-", color=GREEN, linewidth=2.3, markersize=5)
    a.set(xlim=(0, 120), ylim=(0, 14), ylabel="pH (0–14)")
    a.set_xticks([0, 30, 60, 90, 120])
    a.text(.99, .95, f"Son kayıt: pH {ph[-1]:.2f}", ha="right", va="top", transform=a.transAxes, fontsize=16, color=FG)
    b.plot(t, ec, "s-", color=COPPER, linewidth=2.3, markersize=4.5)
    b.set(xlim=(0, 120), ylim=(0, 1.4), xlabel="Model entegrasyon zamanı (s)", ylabel="İletkenlik\n(mS cm⁻¹)")
    b.set_xticks([0, 30, 60, 90, 120])
    b.text(.99, .12, f"Son kayıt: {ec[-1]:.3f} mS cm⁻¹", ha="right", transform=b.transAxes, fontsize=16, color=FG)
    for ax in (a, b):
        ax.grid(color="#d4cec4", linewidth=.7)
    data_file = table(out, "laboratuvar_ph_ec", ("model_time_s", "ph", "conductivity_ms_cm"), zip(t, ph, ec))
    return save(fig, out, "laboratuvar_ph_ec",
                "Preserved WCL_SCENARIO product from an accepted ROS AnalyzeSample operation on a recorded sample with custody evidence. These are authored game-model time points; not archive chemistry or independent replicates. Conductivity and pH use aligned separate panels; no inferred correlation.",
                f"İki hizalı grafikte 120 saniyelik model boyunca pH ve iletkenlik noktaları gösterilir. Son pH {ph[-1]:.2f}, iletkenlik {ec[-1]:.3f} mS/cm. Her iki seri simülasyondur.",
                [path, "test-results/tablet-lab-flow/verification.json"],
                ["Exact recorded model time/series; no smoothing, extrapolation, normalization or statistical interval"], data_file)


def neutron(out):
    data, path = product("dan")
    m, grid = data["measurement"], data["measurement"]["posterior_grid"]
    w, h, res = grid["width"], grid["height"], grid["resolution_m"]
    if w != 9 or h != 9 or len(grid["values"]) != w*h or len(grid["sigma"]) != w*h:
        raise ValueError("Unexpected recorded DAN grid")
    # The core records lower-left cell-centre coordinates, row-major y then x.
    x0, y0 = grid["origin_m"]
    extent = (x0-res/2, x0+(w-.5)*res, y0-res/2, y0+(h-.5)*res)
    fig = base("DAN / yeraltı hidrojen göstergesi", "9 × 9 yerel model ızgarası  ·  Hücre aralığı: 0,5 m  ·  map / ENU",
               "SIMULATED / UNCALIBRATED_SCENARIO  ·  Tek model girdisi; fiziksel nötron sayacı veya yeraltı su haritası değildir.\n"
               "RBF modelinin posterior ortalaması ve model σ'sı aynen çizilir. Renkler % SCENARIO; belirsizlik deneysel güven aralığı değildir.")
    for i, key in enumerate(("values", "sigma")):
        ax = axes(fig, (.08+i*.46, .25, .34, .48))
        z = np.array(grid[key]).reshape(h, w)
        im = ax.imshow(z, extent=extent, origin="lower", interpolation="nearest", cmap="cividis", aspect="equal",
                       vmin=0, vmax=5 if key == "values" else 1)
        fig.colorbar(im, ax=ax, fraction=.047, pad=.035, label="% SCENARIO")
        ax.set_title("Model ortalaması / WEH" if i == 0 else "Model belirsizliği / σ", fontsize=17, pad=14, color=FG)
        ax.set(xlabel="Doğu / map x (m)", ylabel="Kuzey / map y (m)")
        target, = ax.plot([data["target_point_m"][0]], [data["target_point_m"][1]], marker="x", markersize=10, color=FG, markeredgewidth=2)
        target.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])
    fig.text(.10, .80, f"Tek girdide tüm ortalama hücreleri: {grid['values'][0]:.3f} % SCENARIO", fontsize=13, color=MUTED)
    rows = [(x0+col*res, y0+row*res, grid["values"][row*w+col], grid["sigma"][row*w+col]) for row in range(h) for col in range(w)]
    data_file = table(out, "dan_yerel_model", ("map_x_m", "map_y_m", "mean_percent_SCENARIO", "model_sigma_percent_SCENARIO"), rows)
    return save(fig, out, "dan_yerel_model", "Recorded RBF posterior-grid mean and sigma; 9×9 cell centres in local map ENU metres. No interpolation of display pixels, added observations, global CRS inference or physical neutron data. Outlined crosses mark the target point, not independent observations.",
                "Yan yana iki 9×9 hücre haritası model hidrojen eşdeğeri ortalamasını ve model sigma belirsizliğini gösterir. Bu yerel simülasyon ızgarası gerçek yeraltı suyu haritası değildir.",
                [path, "python/redline_core/src/redline_core/science_operations.py"], ["Recorded row-major 9×9 grid reshaped; extent uses recorded cell centres and 0.5 m spacing; nearest-neighbour display; fixed zero-baseline colour scales mean 0–5%, sigma 0–1% to avoid amplifying tiny model variation"], data_file)


def drill(out):
    data, path = product("drill")
    d = data["measurement"]["drill"]
    fig = base("Sondaj / kaydedilen işlem sonucu", "BXW_RIDGE_A  ·  DRILL_SCENARIO  ·  Tek tamamlanmış model işlemi",
               "SIMULATED / UNCALIBRATED_SCENARIO  ·  Son değerler gösterilir; derinlik-zaman eğrisi kaydedilmedi.\n"
               "Kuvvet sensörü yok. Toprak teması, mekanik delme veya fiziksel numune çıkarma doğrulaması değildir.")
    ax = axes(fig, (.17, .27, .46, .47))
    values = [d["requested_depth_mm"], d["achieved_depth_mm"]]
    ax.barh(["İstenen derinlik", "Model sonucu"], values, color=["#746b5e", COPPER], height=.45)
    ax.set_xlim(0, 60)
    ax.set_xlabel("Derinlik (mm)", fontsize=16, labelpad=12)
    ax.invert_yaxis()
    for y, x in enumerate(values):
        ax.text(x+1, y, f"{x:.0f} mm", va="center", fontsize=18, color=FG)
    fig.text(.70, .68, "NUMUNE KAYDI", fontsize=15, color=MUTED)
    fig.text(.70, .61, data["sample"]["sample_id"], fontsize=16, color=FG)
    fig.text(.70, .52, "Durum: " + data["sample"]["state_name"], fontsize=18, color=FG)
    fig.text(.70, .44, "Fiziksel kuvvet sensörü: yok", fontsize=15, color=FG)
    fig.text(.70, .37, "Bu üründe arıza kurtarma: " + ("var" if d["scenario_stall_recovered"] else "yok"), fontsize=15, color=FG)
    data_file = table(out, "sondaj_sonucu", ("field", "value", "unit"), (("requested_depth", values[0], "mm"), ("achieved_model_depth", values[1], "mm"), ("physical_force_sensor", d["physical_force_sensor"], "boolean")))
    return save(fig, out, "sondaj_sonucu", "Requested and achieved model endpoint depths, both 50 mm. No trajectory is reconstructed because the accepted product contains no depth time series. Sample acquisition is a scenario record, not physical drilling acceptance.",
                "İki yatay çubuk istenen ve modelin bildirdiği 50 mm son derinliği gösterir. Ayrı alanda numune kimliği ve fiziksel kuvvet sensörü olmadığı yazılıdır.",
                [path], ["Exact two recorded endpoint depths; zero-baseline bars; no invented temporal interpolation"], data_file)


def custody(out):
    path = Path(f"data/products/{LAB_RUN}/sample-smp-BXW-85834d87582d.json")
    sample = load(path)
    origin, analysis = sample["origin_point_m"], sample["analysis_point_m"]
    fig = base("Numune / köken ve analiz yeri ayrı", sample["sample_id"] + "  ·  " + sample["state_name"],
               "SIMULATED numune zinciri  ·  Noktalar yerel map / ENU koordinatlarıdır. Fiziksel taşıma rotası çizilmedi.\n"
               "Bu testte insan pozu açıkça yer değiştiren bir fixture'dır; yürüyüş süresi veya sarf kabulü değildir.")
    ax = axes(fig, (.08, .24, .51, .52))
    ax.scatter([origin[0]], [origin[1]], marker="o", s=160, color=COPPER, edgecolor=FG, label="Numune kökeni")
    ax.scatter([analysis[0]], [analysis[1]], marker="s", s=140, color=GREEN, edgecolor=FG, label="Analiz yeri")
    ax.set(xlabel="Doğu / map x (m)", ylabel="Kuzey / map y (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.margins(.18)
    ax.grid(color="#d4cec4", linewidth=.7)
    ax.legend(loc="upper right", fontsize=13, frameon=False)
    fig.text(.65, .70, "KAP VE KANIT", fontsize=16, color=MUTED)
    fig.text(.65, .63, "Konteyner: …-01", fontsize=18, color=FG)
    fig.text(.65, .56, f"Bağlı kanıt: {len(sample['evidence_ids'])}", fontsize=18, color=FG)
    fig.text(.65, .48, f"Köken ENU: ({origin[0]:.1f}, {origin[1]:.1f}) m", fontsize=16, color=FG)
    fig.text(.65, .41, f"Analiz ENU: ({analysis[0]:.1f}, {analysis[1]:.1f}) m", fontsize=16, color=FG)
    fig.text(.65, .31, "Tam kimlikler ve kanıtlar\nJSON / CSV kaydında korunur.", fontsize=14, color=MUTED, linespacing=1.5)
    data_file = table(out, "numune_koken_analiz", ("role", "map_x_m", "map_y_m", "map_z_m", "sample_id", "container_id"), [(label, *point, sample["sample_id"], sample["container_id"]) for label, point in (("origin", origin), ("analysis", analysis))])
    return save(fig, out, "numune_koken_analiz", "Persisted sample has separate collection-origin and analysis-location records, a container and two custody evidence IDs. The plot deliberately does not connect them by an invented travelled route. Human positions in this run were a simulation fixture.",
                "Haritada numune kökeni daire, laboratuvar analiz yeri kare ile gösterilir; aralarında yürüyüş yolu çizilmez. Sağ tarafta kap ve iki kanıt kaydı olduğu yazılıdır.",
                [path], ["Exact persisted local ENU coordinates; x/y projection only; no path or travel-cost reconstruction"], data_file)


def station(out):
    data, path = product("dosimeter")
    if data["measurement"]["labels"] or data["measurement"]["values"]:
        raise ValueError("Deployment caption requires a deployment-only product")
    fig = base("Çevre istasyonu / yerleştirme kaydı", "Kayıtlı ürün: DOSIMETER  ·  BXW_RIDGE_A",
               "SIMULATED / UNCALIBRATED_SCENARIO  ·  Bu ürün yalnızca yerleştirme kaydıdır.\n"
               "Doz hızı, atmosfer, sıcaklık veya toz serisi içermediği için ölçüm grafiği üretilmedi.")
    p = data["instrument_point_m"]
    fig.text(.08, .68, "YERLEŞTİRME KAYDEDİLDİ", fontsize=30, color=GREEN, weight="bold")
    fig.text(.08, .56, f"Yerel konum:  x {p[0]:.2f} m  /  y {p[1]:.2f} m", fontsize=22, color=FG)
    fig.text(.08, .46, "Çerçeve: map / ENU  ·  Durum: SIMULATED", fontsize=20, color=FG)
    fig.text(.08, .36, "Zaman: " + data["measured_utc"].replace("T", "  "), fontsize=17, color=MUTED)
    fig.text(.08, .25, "Sonraki doğrulama: fiziksel istasyon + sensör telemetrisi", fontsize=20, color=FG)
    data_file = table(out, "istasyon_yerlestirme", ("map_x_m", "map_y_m", "map_z_m", "measured_utc", "product_id"), [(*p, data["measured_utc"], data["product_id"])])
    return save(fig, out, "istasyon_yerlestirme", "The accepted DOSIMETER product records a scenario deployment and position only. It has no dose-rate or weather values, so this figure is a deployment record rather than a manufactured sensor chart.",
                "Metin kartı simülasyonda istasyon yerleştirildiğini ve kaydedilen ENU konumunu gösterir. Üründe doz veya hava serisi bulunmadığı açıkça yazılıdır.",
                [path], ["Exact deployment position and source timestamp; no quantitative measurement graph generated"], data_file)


def scout(out):
    feed_path = Path("test-results/campaign-field-physical-post-recovery/ue_feed.jsonl")
    verify_path = Path("test-results/campaign-field-physical-post-recovery/scout-trajectory-verification.json")
    verified = load(verify_path)
    full = ROOT / feed_path
    sources[str(feed_path)] = sha(full)
    if not verified["passed"] or verified["source_feed_sha256"] != sha(full):
        raise ValueError("Scout feed differs from accepted trajectory")
    rows = []
    for line in full.open(encoding="utf-8"):
        record = json.loads(line)
        packet = record.get("message", record)
        if packet.get("topic") != "/redline/campaign/state":
            continue
        state = json.loads(packet["msg"]["data"])
        s = state.get("scout", {})
        if s.get("physical_backend") is True and s.get("request_id") and s.get("phase") in ("TAKEOFF", "SURVEY", "RETURN", "LANDING", "COMPLETE"):
            rows.append((record["elapsed"], *s["map_xyz_m"], s["phase"]))
            if s["phase"] == "COMPLETE":
                break
    if len(rows) < 100:
        raise ValueError("Insufficient preserved physical flight records")
    # Include each recorded sample, including duplicates. The x axis is captured
    # wall time because no per-envelope physics timestamp was saved in this feed.
    t0 = rows[0][0]
    origin = verified["origin_map_xyz_m"]
    xyz = np.array([r[1:4] for r in rows])
    fig = base("Drone / Gazebo uçuşunun kayıtlı izi", "Gerçek ROS/Gazebo pozları  ·  Kalkış → tarama → dönüş → iniş",
               "SCENARIO uçuş parametreleri  ·  İz, kayıtlı fizik pozlarından gelir; algısal bir yüzey haritası değildir.\n"
               "Gözlem adaptörü SIMULATED truth kullanır. Sağ eksen kayıt duvar zamanı; hızlandırılmış fizik zamanı ile eşitlenmedi.")
    a = axes(fig, (.08, .25, .38, .49))
    a.plot(xyz[:, 0], xyz[:, 1], "-", color=FG, linewidth=1.6)
    a.scatter([origin[0]], [origin[1]], marker="s", s=100, color=COPPER, label="Kalkış / dönüş")
    a.set(xlabel="Doğu / map x (m)", ylabel="Kuzey / map y (m)")
    a.set_aspect("equal", adjustable="datalim")
    a.grid(color="#d4cec4", linewidth=.7)
    a.legend(loc="upper right", fontsize=13, frameon=False)
    b = axes(fig, (.56, .25, .37, .49))
    b.plot([r[0]-t0 for r in rows], xyz[:, 2]-origin[2], "-", color=GREEN, linewidth=2)
    b.set(xlabel="Kalkıştan sonra kayıt duvar zamanı (s)", ylabel="Kalkış z'sine göre yükseklik (m)")
    b.set_ylim(0, 23)
    b.grid(color="#d4cec4", linewidth=.7)
    fig.text(.57, .76, f"Kayıtlı yükselme: {verified['climb_m']:.2f} m   ·   En uzak: {verified['maximum_home_distance_m']:.2f} m", fontsize=14, color=FG)
    data_file = table(out, "drone_fizik_izi", ("capture_wall_s", "map_x_m", "map_y_m", "map_z_m", "phase"), rows)
    return save(fig, out, "drone_fizik_izi", "Actual recorded scout_flight physical Gazebo pose trace from a passing prior integration run. All recorded points retained, including repeated positions. Height is source z minus recorded origin z; time is capture wall time relative to first TAKEOFF record. No sensor perception or surface map is claimed; human was a pose fixture.",
                f"Solda gerçek Gazebo drone pozlarının yerel ENU izi, sağda kalkışa göre yüksekliği görülür. Drone {verified['climb_m']:.2f} m yükselip geri döner. Bu çizim sensörden üretilen Mars yüzey haritası değildir.",
                [feed_path, verify_path], ["Preserved actual physical_backend=true poses; one recorded request from first TAKEOFF through first COMPLETE, excluding post-flight idle; XY projection; height minus recorded origin; capture wall time offset only; no smoothing/downsampling/interpolation"], data_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/feature-videos/results")
    parser.add_argument("--force", action="store_true", help="Regenerate only this script's named exports")
    args = parser.parse_args()
    out = args.out.resolve()
    if (out / "manifest.json").exists() and not args.force:
        parser.error("Existing export manifest; use --force for an intentional regeneration")
    (out / "data").mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 15, "axes.labelsize": 15,
                         "svg.fonttype": "none", "axes.unicode_minus": False,
                         "savefig.transparent": False}):
        chemistry(out, "apxs", "El tipi temas ölçümü / oksit bileşimi")
        chemistry(out, "libs", "Rover LIBS / oksit bileşimi modeli")
        lab(out)
        neutron(out)
        drill(out)
        custody(out)
        station(out)
        scout(out)
    # Preserve compact source JSON snapshots with their SHA-256 records. The
    # larger trajectory source remains immutable in the repository; CSV provides
    # every selected physical record for the presentation package.
    for relative in list(sources):
        p = ROOT / relative
        if p.suffix == ".json":
            destination = out / "data" / p.name
            if destination.exists() and sha(destination) != sha(p):
                raise ValueError(f"Conflicting source snapshot filename: {p.name}")
            shutil.copyfile(p, destination)
    sources[str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/")] = sha(__file__)
    for relative in ("python/redline_core/src/redline_core/science_operations.py", "python/redline_core/src/redline_core/lab_assay.py"):
        sources[relative] = sha(ROOT / relative)
    manifest = {"schema": "redline.presentation.science-figures.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "Recorded SIMULATED science products and one actual prior Gazebo scout pose trace; no new models or measurements",
                "generator": "scripts/plot_feature_science.py", "matplotlib": matplotlib.__version__,
                "numpy": np.__version__, "sources_sha256": sources, "figures": records,
                "data_files_sha256": {str(p.relative_to(out)): sha(p) for p in sorted((out / "data").iterdir()) if p.is_file()},
                "common_policy": "No smoothing, fabricated points, calibration claims or extrapolated flight/measurement curves. CSV source alternatives and alt text included. Fixed 1920x1080 opaque PNG plus editable-text SVG; no formal accessibility or publisher compliance claim.",
                "workflow_attribution": "Kassis T., Agarwal V., He Y., Patel D., Brueckner A. M. (2026), Scientific Agent Skills, arXiv:2609.00065, current v2 checked 2026-11-15; https://doi.org/10.48550/arXiv.2609.00065"}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# REDLINE bilim sonuçları / sunum görselleri", "", "15 Kasım 2026 · 1920×1080 PNG + metni düzenlenebilir SVG + CSV / kaynak JSON.", "",
             "Bilim ürünleri **SIMULATED / UNCALIBRATED_SCENARIO** durumundadır. Bunlar NASA/Gale ölçümü değildir. Drone izi ise kabul kaydındaki gerçek ROS/Gazebo pozlarından çizilir; gözlem adaptörü SIMULATED truth kullanır ve bu şekil algısal yüzey haritası değildir.", "",
             "| Görsel | İçerik |", "|---|---|"]
    for record in records:
        lines.append(f"| [{record['id']}.png]({record['id']}.png) / [SVG]({record['id']}.svg) | {record['alt_text']} |")
    lines += ["", "Her şeklin kaynak yolu, SHA-256 özeti, açıklaması ve dönüşümleri `manifest.json` içindedir. CSV dosyaları `data/` altında. Bilim değerleri yeniden üretilmedi, normalize edilmedi ve yumuşatılmadı. Hata çubukları model gürültü parametresidir; deneysel güven aralığı değildir.", "",
              "İstasyon ürünü bir yerleştirme kaydıdır; sıcaklık, doz hızı veya atmosfer verisi içermez. Sondaj ürünü son derinlik değerlerini içerir; kaydedilmemiş bir derinlik-zaman serisi çizilmedi. Numune haritası köken ve analiz yerini ayrı gösterir; doğrulanmamış yürüyüş çizilmedi.", "",
              "Tekrar üretim: proje sanal ortamındaki Python ile `scripts/plot_feature_science.py` çalıştırılır; mevcut çıktıları yenilemek için `--force` gerekir. Ham ürünler ve ham uçuş kaydı yerinde korunur.", "",
              "Çizim/provenans kontrolünde scientific-visualization becerisi kullanıldı. Kaynak: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [arXiv:2609.00065](https://doi.org/10.48550/arXiv.2609.00065). Güncel v2 kaydı 15 Kasım 2026'da kontrol edildi.", ""]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"out": str(out), "figures": len(records), "png_svg_files": 2*len(records), "manifest": str(out / "manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
