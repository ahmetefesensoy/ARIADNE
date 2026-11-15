# REDLINE v3 — Uygulama spesifikasyonu

14 Kasım 2026 · Okur: yeni depoda REDLINE'ı sıfırdan kodlayacak AI ajanı ve CRST mühendisleri.

[REDLINE_V3_KILAVUZU.md](README.md) **ne** yapılacağını ve **neden** yapılacağını anlatır. Bu belge **nasıl** yapılacağını anlatır: depo yapısı, mesaj tanımları, düğümler, algoritmalar, Unreal sınıfları, testler ve kabul ölçütleri. Fikir sabittir; bu belge kapsamı değiştirmez, yalnız uygulamayı tanımlar.

Etiketler: **[D]** 14 Kasım'da birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** kodlamadan önce kontrol et.

---

## 0. AI ajanı için çalışma kuralları

1. **Okuma sırası:** bu belgenin §0–4'ü → üzerinde çalışılan bölüm → kılavuzun ilgili bölümü.
2. **Sırayla ilerle:** §18'deki kilometre taşlarını sırayla uygula. Her taşın "bitti" ölçütü sağlanmadan sonrakine geçme.
3. **Veri uydurma:** hiçbir NASA ölçüm değeri uydurulmaz. Her sayısal katman bir ürün kimliğine veya açık bir senaryo tohumuna bağlanır. Her kayıt `Provenance.status` taşır: ARCHIVE / DERIVED / SIMULATED / SCENARIO.
4. **CRS:** her ürünün CRS'i kendi etiketinden veya WKT'sinden okunur. Dünya/WGS84 varsayılanı kullanılmaz. Bounding-box örtüşmesi hizalama kanıtı sayılmaz.
5. **Eski kod:** `önceki deneme/` ve `roversim27` kodu kopyalanmaz. Yeni depoda yeniden yazılır.
6. **Test:** her `redline_core` fonksiyonu için birim test yazılır. Her ROS düğümü için en az bir `launch_testing` veya pytest entegrasyon testi yazılır.
7. **Belirsizlik:** [?] etiketli bir API veya ürünü kullanmadan önce gerçek davranışı küçük bir denemeyle doğrula ve sonucu `docs/VERIFICATION_LOG.md`'ye yaz.
8. **Sırlar:** API anahtarı veya kişisel bilgi depoya yazılmaz. Cesium ion anahtarı gerekirse ortam değişkeninden okunur.
9. **Raporlama:** bir taşı bitirince ne çalıştığını, hangi testin geçtiğini ve neyin eksik kaldığını `docs/PROGRESS.md`'ye yaz.

---

## 1. Sabit kararlar

- Ürün: katmanlı EVA haritası + kırmızı çizgi. Unreal prova görünümüdür.
- Sahalar:
  - **BXW** (boxwork-Batı): ileri EVA ve V2 zaman bölmeli testi
  - **YKB** (Yellowknife Bay): V1 tutarlılık kontrolü ve sol 242 sahnesi
- Kriz verisi: RAD sol 4190 (ana) ve sol 242 (destek).
- Beş görev = tek EVA'nın beş evresi (kılavuz §5).
- Robot fiziği ve otonomi ROS 2 Jazzy + Gazebo Harmonic'te; insan ve arayüz Unreal 5.8.4'te.
- Bilim görevleri ROS aksiyonlarıyla yürür ve haritaya katman yazar (§9).

---

## 2. Ortam

| Bileşen | Sürüm | Not |
|---|---|---|
| Windows | 11 | Unreal, Open MCT tarayıcısı |
| WSL2 | Ubuntu 24.04 | ROS ve Gazebo |
| ROS 2 | Jazzy | `ROS_DOMAIN_ID=77` |
| Gazebo | Harmonic | `GZ_PARTITION=redline` |
| Unreal | 5.8.4 | C++ projesi (Blueprint-only değil) |
| Python | 3.12 (Ubuntu 24.04 varsayılanı) | venv: `redline_data` ve `redline_core` için |
| Node.js | 20 LTS [?] | Open MCT |
| GDAL | ≥ 3.8 | `/vsicurl/` ile COG pencere okuma |

Portlar:
- rosbridge `9090`
- foxglove_bridge `8765`
- Open MCT `8080`
- telemetri geçmiş servisi `8081`
- web harita `8082`

Ağ: Windows'tan WSL'e `localhost` yönlendirmesi ilk saatte test edilir. Çalışmazsa `.wslconfig` içinde `networkingMode=mirrored` [?] veya WSL IP'si kullanılır.

---

## 3. Depo yapısı

```
redline/
├─ AGENTS.md                      # §21 şablonu
├─ README.md
├─ docs/
│  ├─ PROGRESS.md  VERIFICATION_LOG.md  DECISIONS.md
│  ├─ PRE_EXISTING_WORK.md  DATA_SOURCES.md  THIRD_PARTY_NOTICES.md  AI_DISCLOSURE.md
├─ config/
│  ├─ sites.yaml                  # saha tanımları (§6.1)
│  ├─ products.yaml               # ürün kataloğu (§6.1)
│  ├─ crew.yaml  suit.yaml  rover.yaml  drone.yaml
│  ├─ rules.yaml                  # uçuş kuralları (§12)
│  └─ scenarios/*.yaml            # §16
├─ data/                          # .gitignore: büyük dosyalar; yalnız manifest ve hash'ler commit edilir
│  ├─ raw/  derived/  engines/  env/  stac/
├─ python/
│  ├─ redline_data/               # veri hattı (CLI: `redline-data`)
│  └─ redline_core/               # ROS'tan bağımsız algoritma kütüphanesi
├─ ros_ws/src/
│  ├─ redline_msgs/               # msg/srv/action
│  ├─ redline_bringup/            # launch, profiller, ros_gz_bridge yaml
│  ├─ redline_gazebo/             # dünya, modeller, senaryo kayaları
│  ├─ redline_description/        # rover, drone, proxy URDF/SDF
│  ├─ redline_navigation/         # Nav2 parametreleri, BT XML
│  ├─ redline_mission/            # mission_manager, command_authority, cell_store, voi_tasker
│  ├─ redline_planner/            # planner_server, walkback_field, rover_placer, science_optimizer
│  ├─ redline_env/                # sim_clock, scenario_player, rad_replay, rems_replay, env_server
│  ├─ redline_crew/               # ev_sim, human_model, consumables_estimator
│  ├─ redline_science/            # enstrüman çatısı ve bilim düğümleri (§9)
│  ├─ redline_safety/             # rule_monitor, safety_aggregator
│  ├─ redline_comm/               # link_manager
│  └─ redline_telemetry/          # telemetry_adapter, history_server
├─ unreal/Redline/                # UE 5.8.4 projesi (§13)
├─ openmct/                       # Open MCT eklentisi (§14)
├─ web/                           # statik harita (§15)
├─ validation/                    # V1, V2, V3 not defterleri ve çıktılar
└─ scripts/                       # start_all.ps1, start_backend.sh, check_ready.py
```

Python paketleri `pip install -e python/redline_core python/redline_data` ile kurulur. ROS düğümleri `redline_core`'u import eder: algoritma tek yerde yaşar.

---

## 4. Ortak sözleşmeler

### 4.1 Kimlikler
- `site_id`: `BXW`, `YKB`, `JEZ`
- `run_id`: `YYYYMMDDThhmmssZ-<scenario_id>-<seed>`
- `evidence_id`: `ev-<run_id>-<seq>`
- `sample_id`: `smp-<site>-<seq>`
- `product_id`: gerçek ürünlerde gerçek ID; simülede `sim-<instrument>-<run_id>-<seq>`
- `crew_id`: `EV1`, `EV2`
- `vehicle_id`: `rover_1`, `scout_1`, `pr_1` (basınçlı rover)

### 4.2 Çerçeveler
- `map`: yerel ENU, metre. x=doğu, y=kuzey, z=yukarı. Orijin `sites.yaml`'daki `(E0, N0, H0)`.
- Her araç: `<vehicle>/odom → <vehicle>/base_link → sensör frame'leri`. Her dönüşümün tek yayıncısı olur.
- `map → <vehicle>/odom`: `localization` düğümü yayımlar. Başlangıçta manifestteki spawn pozu kullanılır.
- **eqc → ENU dönüşümü** (Gale ürünleri: eqc, R = 3.396.190 m, lon_0 = 0, lat_ts = 0 [K]):
  - `E = R·λ` (λ radyan, doğu pozitif), `N = R·φ`
  - `x = (E − E0)·cos φ0`, `y = N − N0`, `z = H − H0`
  - `cos φ0` düzeltmesi zorunludur: lat_ts=0 eqc'de −4,8° enleminde doğu-batı mesafesi %0,35 büyük görünür (2 km'de ≈7 m).
- **ROS → Unreal:** `ue = (100·x, −100·y, 100·z)` cm. Quaternion `(x, y, z, w) → FQuat(−x, y, −z, w)`. Ters dönüşüm aynı formüldür.
- **Kamera optik frame'i** (z ileri, x sağ, y aşağı) için ayrı statik TF tanımlanır.

### 4.3 Zaman
- **İki saat (son inceleme kararı):**
  - **Fizik saati:** Gazebo `/clock`. Gazebo gerçek zaman çarpanı (RTF) ≈ 1'de çalışır ve hızlandırılamaz.
  - **Görev saati (PET):** `scenario_player` yönetir: `/redline/mission/clock`. Hızlandırılabilir ve atlanabilir.
  - 4 saatlik bir EVA demoda gerçek zamanlı oynatılamaz. Sarf tüketimi, crew durumu ve RAD/REMS replay görev saatine bağlıdır. Robotlar yalnız aktif segmentlerde gerçek zamanlı fizikte koşar.
  - Atlama (`ScenarioControl.SEEK`) sırasında robotlar planlanan rotaya yerleştirilir: Gazebo `set_pose`, kayıtta "teleport" etiketi.
- ROS `use_sim_time: true` fizik saatidir. Replay eşlemesi görev saatiyle yapılır: `utc = utc0 + scale·(t_mission − t0)`.
- **LMST (Mars24, Allison & McEwen 2000):**
  - `JD_TT = JD_UTC + (37 + 32,184)/86400` (TAI−UTC = 37 s, 2017'den beri)
  - `MSD = (JD_TT − 2405522,0028779)/1,0274912517`
  - `MTC = (24·MSD) mod 24`
  - `LMST = (MTC + λ_doğu/15) mod 24`
- Sol uzunluğu 88.775,244 s. Görev sol'ü senaryonun kendi sayacıdır; Curiosity sol'ü yalnız replay kaynağının etiketidir.
- Mesajlarda `measured` (ölçüm zamanı) ve `header.stamp` (yayın zamanı) ayrı tutulur.

### 4.4 QoS
| Sınıf | Ayar | Örnek |
|---|---|---|
| Sensör | best_effort, depth 5 | LiDAR, kamera |
| Durum | reliable, depth 10 | odom, crew state |
| Harita / plan | reliable, transient_local, depth 1 | margin field, plan, site manifest |
| Olay | reliable, depth 50 | alert, violation, evidence |

### 4.5 Adlandırma
- Topic'ler snake_case: `/redline/...`, `/<vehicle>/...`, `/crew/<crew_id>/...`.
- Parametreler YAML'da tutulur; sabit kodlanmaz.
- Unreal sınıfları önekleri: `A` (Actor), `U` (UObject), `F` (struct), `WBP_` (widget Blueprint), `BP_`.

---

## 5. `redline_msgs`

### 5.1 msg

```
# FieldTile.msg   (Unreal ve web'e giden sıkıştırılmış ızgara; son inceleme eki)
std_msgs/Header header
string site_id
string name                        # "margin_min_EV1", "cell_state", "weh_percent"
string unit
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32 scale                      # değer = byte·scale + offset
float32 offset
uint8 nodata_byte
uint8[] png                        # 8 veya 16 bit gri PNG
```

Bant genişliği kuralı:
- ROS içinde ızgaralar float32 olarak tutulur (`ScalarField`, `MarginField`).
- Unreal, web ve Open MCT'ye **yalnız `FieldTile` (PNG) ve `RedLine` poligonları** gider.
- 3×3 km'yi 2 m'de float JSON olarak yollamak tek mesajda ≈20 MB eder. rosbridge bunu taşıyamaz.

```
# Provenance.msg
uint8 ARCHIVE=0
uint8 DERIVED=1
uint8 SIMULATED=2
uint8 SCENARIO=3
uint8 status
string product_id
string source_url
string version
string sha256
builtin_interfaces/Time acquired
string note
```

```
# CellState.msg
uint32 ix
uint32 iy
uint8 UNOBSERVED=0
uint8 DETECTED=1
uint8 NOT_DETECTED_LIMITED=2
uint8 state
float32 elevation_m
float32 slope_deg
float32 slope_sigma_deg
float32 rock_density_per_m2        # N(>=D*) per m^2
float32 speed_factor                # 0..1, insan hız çarpanı
uint8 provenance_status            # Provenance.status
string evidence_id
```

```
# CellDelta.msg
std_msgs/Header header             # frame_id = map
string site_id
float32 resolution_m
geometry_msgs/Point origin         # ızgara (0,0) köşesi, map frame
CellState[] cells
```

```
# ScalarField.msg   (marj, doz, WEH gibi ızgara alanları)
std_msgs/Header header
string site_id
string name                        # "margin_min_EV1", "weh_percent", ...
string unit
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32[] data                     # satır-öncelikli, NaN = veri yok
float32[] sigma                    # boş olabilir
Provenance provenance
```

```
# MarginField.msg
std_msgs/Header header
string site_id
string crew_id
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32[] margin_min               # dakika; NaN = erişilemez
uint8 LIM_O2=0
uint8 LIM_CO2=1
uint8 LIM_WATER=2
uint8 LIM_BATTERY=3
uint8 LIM_DAYLIGHT=4
uint8 LIM_SHELTER=5
uint8[] limiting
float32 terminate_threshold_min
```

```
# RedLine.msg
std_msgs/Header header
string site_id
geometry_msgs/Polygon[] abort_regions      # margin >= 0 sınırı (kırmızı)
geometry_msgs/Polygon[] terminate_regions  # margin >= T_term sınırı (sarı)
string limiting_crew_id
uint8 limiting_consumable                  # MarginField.LIM_*
float32 margin_now_min
```

```
# Consumables.msg
std_msgs/Header header
string crew_id
float32 o2_kg
float32 water_kg
float32 co2_capacity_kg
float32 battery_wh
float32 o2_rate_kg_h
float32 water_rate_kg_h
float32 battery_rate_w
float32 metabolic_w
float32 theta                      # kişisel metabolik çarpan kestirimi
```

```
# CrewState.msg
std_msgs/Header header
string crew_id
geometry_msgs/PoseWithCovariance pose
Consumables consumables
float32 heart_rate_bpm
float32 suit_pressure_kpa
float32 ppco2_kpa
uint8 OK=0
uint8 SLOW=1
uint8 INCAPACITATED=2
uint8 status
```

```
# Station.msg
string station_id
string target_id
geometry_msgs/Point position
float32 service_min
string[] tasks                     # "LIBS", "APXS", "PHOTO", "SAMPLE", "DAN", ...
float32 science_value
float32 window_open_pet_min
float32 window_close_pet_min
```

```
# PlanLeg.msg
string from_id
string to_id
float32 duration_min
float32 duration_sigma_min
float32 o2_kg
float32 water_kg
float32 battery_wh
float32 return_margin_min
```

```
# EVAPlan.msg
std_msgs/Header header
string plan_id
uint32 version
string site_id
string[] crew_ids
Station[] stations
PlanLeg[] legs
nav_msgs/Path route
float32 total_duration_min
string decision_id
```

```
# Alert.msg
std_msgs/Header header
string alert_id
uint8 INFO=0
uint8 CAUTION=1
uint8 WARNING=2
uint8 EMERGENCY=3
uint8 severity
string code                         # SEP_ALERT, SUIT_LEAK, LINK_LOSS, MARGIN_LOW, RULE_VIOLATION, ROBOT_HELP
string text
string[] related_ids
```

```
# RuleViolation.msg
std_msgs/Header header
string rule_id
uint8 severity                      # Alert.*
float32 value
float32 threshold
string text
```

```
# DoseRate.msg
std_msgs/Header header
float32 dose_rate_b_ugy_h
float32 dose_rate_e_ugy_h
float32 background_b_ugy_h
float32 background_e_ugy_h
bool alert
string alert_detector               # "B" veya "E"
int32 source_sol
string source_file
builtin_interfaces/Time historical_utc
float32 sky_view_factor             # topografik ölçek (1 = açık gökyüzü)
```

```
# EnvState.msg
std_msgs/Header header
float32 sun_az_deg
float32 sun_el_deg
string lmst                          # "HH:MM:SS"
int32 mission_sol
float32 pressure_pa
float32 air_temp_k
float32 ground_temp_k
float32 tau
float32 air_density_kg_m3
float32 earth_light_time_s
Provenance provenance
```

```
# EvidenceRecord.msg
std_msgs/Header header
string evidence_id
builtin_interfaces/Time measured
builtin_interfaces/Time received
string source                        # sensör veya ürün adı
Provenance provenance
geometry_msgs/PoseWithCovariance pose
float32 resolution_m
float32 quality                       # 0..1
string[] input_ids
string payload_uri
string summary_json
```

```
# InstrumentProduct.msg
std_msgs/Header header
string product_id
string instrument                     # "APXS", "LIBS", "MSPEC", "DAN", "DOSIMETER", "WEATHER", "CAMERA"
string target_id
geometry_msgs/PoseWithCovariance instrument_pose
geometry_msgs/Point target_point
float32 integration_s
Provenance provenance
string payload_uri                    # data/products/... (JSON + PDS4 benzeri etiket)
string summary_json
```

```
# SampleRecord.msg
std_msgs/Header header
string sample_id
string target_id
geometry_msgs/Point origin_point       # numunenin alındığı yer
geometry_msgs/Point analysis_point     # analiz sırasında araç/kişi
string tool
string container_id
uint8 SELECTED=0
uint8 REACH_OK=1
uint8 PRE_POSITIONED=2
uint8 READY=3
uint8 ACQUIRING=4
uint8 ACQUIRED=5
uint8 STOWED=6
uint8 RECORDED=7
uint8 FAILED=8
uint8 state
string[] evidence_ids
```

```
# DecisionRecord.msg
std_msgs/Header header
string decision_id
string context
string[] evidence_ids
string[] candidates
string chosen
string[] rejected_reasons
string assumptions_json
string model_version
```

```
# CommandOwner.msg
std_msgs/Header header
string vehicle_id
uint8 NONE=0
uint8 MANUAL_UE=1
uint8 AUTONOMY=2
uint8 SAFETY_STOP=3
uint8 owner
builtin_interfaces/Time since
```

```
# MissionState.msg
std_msgs/Header header
string run_id
string scenario_id
uint8 BRIEFING=0
uint8 PRECURSOR=1
uint8 TRAVERSE=2
uint8 STATION_SCIENCE=3
uint8 RETURN=4
uint8 CONTINGENCY=5
uint8 DEBRIEF=6
uint8 phase
string active_plan_id
string[] active_task_ids
float32 pet_min
```

### 5.2 srv

```
# SetCommandOwner.srv
string vehicle_id
uint8 requested_owner        # CommandOwner.*
string reason
---
bool accepted
uint8 current_owner
string message
```

```
# PlanEva.srv
string site_id
string[] crew_ids
string[] candidate_target_ids
float32 max_duration_min
string objective               # "SAFE", "FAST", "SCIENCE"
---
bool success
string message
redline_msgs/EVAPlan plan
```

```
# QueryCell.srv
string site_id
geometry_msgs/Point point
---
bool found
redline_msgs/CellState cell
redline_msgs/EvidenceRecord[] evidence
```

```
# ScenarioControl.srv
uint8 LOAD=0
uint8 START=1
uint8 PAUSE=2
uint8 RESUME=3
uint8 SEEK=4
uint8 STOP=5
uint8 command
string scenario_id
float32 time_scale
float32 seek_s
---
bool success
string message
string run_id
```

```
# GetManifest.srv
string site_id
---
bool success
string manifest_json
```

### 5.3 action

Her action'da ortak sonuç kodu kullanılır: `uint8 SUCCEEDED=0, PARTIAL=1, CANCELED=2, FAILED=3, REJECTED=4`.

```
# SurveyArea.action
string request_id
string vehicle_id
geometry_msgs/Polygon area
string purpose
float32 deadline_s
---
uint8 outcome
string reason
string[] evidence_ids
float32 covered_fraction
float32 cost_s
float32 energy_wh
---
string phase
float32 covered_fraction
string[] new_evidence_ids
```

```
# InspectTarget.action
string request_id
string vehicle_id
string target_id
geometry_msgs/PoseWithCovariance target_estimate
string[] instruments
float32 deadline_s
---
uint8 outcome
string reason
string[] evidence_ids
string[] product_ids
---
string phase
```

```
# ContactScience.action        # kol ile temas bilimi (APXS benzeri)
string request_id
string target_id
geometry_msgs/Point target_point
string instrument
float32 integration_s
---
uint8 outcome
string reason
string product_id
float32 achieved_contact_angle_deg
---
string phase
float32 elapsed_s
```

```
# RemoteLibs.action            # uzaktan LIBS (ChemCam benzeri)
string request_id
string target_id                 # boş = otonom hedef seçimi
uint32 raster_rows
uint32 raster_cols
float32 raster_spacing_mrad
uint32 shots_per_point
---
uint8 outcome
string reason
string[] product_ids
string chosen_target_id
---
string phase
uint32 points_done
```

```
# MultispectralImage.action
string request_id
string target_id
string[] filters
---
uint8 outcome
string reason
string product_id
---
string phase
```

```
# NeutronSurvey.action         # DAN benzeri
string request_id
string vehicle_id
uint8 PASSIVE=0
uint8 ACTIVE=1
uint8 mode
geometry_msgs/Polygon area
uint32 max_points
float32 dwell_s
---
uint8 outcome
string reason
string[] product_ids
string field_name                 # ScalarField adı
---
uint32 points_done
float32 max_posterior_sigma
```

```
# Drill.action
string request_id
string target_id
float32 depth_mm
uint8 ROTARY=0
uint8 PERCUSSIVE=1
uint8 mode
---
uint8 outcome
string reason
string sample_id
string fault_code                  # "", "STALL", "FEED_LIMIT", "OVER_TORQUE", "BIT_STUCK"
float32 achieved_depth_mm
---
string phase
float32 depth_mm
float32 feed_force_n
float32 torque_nm
```

```
# CacheSample.action
string request_id
string sample_id
string container_id
---
uint8 outcome
string reason
---
string phase
```

```
# DeployStation.action
string request_id
string deployer_id                 # EV1/EV2 veya rover_1
uint8 WEATHER=0
uint8 DOSIMETER=1
uint8 station_type
geometry_msgs/Point position
---
uint8 outcome
string reason
string station_id
---
string phase
```

```
# ReturnToShelter.action
string request_id
string[] crew_ids
string shelter_id                  # "habitat" veya "pr_1"
bool rover_meets_crew
---
uint8 outcome
string reason
float32 actual_time_min
---
float32 eta_min
float32 distance_m
```

```
# ExecuteScout.action          # drone uçuşu
string request_id
string vehicle_id
geometry_msgs/Polygon corridor
float32 altitude_m
float32 max_flight_s
---
uint8 outcome
string reason
string[] evidence_ids
float32 flight_s
float32 battery_used_wh
---
string phase                         # PREFLIGHT, TAKEOFF, TRANSIT, SURVEY, RETURN, LANDING
float32 battery_wh
```

---

## 6. Veri hattı: `redline_data`

### 6.1 Yapılandırma

`config/sites.yaml`:

```yaml
crs_default:
  proj: eqc
  sphere_radius_m: 3396190      # ürün etiketinden yeniden doğrulanır
  lon_0: 0
  lat_ts: 0
sites:
  BXW:
    name: "Boxwork-West, Mount Sharp"
    center_lat: -4.805           # öneri; QA ile doğrula
    center_lon_east: 137.370
    size_m: [3000, 3000]
    grid_m: 1.0                  # kaynak pencere
    plan_grid_m: 4.0             # walkback, kırmızı çizgi, ufuk küpü (canlı)
    engine_grid_m: 4.0           # Unreal landscape ve Gazebo uzak arazi
    ops_box:                     # robotların fizikte sürdüğü yüksek çözünürlüklü kutu
      size_m: [1000, 1000]
      center_offset_m: [0, 0]    # EVA rotasına göre T1'de ayarla
      grid_m: 1.0
    role: forward_eva
    validation_campaign_sols: [4534, 4805]    # MMGIS [D]
    hirise_dtms: [DTEEC_019698_1750_019988_1750_U01, DTEEC_009149_1750_009294_1750_U01]   # [K]
  YKB:
    name: "Yellowknife Bay"
    center_lat: -4.5895          # John Klein [K]
    center_lon_east: 137.4491
    size_m: [2000, 2000]
    grid_m: 1.0
    plan_grid_m: 4.0
    engine_grid_m: 4.0
    role: calibration
    hirise_dtms: [DTEEC_010573_1755_010639_1755_U01, DTEEC_018854_1755_018920_1755_U01, DTEEC_023957_1755_024023_1755_U01]   # ilki [D], diğerleri [K]
```

`config/products.yaml` (ilk liste):

| key | URL | statü |
|---|---|---|
| `gale_dem_v3` | `https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif` [D 200] | DERIVED |
| `gale_lrgb` | `https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif` [K] | ARCHIVE |
| `hirise_dtm_*` | STAC `https://stac.astrogeology.usgs.gov/api`, collection `mro_hirise_socet_dtms` [D] | DERIVED |
| `ctx_dtm_*` | STAC collection `mro_ctx_controlled_usgs_dtms` [K] | DERIVED |
| `themis_ti` | USGS Astropedia THEMIS TI 100 m [K] | DERIVED |
| `sim3292` | USGS SIM 3292 ArcGIS feature service [K] | DERIVED |
| `places_interp` | `https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv` [D 200] | ARCHIVE |
| `mmgis_msl_waypoints` | `https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json` [D] | ARCHIVE (operasyonel) |
| `apxs_supp` | `https://pds-geosciences.wustl.edu/msl/urn-nasa-pds-msl_apxs_supplement_sols_0_2301/data/ds01_2020je006536rr.csv` [K] | ARCHIVE |
| `chemin_jk` | `https://pds-geosciences.wustl.edu/msl/msl-m-chemin-4-rdr-v1/mslcmn_1xxx/data/rdr5/cma_414856883min01960060000ch12240p1.csv` [K] | ARCHIVE |
| `rad_rdr` | `https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/` [D] | ARCHIVE |
| `rems` | PDS Atmospheres `MSL-M-REMS-5-MODRDR` [?]; yedek mars.nasa.gov REMS JSON özeti [K] | ARCHIVE |
| `chemcam`, `dan` | PDS Geosciences MSL ChemCam / DAN RDR (Release 42, sol 4843'e kadar [K]); tekil yol [?] | ARCHIVE |
| `spice_lsk` | `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls` [D 200] | — |
| `spice_pck` | `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc` [D 200] | — |
| `spice_spk` | `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp` [D 200] | — |

Kapsam kontrolü (başkan hesabı): DEM v3 kapsamı E 8.127.994–8.160.974, N −302.222…−244.782 [K]. LRGB kapsamı E 8.140.000–8.149.000, N −289.000…−270.000 [K]. BXW (E ≈ 8.142.5 km, N ≈ −284.8 km) ve YKB (E ≈ 8.147.3 km, N ≈ −272.0 km) ikisinin içinde. BXW'nin batı sınırı LRGB'nin batı kenarına (lon ≈ 137,327°) yakın; QA'da nodata oranını kontrol et.

### 6.2 CLI adımları

`redline-data <adım> --site BXW` ile çalışır. Her adım idempotenttir; çıktısını hash'iyle `data/stac/` altına yazar.

| Adım | Fonksiyon | Davranış | Bitti ölçütü |
|---|---|---|---|
| `catalog` | `catalog.build(products.yaml)` | HEAD isteği, boyut, ETag; `DATA_SOURCES.md` taslağı | tüm URL'ler 200 veya açık hata |
| `fetch` | `fetch.window(product, site)` | `rasterio.open('/vsicurl/<url>')`, `from_bounds` ile pencere; tam dosya indirilmez | `data/raw/<site>/<key>.tif` |
| `crs` | `crs.check(path, expected)` | WKT'den küre yarıçapı, lon_0, lat_ts, birim, nodata okunur; beklenenle farklıysa **durur** | `crs_report.json` |
| `enu` | `enu.to_local(path, site)` | §4.2 formülü; cos φ0 düzeltmesi; yeniden örnekleme bilinear (DEM), nearest (sınıf) | `derived/<site>/dem_enu.tif` |
| `derive` | `derive.slope(dem, baselines=[2,5])`, `roughness`, `sigma` | çok tabanlı eğim; DTM farkından σ (önce eşkayıt: dikey ofset medyanı çıkarılır) | `slope_2m.tif`, `slope_5m.tif`, `slope_sigma.tif` |
| `horizon` | `horizon.cube(dem_plan_grid, n_az=72, r_max_m=3000)` | her hücre ve azimut için ufuk yüksekliği; numba ile ışın yürütme. **4 m ızgarada** yapılır: 3 km'de 1 m ızgara 9M hücre × 72 = 1,3 GB; 4 m'de ≈80 MB | `horizon_cube.npy` (float16) |
| `skyview` | `skyview.f_alpha(cube, alpha=1.18)` | §7.3 formülü | `sky_view.tif` |
| `viewshed` | `viewshed.from_points(dem, observers)` | habitat, PR istasyonları, anten yüksekliği 3 m, EV 2 m | `los_<id>.tif` |
| `rocks` | `rocks.detect(ortho, sun_inc, sun_az)` + `rocks.fit_golombek(...)` | gölge segmentasyonu → çap; 50 m hücrelerde k kestirimi | `rock_k.tif`, `rocks_detected.geojson` |
| `scenario` | `scenario.world(site, seed)` | Golombek dağılımından çözünürlük altı kayalar (SCENARIO); dekor/navigasyon ayrımı | `scenario_rocks_<seed>.json` |
| `engines` | `engines.export(site)` | Gazebo: OBJ/DAE mesh (2 m), collision; Unreal: 16 bit PNG heightmap + Z ölçeği + ortho doku | `data/engines/<site>/` |
| `env` | `env.rad(sols)`, `env.rems(sols)`, `env.spice(site, utc_range)` | RAD dosyası ayrıştırma, REMS özet, güneş az/el tablosu, ışık süresi | `data/env/*.parquet` |
| `traverse` | `traverse.mmgis()`, `traverse.places()` | Curiosity rotası ENU'da; PLACES tilt | `traverse_<site>.geojson` |
| `stac` | `stac.write(site)` | Collection + Item'lar, `proj:wkt2`, statü, hash | `data/stac/<site>/collection.json` |
| `qa` | `qa.report(site)` | 3 nokta yükseklik testi, nodata oranı, eğim histogramı, PNG önizlemeler | `qa_<site>.html` |

### 6.3 RAD ayrıştırıcı (biçim [D])
- Dosya bölümleri `[OBSERVATION: NN]`, `[DOSIMETRY_TOTAL_DOSE_B: NN]`, `[DOSIMETRY_TOTAL_DOSE_E: NN]`.
- Gözlem bölümünde `START_OBS_UTC="YYYY-DOY hh:mm:ss"` var. Doz bölümlerinde başlıktan sonraki ilk boş olmayan satır tek sayıdır.
- **Eşleme `NN` indeksiyle yapılır, sıra numarasıyla değil.** Sol 4190 dosyasında 186 gözlem bölümü ama 93 doz bloğu var: doz blokları yalnız çift indeksli gözlemlerde bulunur [D]. Sol 242'de 18 / 18.
- Kadans değişkendir: olay öncesi ~17 dk, olay sırasında ~9 dk (sol 4190) [D]. Değer basamaklı tutulur; enterpolasyon yapılmaz.
- Birim µGy/h olarak yorumlanır: Hassler+2014 ile tutarlı [K]. SIS'te birim tutarsız yazıyor; `VERIFICATION_LOG`'a not edilir.
- Doğrulama testi (sabit beklenen değerler [D]):
  - sol 241 B ortalaması 9,163 (n=24)
  - sol 242 B maksimum 12,13153; E maksimum 10,87475
  - sol 4190 E maksimum 351,42427 (gözlem 88, 2024-141 06:15:19 UTC); 93 doz bloğu, 186 gözlem bölümü
  - sol 4190 E serisi: gözlem 76 → 5,72 (05:04:45), 78 → 9,97 (05:21:50), 80 → 85,38 (05:38:56), 82 → 214,04, 84 → 316,37, 86 → 343,28, 88 → 351,42
  - %25 alarmı (arka plan ≈ 5,6) ilk kez gözlem 78'de, 05:21:50 UTC'de tetiklenir. Tepeye kadar ≈ 53 dk.

### 6.4 Güneş ve ışık süresi (SpiceyPy)
```python
sp.furnsh([lsk, pck, spk])
et = sp.str2et(utc)
sun, _ = sp.spkpos("SUN", et, "IAU_MARS", "LT+S", "MARS")
site = sp.latrec(R, lon_rad, lat_rad)                 # küre; ürün yarıçapıyla
up = site/|site|; east = unit(cross([0,0,1], up)); north = cross(up, east)
v = sun - site
el = asin(dot(unit(v), up)); az = atan2(dot(v, east), dot(v, north))
earth, lt = sp.spkpos("EARTH", et, "J2000", "NONE", "MARS")   # lt saniye
```

---

## 7. `redline_core` (saf Python kütüphanesi)

Bağımlılıklar: numpy, scipy, numba, networkx (yalnız testlerde), ortools (isteğe bağlı), pyyaml. Bütün fonksiyonlar birim kontrollüdür: girdiler SI, dakika yalnız çıktı katmanında.

### 7.1 `grid.py`
- `Grid(origin_xy, resolution_m, width, height, layers: dict[str, np.ndarray])`
- `neighbors16()`: 16 komşuluk ofsetleri (±1,±2 kombinasyonları; yönlü).
- `edge_grade(z, i, j, di, dj) = (z[j]−z[i]) / d`

### 7.2 `cost_human.py` — insan yürüyüş ve metabolik maliyeti
Bütün parametreler `config/suit.yaml` ve `crew.yaml`'dan gelir ve SCENARIO etiketlidir.
- **Hız (Tobler × Froude):** `v(S) = f_froude · 6·exp(−3,5·|S + 0,05|)` km/h, `S = tan(eğim)` yönlü, `f_froude = sqrt(g_M/g_E) ≈ 0,615`. Üst sınır `v_wr = sqrt(0,5·g_M·L_leg)`; L_leg = 0,9 m için ≈ 1,29 m/s.
- **Metabolik güç (Pandolf 1977 yapısı, Mars ölçeklemesi, v0.3 [K]):**
  `M = θ·[ s·(1,5·W + 2,0·(W+L)·(L/W)²) + η·(W+L)·( s·1,5·V² + 0,35·(g_M/g_E)·V·G⁺ + k_d·0,35·(g_M/g_E)·V·G⁻ ) ] + ΔM_suit`
  - W vücut kütlesi (kg), L taşınan yük + giysi kütlesi (kg), V hız (m/s), G eğim (%).
  - `G⁺ = max(G,0)`, `G⁻ = max(−G,0)`; `s = (g_M/g_E)^β`. Varsayılanlar: β = 0,7, k_d = 0,3.
  - η arazi çarpanı: sert 1,0, toprak 1,1, gevşek kum 2,1 [K].
  - `ΔM_suit`: EWT 3/8 g ağırlık dışı maliyeti (14,9–21,6 ml/kg/dk [K]) → W ile `335·VO₂[L/dk]` dönüşümü; varsayılan orta değer 18,8.
- **Sarf dönüşümleri [K]:**
  - O₂ g/h = 0,256·M[W]
  - CO₂ = 0,85·VO₂
  - Su kg/h = (1−0,2)·M·3600 / 2,45e6 (buharlaştırmalı soğutma; belirsiz, geniş σ)
  - Batarya W = P0 + k·M (varsayılan P0 = 60 W, k = 0,05)
- **Kenar sonucu:** `EdgeCost(t_s, o2_kg, water_kg, battery_wh, sigma_t_s)`. σ_t eğim σ'sının sonlu farkla yayılımından ve bilinmeyen hücre cezasından gelir.
- **Bilinmeyen hücre:** `state == UNOBSERVED` ise `speed_factor = 0,7` ve `sigma_t ×= 1,5` (parametre). `NOT_DETECTED_LIMITED` ise `0,85`.
- **Yasaklar:** `|μ_s| + z·σ_s > s_max` (s_max 25°, z = 1,645) veya sırt duvarı (yerel rölyef > 0,8 m ve eğim > 30°) → kenar yok.
- **Kaya riski:** `λ·N(≥D*)·w·L_e` (w = 0,6 m, D* = 0,5 m) maliyete eklenir.

### 7.3 `radiation.py`
- `f_alpha(h_cube, alpha) = mean_k [1 − sin^(α+1)(max(h_k,0))]`
- `dose_rate_site(d_open, F, f_a=0.2) = d_open·((1−f_a)·F + f_a)`
- Gale GCR tabanı 0,21 mGy/gün [K]. Bu katman ALARA için yardımcıdır, ana güvenlik etkeni değildir.

### 7.4 `rocks.py`
- `F_k(D) = k·exp(−q·D)`, `q = 1,79 + 0,152/k`
- `N_ge(D, k) = (4·k·q/π)·[exp(−q·D)/D − q·E1(q·D)]`; `scipy.special.exp1` kullanılır.
- `fit_k(detected_diameters, area_m2, D_min)`: en çok olabilirlik (k ∈ [0,005, 0,3]).
- `sample_rocks(k, area, D_range, seed)`: çözünürlük altı kayalar (SCENARIO).

### 7.5 `walkback.py` — dönüş alanı
- Girdi: grid, kenar maliyet fonksiyonu, sığınak kümesi H (habitat ve o andaki PR konumu).
- **Ters graf üzerinde çok kaynaklı Dijkstra:** her hücre x için `W(x) = min yol maliyeti x → H`. Kenarlar yönlüdür; ters grafta `u←v` kenarının maliyeti `v→u` yürüyüşüdür.
- Skaler anahtar = süre. Aynı yol boyunca O₂, su, batarya ve σ² toplanır (etiket taşıma).
- **Risk düzeltmesi:** `W_ε = μ_W + z_ε·sqrt(Σσ_e² + (σ_θ·μ_W)²)`; σ_θ = 0,2, z_ε = 1,645.
- Performans hedefi: 3×3 km, **4 m** ızgara (562 bin düğüm, ≈9M kenar) ≤ 1 s (numba heap Dijkstra). 2 m yalnız çevrimdışı doğrulamada kullanılır.
- Çıktı: `WalkbackField(time_s, o2_kg, water_kg, battery_wh, sigma_s, next_hop)`.
- **Yeniden hesaplama politikası (son inceleme):**
  - W alanları zamanla değişmez. Yalnız **harita deltası veya sığınak konumu değişince** yeniden hesaplanır.
  - Her tick'te yalnız `m_j = R_j(t) − R_rez − W_j` dizi çıkarması yapılır: milisaniyeler.
  - O₂, su ve batarya alanları θ ile doğrusal ölçeklenir: `W_o2(θ) = θ·W_o2(1)`. Kişisel θ değişimi yeniden Dijkstra gerektirmez.
  - EV1 ve EV2 aynı süre alanını paylaşır; sarf alanları kişisel parametrelerle ölçeklenir.
  - PR hareket ederken sığınak kümesi değişir. O zaman en yakın 3 PR istasyonu için önceden hesaplanmış alanların minimumu kullanılır (§7.7).

### 7.6 `redline.py` — pay ve çizgi
- Her sarf j için `m_j(t, x) = R_j(t) − R_j^rez − W_j,ε(x)`.
- Dakika payı: `margin_min(x) = min_j m_j(x) / ṙ_j`; `limiting(x) = argmin_j`.
- Gün ışığı: `m_daylight = (t_sunset − T_dusk) − t_now − W_time`.
- SEP modunda ek kısıt: `T_sh(x) ≤ T_SEP,max` sağlanmazsa `margin_min = −∞`, `limiting = SHELTER`.
- **Kırmızı (abort):** `margin_min ≥ 0` bölgesinin sınırı. **Sarı (terminate):** `margin_min ≥ T_term` (varsayılan 30 dk) sınırı.
- Kontur: `skimage.measure.find_contours` → polygon (map frame).
- **İki astronot:** çizgi her EV için ayrı hesaplanır; gösterilen çizgi `min(EV1, EV2)` olur.

### 7.7 `shelter.py` — sığınağa süre ve rover yerleşimi
- `T_sh(x) = min( W_time_to_PR(x), T_rover(PR→x) + τ_al )`; τ_al = 5 dk (varsayım).
- **Darboğaz DP (v0.3 M8):**
  - `B_1(c) = κ(1,c)`
  - `B_k(c) = max(κ(k,c), min_{c': T_R(c',c) ≤ Δt_k} B_{k−1}(c'))`
  - `κ(k,c) = max_{x ∈ X_k} R_c(x)`; görüş hattı oranı < ρ ise ∞
  - Geriye izleme ile istasyon dizisi bulunur. Eşitlikte rover mesafesi en aza indirilir.
- Karmaşıklık O(K·|C|²). K ≤ 40, |C| ≤ 400.

### 7.8 `pet.py` — zaman çizelgesi
- `build_timeline(route, stations, cost_fn) -> list[PlanLeg]`; her bacakta süre ± σ ve sarf.
- `return_margin_min` her istasyonda `R − C(s) − W_ε(x(s)) − R_rez`.
- Plan geçerliliği: her s için `R0 − C_ε(s) − W_ε(x(s)) ≥ R_rez`.
- **Cuff checklist üretimi:** her istasyon için "varış PET, iş listesi, dönüş kararı PET, sınırlayan sarf".

### 7.9 `orienteering.py` — durak seçimi
- MVP: açgözlü ekleme (değer/ek süre oranı) + 2-opt + yer değiştirme yerel araması. Her adayda walkback ve pencere kontrolü yapılır.
- İsteğe bağlı: OR-Tools CP-SAT ile kesin model (v0.3 M7). Sezgiselin optimallik açığı raporlanır.
- Üç Pareto rotası: `FAST` (süre), `SAFE` (min margin maks), `SCIENCE` (değer maks).

### 7.10 `science_value.py` — Bayesçi bilim değeri
- Hipotezler ve önseller `config/science_<site>.yaml` içinde tanımlıdır. BXW örneği: H1 desen batıda da var / H2 yok / H3 karışık.
- Gözlem modeli: `p(o | H, features(s))` tablosu.
- `EIG(s) = Σ_H Σ_o P(H)·p(o|H)·log(p(o|H)/p(o))`; ölçüm gelince posterior güncellenir.

### 7.11 `voi.py` — robot gözlem değeri
- Aday hücreler: mevcut rota koridoru ±50 m içinde `UNOBSERVED` veya `NOT_DETECTED_LIMITED` olanlar.
- Her aday c için iki hipotez:
  - açık (olasılık `p = exp(−N·w·L)`)
  - engelli (1−p)
- Her hipotez için yerel yeniden plan yapılır ve plan margin'i hesaplanır.
- `VOI(c) = E[max(margin_plan | gözlem)] − margin_plan_şimdi`; `score = VOI / robot_cost_s(c)`.
- En iyi K aday `SurveyArea`/`InspectTarget` önerisi olarak yayımlanır.
- Hesap bütçesi: aday başına ≤ 50 ms; yerel pencere 200×200 m.

### 7.12 `sep.py`
- Arka plan: son 6 saatlik gözlemlerin medyanı (parametre).
- Alarm: `dose_rate ≥ 1,25 × background`. Dedektör seçimi parametredir (`B` varsayılan); her iki dedektörün durumu ayrı raporlanır.
- Alarm anında uçuş kuralı: `T_sh(x_crew) ≤ T_SEP,max` (20 dk). İhlalde `EMERGENCY` alert ve otomatik `ReturnToShelter` önerisi üretilir.

### 7.13 `localization_fix.py` (isteğe bağlı, M11)
- Ufuk profili eşleştirme: görüntüden gökyüzü maskesi (renk eşiği) → azimut başına ufuk açısı → aday konumlarda `h_cube` ile normalize çapraz korelasyon → olabilirlik haritası.
- Güneş pusulası: görüntüdeki güneş azimutu ile SPICE azimutu farkından yön düzeltmesi.

### 7.14 Altın testler (zorunlu)
- Düz düzlemde `W = mesafe / v(0)`.
- Silindirik çukur (her yönde h): `F = 1 − sin^(α+1) h`.
- Eğimli düzlemde yokuş yukarı ve aşağı walkback farklı; asimetri işaretinin doğruluğu.
- Golombek `N_ge` için sayısal integral ile kapalı form farkı < %1.
- Küçük ızgarada (10×10) Dijkstra = networkx kaba kuvvet.
- Darboğaz DP = kaba kuvvet (K=4, |C|=6).
- Hypothesis ile `W ≥ 0` ve üçgen eşitsizliği.
- eqc→ENU: 1° boylam farkı ↔ `R·cos φ0·π/180` m.

---

## 8. ROS düğümleri

Her düğüm için: paket, dil, parametre dosyası, abonelikler, yayınlar, servis/aksiyon ve hata davranışı. Bütün düğümler `use_sim_time` ile çalışır ve `diagnostic_updater` ile durum yayımlar.

### 8.1 `redline_env`
| Düğüm | Giriş | Çıkış | Davranış |
|---|---|---|---|
| `scenario_player` | `config/scenarios/*.yaml`, srv `ScenarioControl` | `/redline/scenario/event` (Alert), `/redline/mission/state` güncellemesi | olayları zamanında enjekte eder; tohum ve run_id üretir |
| `rad_replay` | `data/env/rad_*.parquet`, `/redline/scenario/*` | `/env/dose_rate` (DoseRate, 1 Hz yayın, kaynak kadansında değer değişir) | tarihsel UTC'ye göre doğrusal enterpolasyon yok; basamaklı değer ve blok zamanı |
| `rems_replay` | REMS parquet | `/env/weather` | basınç, sıcaklık, tau |
| `env_server` | SPICE tablosu, weather | `/env/state` (EnvState, 1 Hz) | güneş az/el, LMST, ρ = P/(188,9·T), ışık süresi |

### 8.2 `redline_crew`
| Düğüm | Giriş | Çıkış | Davranış |
|---|---|---|---|
| `ev_sim` (EV2; EV1 Unreal'dan gelirse yalnız fizyoloji) | plan, olaylar, `/crew/<id>/pose` | `/crew/<id>/state` (CrewState, 5 Hz) | kalp hızı ve sarf tüketimi; giysi kaçağı olayında O₂ tüketimi × k_leak |
| `consumables_estimator` | crew state | `/crew/<id>/consumables` | HR→VO₂ doğrusal kalibrasyon; θ için Kalman (rastgele yürüyüş) |

### 8.3 `redline_mission`
| Düğüm | Görev |
|---|---|
| `cell_store` | yörünge katmanlarını yükler; `EvidenceRecord` → hücre durumu güncellemesi; `/redline/cells/delta` (olay) ve `QueryCell` servisi |
| `command_authority` | araç başına tek komut sahibi; `SetCommandOwner`; `/<vehicle>/cmd_vel_in_*` girişlerini seçip `/<vehicle>/cmd_vel_gated` çıkışına verir; 0,5 s tazelik; kopmada sıfır komut |
| `mission_manager` | MissionState makinesi (§8.7); action istemcisi; `DecisionRecord` yazar |
| `voi_tasker` | `voi.py`; `/redline/robot_tasks/proposed` |

### 8.4 `redline_planner`
| Düğüm | Görev |
|---|---|
| `walkback_field` | 1 Hz veya olayda: her EV için `MarginField`, `RedLine` yayımı; hücre deltası veya sarf değişiminde yeniden hesap |
| `planner_server` | `PlanEva` servisi: orienteering + PET + üç Pareto rotası |
| `rover_placer` | plan değişince PR istasyon planı → Nav2 hedefleri; `/pr_1/station_plan` |
| `science_optimizer` | posterior güncellemesi, istasyon değerleri |

### 8.5 `redline_safety`
- `rule_monitor` (Python MVP): `config/rules.yaml`'daki kuralları 10 Hz tick ile değerlendirir ve `/safety/violations` yayımlar.
- İsteğe bağlı: aynı kurallar FRET → Ogma → Copilot ile üretilir; `safety_aggregator` iki kaynağı birleştirir.

### 8.6 `redline_comm`
- `link_manager`: EV↔PR↔habitat görüş hattı (`los_*.tif` + dinamik konum). Kopmada seçili topic'leri düşürür veya geciktirir (uygulama seviyesi emülasyon). `/comm/link/state` yayımlar.

### 8.7 Görev durum makinesi
```
BRIEFING → PRECURSOR → TRAVERSE ⇄ STATION_SCIENCE → RETURN → DEBRIEF
                 ↘ CONTINGENCY (SEP_ALERT | SUIT_LEAK | LINK_LOSS | INCAPACITATED) ↗ RETURN
```
- Her geçiş bir `DecisionRecord` yazar.
- CONTINGENCY'de: plan dondurulur, `ReturnToShelter` başlatılır, PR'ye karşılama hedefi verilir.

---

## 9. Bilim görevleri (ROS)

### 9.1 Enstrüman çatısı (`redline_science`)
- Her enstrüman bir **lifecycle node**'dur (rclpy lifecycle): `unconfigured → inactive (STANDBY) → active`. Güç tüketimi `/power/<instrument>` (W) olarak yayımlanır.
- Ortak taban sınıf `InstrumentBase`: hazır olma ön koşulları (pozisyon, temas, güneş, güç), zamanlama, ürün yazımı ve hata kodları.
- **Ürün yazımı:** `data/products/<run_id>/<product_id>.json` + `<product_id>.xml` (PDS4 benzeri etiket: instrument, target, zaman, poz, entegrasyon, provenance, girdiler). Ardından `InstrumentProduct` ve `EvidenceRecord` yayımlanır.
- **Hedef kaydı:** `config/targets_<site>.yaml`. Gerçek hedeflerde (YKB: John Klein, Cumberland) gerçek NASA değerleri ARCHIVE olarak tutulur. Senaryo hedeflerinde birim önselinden (BXW: Htu, boxwork-doğu ChemCam/APXS istatistikleri) çekilir ve SCENARIO olarak tutulur.
- **Ölçüm modeli kuralı:** simüle ölçüm = hedef "gerçeği" + gürültü modeli. Gürültü, gerçek ürünlerin hata sütunlarından kalibre edilir. Çıktı her zaman SIMULATED etiketlidir; kalibrasyon kaynağı provenance'ta yazılır.

### 9.2 Görevler

| # | Görev | Action | ROS/Gazebo uygulaması | Gerçek veri bağı | Haritaya yazdığı katman |
|---|---|---|---|---|---|
| B1 | **Kol ile temas bilimi** (APXS benzeri) | `ContactScience` | derinlik kamerası → nokta bulutu → yüzey normali (PCL/Open3D); MoveIt 2 erişim ve çarpışma kontrolü; Gazebo contact sensörü; temas açısı < 15°, mesafe < 2 cm koşulu | APXS supplement oksit değerleri ve `_error` sütunları; σ_i(t) = σ_ref,i·sqrt(t_ref/t) (Poisson sayım) | istasyon noktası: oksit kartı |
| B2 | **Uzaktan LIBS + otonom hedef seçimi** (ChemCam + AEGIS benzeri) | `RemoteLibs` | direk pan-tilt eklemleri (ros2_control); Navcam benzeri kamerada OpenCV ile kaya segmentasyonu (kenar/kontur, boyut, parlaklık ölçütleri) → hedef seçimi → raster | ChemCam RDR (BXW-doğu) ile birim önseli ve atış gürültüsü; ilk atışlarda toz katmanı etkisi [?]; menzil ≤ 7 m [?] | nokta kompozisyonları |
| B3 | **Multispektral görüntüleme** | `MultispectralImage` | kamera pozundan görüş ayak izi; filtre başına sentetik görüntü = senaryo mineral bolluğu × spektral kütüphane × filtre yanıtı | USGS spektral kütüphanesi splib07 [?], Mastcam filtre tanımları [?]; CRISM önseliyle karşılaştırma | spektral indeks ızgarası (SIMULATED) |
| B4 | **Nötron taraması ve adaptif örnekleme** (DAN benzeri) | `NeutronSurvey` | rover durarak ölçer; Gaussian process posterior (sklearn veya kendi uygulaması); sonraki nokta = max σ × erişim maliyeti | DAN RDR (BXW-doğu, sol 4843'e kadar [K]) önsel ve gürültü kalibrasyonu | `weh_percent` ScalarField + σ → güven katmanına girer |
| B5 | **Sondaj ve FDIR** | `Drill` | Gazebo'da prismatic besleme + revolute uç; force-torque sensörü; kaya sertliği parametresiyle direnç modeli; stall: tork > τ_max veya ilerleme < v_min (Δt) → geri çekil, besleme kuvvetini azalt, perküsif moda geç | Curiosity sondaj besleme arızası (Aralık 2016) ve sonrası besleme-uzatmalı sondaj tekniği tarihî referans [?]; telemetri değerleri SCENARIO | sondaj noktası + SampleRecord |
| B6 | **Numune zinciri ve önbellek** | `CacheSample` | SampleRecord durum makinesi (§5.1); komut kimliği ile tekrar koruması; kap kimliği | Mars 2020 Sample Dossier kayıt yapısı referans [K] | numune kökeni ≠ analiz noktası (iki simge) |
| B7 | **Çevre istasyonu ağı** | `DeployStation` | astronot veya rover istasyon bırakır; her istasyon `weather` ve `dosimeter` yayımlar; zaman eşlemesi; SEP nowcast çok istasyonlu birleşim | REMS replay + yerel bozulma; RAD replay × istasyon sky-view F_α | istasyon noktaları; doz ve sıcaklık zaman serisi (Open MCT) |
| B8 | **Bilim etkinliği zamanlayıcı** | (`science_scheduler` düğümü) | görevler: süre, güç (W), enerji, sıcaklık penceresi, güneş açısı, iletişim geçişi, önkoşul; CP-SAT veya açgözlü; BehaviorTree.CPP ile yürütme | güneş SPICE; röle geçişleri senaryo; enerji bütçesi (rover gücü parametre [?]) | PET zaman çizelgesine bilim blokları |
| B9 | **Veri önceliklendirme ve downlink** | (`downlink_planner` düğümü) | ürün boyutu (MB), değer, öncelik sınıfı (güvenlik > özet telemetri > bilim > notlar); geçiş kapasitesine göre sırt çantası (knapsack) | röle günlük hacimleri TGO ~2.228, MRO ~851, Odyssey ~107 Mb/gün (2026 başı [K]) | Dünya konsolunda "inmiş / kuyrukta" |
| B10 | **Astronot saha bilimi** | (Unreal etkileşimi → `/crew/<id>/science_note`) | fotoğraf, not, hedef işareti; el tipi XRF benzeri ölçüm `ContactScience` ile aynı model; bilim arka odası gecikmeli yanıt | aynı hedef kaydı | istasyon notları |

Bilim görevleri ile güven katmanının bağı:
- B4 (WEH σ) ve B2/B1 (kompozisyon) `science_value.py` posterior'unu günceller ve istasyon değerlerini değiştirir.
- B1/B2 ölçümleri ve B5 sondaj süresi PET'i değiştirir, PET de kırmızı çizgiyi.
- Böylece bilim, robot ve güvenlik aynı haritada birleşir.

### 9.3 Gazebo tarafı gereksinimleri
- **Sensörler:** `gpu_lidar`, `camera`, `depth_camera`, `imu`, `force_torque` (sondaj), `contact` (temas bilimi), `altimeter` + `air_pressure` (drone). Hepsi gz-sim sistemleri olarak eklenir [?: Harmonic sistem adlarını kontrol et].
- **Kol:** 5 DOF basit kol (rover ön tareti); MoveIt 2 yapılandırması `redline_description/moveit/`.
- **Direk:** 2 DOF pan-tilt; kamera ve LIBS "lazer" frame'i.

---

## 10. Gazebo dünyası

- `redline_gazebo/worlds/<site>.sdf`:
  - `<gravity>0 0 -3.721</gravity>`
  - `<physics>` adımı 1 ms (veya 2 ms), real-time factor 1
  - **arazi iki katmanlı (son inceleme):**
    - `ops_box` 1 km × 1 km, 1 m ızgara, 250 m'lik karolara bölünmüş mesh'ler (her karo ≈125 bin üçgen; görsel ve collision aynı)
    - çevresi 4 m düşük çözünürlüklü tek mesh
    - 3 km'yi 2 m'de tek mesh yapmak ≈4,5M üçgen eder; collision ve GPU LiDAR'ı yavaşlatır
  - Gazebo WSL'de başsız ve EGL ile çalışır: `gz sim -s -r --headless-rendering <world>` [?]. Sensör render'ı için GPU erişimini T3'ün ilk saatinde doğrula.
  - senaryo kayaları `scenario_rocks_<seed>.json`'dan launch sırasında spawn edilir
- Gerekli sistemler: `Physics`, `SceneBroadcaster`, `UserCommands`, `Sensors` (render engine ogre2), `Imu`, `ForceTorque`, `Contact`, `Altimeter`, `AirPressure`.
- **Rover:** `space-ros/demos/curiosity_rover/curiosity_description` [D] Jazzy + Harmonic'e taşınır (`gz_ros2_control`, 6 teker, direksiyon). Taşıma 4 saatte bitmezse sadeleştirilmiş 6 tekerli SDF + `DiffDrive` sistemiyle devam edilir ve görsel olarak Curiosity mesh'i kullanılır.
- **Drone:** 4 rotorlu gövde + `MulticopterMotorModel` ×4 + `MulticopterVelocityControl` [?]. `motorConstant` Mars ρ ile ölçeklenir: `k_mars = k_earth·ρ_mars/1,225`; motor hızı ve kütle buna göre ayarlanır (SCENARIO).
- **PR (basınçlı rover):** basit kutu collision + diff-drive; Nav2 ile sürülür; görseli Unreal'da NASA SEV modeli.
- **Astronot proxy'leri:** kinematik kapsül modelleri. `/crew/<id>/pose` küçük bir C++ düğümüyle gz-transport `/world/<w>/set_pose` çağrısına çevrilir (10 Hz). ROS servis köprüsü üzerinden 20 Hz servis çağrısı yapılmaz.
- **`ros_gz_bridge` yaml (örnek):**
```yaml
- ros_topic_name: "/rover_1/lidar/points"
  gz_topic_name: "/world/bxw/model/rover_1/link/mast/sensor/lidar/scan/points"
  ros_type_name: "sensor_msgs/msg/PointCloud2"
  gz_type_name: "gz.msgs.PointCloudPacked"
  direction: GZ_TO_ROS
- ros_topic_name: "/clock"
  gz_topic_name: "/clock"
  ros_type_name: "rosgraph_msgs/msg/Clock"
  gz_type_name: "gz.msgs.Clock"
  direction: GZ_TO_ROS
```

---

## 11. Nav2 yapılandırması (rover_1 ve pr_1)

- `planner_server`: `SmacPlannerHybrid` (minimum dönüş yarıçapı rover parametresi). Uzun rota için `redline_planner`'dan gelen waypoint'ler `FollowWaypoints` ile izlenir.
- `controller_server`: `MPPIController`; `vx_max` 0,4 m/s (rover), 2,5 m/s (PR, varsayım).
- **Costmap katmanları:**
  - `static_layer`: DEM'den türetilmiş eğim maliyeti, `map_server` ile yüklenen OccupancyGrid
  - `obstacle_layer` / `voxel_layer`: LiDAR
  - özel `redline_cell_layer` (C++ costmap eklentisi): `CellDelta`'dan bilinmeyen ve kaya riski
- `collision_monitor`: `/rover_1/cmd_vel_gated` → `/rover_1/cmd_vel`; durma ve yavaşlama poligonları.
- **BT XML:** NavigateToPose + yeniden plan + `BackUp` + `Wait` + özel `RequestHelp` (Alert `ROBOT_HELP` yayımlar ve bekler).
- **Konum:** `robot_localization` ekf_node: teker odometrisi + IMU (+ isteğe bağlı görsel odometri). `map → odom` yayını `localization` düğümünde.

---

## 12. Uçuş kuralları (`config/rules.yaml`)

| ID | İfade | Sinyaller | Varsayılan | Tepki |
|---|---|---|---|---|
| FR-01 | `o2_rem ≥ wb_o2_q + o2_res` | Consumables, MarginField | o2_res 0,1 kg | WARNING; dönüş önerisi |
| FR-02 | aynı kural su için | | | |
| FR-03 | `t_shelter(x) ≤ T_SEP_max` (plan noktaları) | ShelterField | 20 dk | plan reddi |
| FR-04 | SEP alarmından 30 s içinde mod = SHELTER | DoseRate, MissionState | 30 s | EMERGENCY |
| FR-05 | `buddy_dist ≤ 100 m` ve görüş hattı; ihlal ≤ 60 s | CrewState ×2, link | 100 m | CAUTION→WARNING |
| FR-06 | bağlantı kaybı > 300 s → dönüş | link state | 300 s | WARNING |
| FR-07 | `M > M_cap` 5 dk'dan uzun → yavaşla; HR > 0,9·HR_max → uyarı | CrewState | f_cap 0,5 | CAUTION |
| FR-08 | eğim ≥ s_max hücresine girme (σ dahil) | konum, hücre | 25° | WARNING |
| FR-09 | konum σ > 20 m → 120 s içinde yeniden lokalizasyon | pose cov | 20 m | CAUTION |
| FR-12 | gün batımından T_dusk önce sığınakta | EnvState | 30 dk | WARNING |
| FR-13 | kurtarma süresi ≤ T_rescue_max | shelter | 30 dk | plan reddi |
| FR-14 | drone EV'lere ≥ 30 m ve dönüş rezervi | scout state | 30 m | drone RTL |

Kural kaynağı ve parametreleri SCENARIO varsayımıdır (v0.3 [K]).

---

## 13. Unreal projesi (`unreal/Redline`)

### 13.1 Modüller ve eklentiler
- Oyun modülü `Redline` (C++).
- Proje eklentisi `RedlineBridge` (C++, Runtime). Bağımlılıklar: `WebSockets`, `Json`, `JsonUtilities`, `ImageWrapper` (JPEG çözme), `DeveloperSettings`.
- Etkin motor eklentileri: `WebBrowserWidget` (Open MCT gömme denemesi [?]), `EnhancedInput`, `Landscape`.

### 13.2 `RedlineBridge` sınıfları

| Sınıf | Görev |
|---|---|
| `URedlineSettings : UDeveloperSettings` | `RosbridgeUrl` (`ws://localhost:9090`), `SiteId`, `ManifestPath`, yeniden bağlanma süreleri |
| `URedlineBridgeSubsystem : UGameInstanceSubsystem` | bağlantı, yeniden bağlanma (üstel geri çekilme 0,5→8 s); `Subscribe(Topic, Type, ThrottleMs, Delegate)`, `Advertise`, `Publish`, `CallService(…, Callback)`; gelen mesajları game thread'e taşır (`AsyncTask(ENamedThreads::GameThread, …)`); her topic için son mesaj zamanı (tazelik) |
| `URedlineCoords : UBlueprintFunctionLibrary` | `RosToUeLocation`, `UeToRosLocation`, `RosToUeRotation`, `UeToRosRotation` (§4.2); `MapToCellIndex` |
| `FRedlineOdometry`, `FRedlineCrewState`, `FRedlineMarginField`, `FRedlineRedLine`, `FRedlineAlert`, `FRedlineDoseRate`, `FRedlineEnvState`, `FRedlinePlan` (USTRUCT) | JSON → struct ayrıştırıcıları (`FJsonObjectConverter` veya elle) |
| `URedlineStaleMonitor` | topic başına `MaxAgeSec`; aşılınca `OnStale` olayı |

Protokol örnekleri (rosbridge v2):
```json
{"op":"subscribe","id":"sub-odom","topic":"/rover_1/odom","type":"nav_msgs/msg/Odometry","throttle_rate":100,"queue_length":1}
{"op":"advertise","topic":"/crew/EV1/pose","type":"geometry_msgs/msg/PoseStamped"}
{"op":"publish","topic":"/crew/EV1/pose","msg":{"header":{"frame_id":"map"},"pose":{"position":{"x":1.0,"y":2.0,"z":0.0},"orientation":{"x":0,"y":0,"z":0,"w":1}}}}
{"op":"call_service","id":"srv-1","service":"/redline/plan_eva","type":"redline_msgs/srv/PlanEva","args":{"site_id":"BXW","crew_ids":["EV1","EV2"],"candidate_target_ids":[],"max_duration_min":240,"objective":"SAFE"}}
```
- Unreal'dan action yerine `mission_manager` servisleri çağrılır; action'lar ROS içinde kalır.
- Izgaralar Unreal'a `FieldTile` (PNG) olarak gelir: `uint8[]` rosbridge'de base64 taşınır, Unreal `IImageWrapper` ile çözer ve `UTexture2D`'ye yazar. Ham float `MarginField` Unreal'a abone edilmez.
- Kırmızı/sarı çizgi `RedLine` poligonlarıyla gelir (küçük mesaj); spline mesh doğrudan buradan kurulur.
- **Çevrimdışı mod (köprü yedeği):** `RedlineBridge`, rosbridge yerine `runs/<run_id>/ue_feed.jsonl` dosyasını aynı mesaj biçiminde oynatabilir. Köprü veya ROS çökse de Unreal demosu ve video kaydı çalışır.

### 13.3 Aktörler
| Aktör | Görev |
|---|---|
| `ARedlineTerrain` | Landscape veya statik mesh; manifestten orijin; 3 nokta test işaretleri |
| `ARedlineRoverActor` | `/rover_1/odom` + `/rover_1/joint_states` → poz ve teker dönüşü; mod göstergesi |
| `ARedlinePrActor` | basınçlı rover (NASA SEV görseli); hayalet gelecek konumlar (`/pr_1/station_plan`) |
| `ARedlineDroneActor` | `/scout_1/odom`; rotor animasyonu |
| `ARedlineAstronautCharacter` | EV1 oyuncu; 20 Hz `/crew/EV1/pose` yayını; hız M1 tablosundan; Mars yerçekimi |
| `ARedlineAstronautProxy` | EV2; `/crew/EV2/state`'ten poz |
| `ARedlineOverlay` | `MarginField` → `UTexture2D` (dinamik, `UpdateTextureRegions`) → araziye decal veya landscape malzeme parametresi; kırmızı/sarı çizgi `USplineMeshComponent` ile |
| `ARedlineStationMarker` | istasyon pinleri; tıklanınca istasyon kartı |
| `ARedlineSkyController` | `/env/state` güneş az/el → Directional Light; SkyAtmosphere Mars ayarı |

Mars yerçekimi: World Settings → Global Gravity Z = −372,1 cm/s².

### 13.4 Widget'lar
| Widget | İçerik |
|---|---|
| `WBP_MapTable` | üstten ortografik `SceneCapture2D` + overlay; katman açma/kapama; hücre kartı (QueryCell) |
| `WBP_MissionWall` | PET zaman çizelgesi, EV1/EV2 pay dakikası, sınırlayan sarf, kural durumu, veri yaşı |
| `WBP_SpaceWeather` | RAD doz hızı grafiği + %25 eşik + kümülatif doz + "PDS PPI · sol 4190 · ölçüm" rozeti |
| `WBP_RobotConsole` | rover/drone kamera (`CompressedImage` → `UTexture2D`), mod, görev kuyruğu, "yardım isteği" |
| `WBP_Science` | APXS/LIBS kartları (hata çubuklu), posterior grafiği, numune kaydı |
| `WBP_Sensitivity` | tornado grafiği |
| `WBP_HUD` | kalan pay, sonraki istasyon, dönüş oku, alarm; merkez boş |
| `WBP_Tablet` | brifing, cuff checklist |
| `WBP_POVSwipe` | gerçek Navcam karesi ↔ aynı pozdan render |
| `WBP_DataAge` | kaynakların son kaydı ve yaşı |
| `WBP_OpenMct` | Web Browser widget ile `http://localhost:8080` (deneme) |

Grafik çizimi için C++ `URedlineLineChart : UWidget` (SLeafWidget + `OnPaint` içinde `FSlateDrawElement::MakeLines`). Halka tamponlu seriler, eksen etiketleri, eşik çizgisi.

### 13.5 Arazi içe aktarma
1. `data/engines/<site>/heightmap.png` (16 bit), `terrain_meta.json` (boyut, çözünürlük, z_min, z_max, Z ölçeği).
2. Landscape boyutu önerilen değerlerden biri olmalı (ör. 1009 veya 2017 vertex [?]). XY ölçeği = çözünürlük(m) × 100.
3. Z ölçeği = (z_max − z_min) × 100 / 512. Landscape konumu z = z_min × 100 + aralığın yarısı (içe aktarma ofseti).
4. Doku: ortho → `T_<site>_Ortho` → landscape malzemesinde dünya koordinatından UV.
5. **Kabul:** manifestteki 3 test noktasında Unreal'daki line trace yüksekliği ile DEM farkı ≤ 10 cm.

### 13.6 Unreal testleri (Automation)
- `Redline.Coords.RoundTrip`: rastgele 1000 poz için ROS→UE→ROS hatası < 1e-4.
- `Redline.Coords.Axes`: ROS +x → UE +X, ROS +y → UE −Y, ROS yaw +90° → UE yaw −90°.
- `Redline.Bridge.Reconnect`: sunucu kapanınca `OnStale`; açılınca abonelikler yeniden kurulur.

---

## 14. Open MCT (`openmct/`)

- `npm install openmct` [?: sürümü sabitle]. `index.html` içinde Open MCT başlatılır ve `redline-plugin.js` yüklenir.
- **Sözlük** `dictionary.json`: telemetri noktaları ve birimler. Örnekler:
  - `rad.dose_b`, `rad.dose_e`, `rad.background_b`
  - `ev1.margin_min`, `ev1.o2_kg`, `ev1.hr`, `ev2.*`
  - `rover1.speed`, `rover1.mode`
  - `safety.violations`
  - `env.sun_el`, `env.pressure`, `science.weh_sigma_max`
- **Gerçek zamanlı:** roslibjs ile `ws://localhost:9090` → ilgili topic'ler → `{timestamp, value}`.
- **Geçmiş:** `redline_telemetry/history_server` (FastAPI, SQLite). `GET /history/<key>?start=&end=` uç noktası. `telemetry_adapter` düğümü SQLite'a yazar.
- **Zaman:** Time Conductor'da UTC; ek sütunda LMST.
- **Kabul:** sol 4190 replay'inde doz grafiği Open MCT ve Unreal `WBP_SpaceWeather`'da aynı değerleri gösterir.

---

## 15. Web harita (`web/`)

- OpenLayers + `ol/source/GeoTIFF` (COG) + WebGLTile. Projeksiyon olarak yerel ENU metre kullanılır (`ol/proj/Projection`, units 'm').
- Katman listesi STAC Collection'dan okunur. Her katmanın lejantında statü rozeti bulunur.
- **EVA kartı:** plan JSON'undan yazdırılabilir HTML (istasyonlar, PET, dönüş noktaları, sınırlayan sarf).

---

## 16. Senaryolar (`config/scenarios/`)

Şema:
```yaml
id: S1_SEP_4190
site: BXW
seed: 42
time_scale: 10
start:
  historical_utc: "2024-05-20T00:00:00Z"   # RAD dosyası penceresine göre ayarla [D: dosya 2024-140 18:30 başlıyor]
  pet_min: 0
crew: [EV1, EV2]
suit_profile: default
replay:
  rad: {sols: [4189, 4190, 4191], detector: B}
  rems: {sols: [4190]}
events:
  - {t_min: 45, type: ROBOT_FINDS_OBSTACLE, params: {cell_radius_m: 15}}
expected:
  - {rule: FR-04, must_hold: true}
```

| ID | Saha | Amaç |
|---|---|---|
| S0_NOMINAL | BXW | kural ihlali yok; plan ve çizgi sabit |
| S1_SEP_4190 | BXW | gerçek SEP replay; alarm, çizgi daralması, ReturnToShelter, PR karşılama |
| S2_SUIT_LEAK | BXW | EV2 O₂ tüketimi ×3; sınırlayan sarf değişir; çizgi EV2'ye göre daralır |
| S3_CONJUNCTION_242 | YKB | Dünya bağlantısı yok; sol 242 B alarmı, E alarmsız; yerel karar |
| S4_BLOCKED_CORRIDOR | BXW | drone/rover gözlemi bir koridoru kapatır; VOI ve yeniden plan |
| V1_YKB_RETRO | YKB | yalnız yörünge önerisi ↔ Curiosity izi; karne |
| V2_BXW_TIMESPLIT | BXW | sol 4533 öncesi veriyle plan ↔ 4534–4805 bulguları; karar kuralı commit hash'iyle donduruldu |
| V3_MONTE_CARLO | BXW | 1000 koşu; yalnız yörünge ↔ yörünge + robot; Wilson aralığı |

Determinizm: aynı `id + seed`, aynı ihlal dizisi ve aynı plan sürümlerini üretir. Her koşu `rosbag2` MCAP olarak `runs/<run_id>/` altına kaydedilir.

---

## 17. Test ve kabul ölçütleri

| Seviye | Araç | Ölçüt |
|---|---|---|
| Birim | pytest, Hypothesis | §7.14 altın testleri geçer |
| Veri QA | `redline-data qa` | CRS raporu temiz; nodata < %2 (AOI içi); 3 nokta testi ≤ 10 cm |
| ROS entegrasyon | launch_testing | S0'da ihlal yok; S1'de FR-04 sağlanır; S2'de limiting = O2 ve EV2 |
| Sözleşme | pytest + UE Automation | eksen/birim, saat, stale komut reddi, tekrar komut koruması |
| Performans | pytest-benchmark | walkback ≤ 1 s (3×3 km, 4 m); tick başına marj güncellemesi ≤ 20 ms; VOI aday ≤ 50 ms; FieldTile PNG ≤ 300 KB |
| Uçtan uca | `scripts/check_ready.py` | odom, TF, LiDAR, kamera, IMU, rosbridge, UE bağlantısı hazır |
| Replay | rosbag2 | aynı MCAP iki kez oynatılınca Unreal ekranları aynı olay sırasını gösterir |

---

## 18. Uygulama sırası (kilometre taşları)

Her taşın sonunda `docs/PROGRESS.md` güncellenir. Taşlar sıralıdır; ekipte paralel çalışılırsa arayüzler (§5) önce dondurulur.

### 18.1 Önce çelik iplik (son inceleme kararı)
- İlk hedef bütün sistemi değil, **uçtan uca ince bir dikey hattı** çalıştırmaktır:
  BXW verisi (4 m) → `redline_core` walkback/çizgi → ROS düğümü → `FieldTile` + `RedLine` → Unreal arazi + overlay + EV1 yürüyüşü → sol 4190 RAD replay → alarm → çizgi daralması.
- **Bu hattın Gazebo'ya ihtiyacı yok.** Gazebo/Nav2 (T3) ayrı akışta paralel ilerler ve iplik çalıştıktan sonra "rover gözlemi → hücre deltası" ile birleşir.
- Hedef: iplik H+14 civarında çalışsın. Bundan sonraki her taş ipliğe genişlik ekler; iplik hiç kırılmaz.
- **H+30'da altın koşu:** en iyi senaryo koşusu MCAP ve `ue_feed.jsonl` olarak dondurulur; video bundan çekilir. Sonrası cila ve ek derinliktir.

### 18.2 Paralel akışlar (insan veya AI ajanı başına bir paket grubu)

| Akış | Paketler | İlk teslim | Bağımlılık |
|---|---|---|---|
| A Veri | `redline_data` | BXW 4 m DEM, eğim, σ, ufuk küpü, RAD parquet | yok |
| B Çekirdek | `redline_core` | walkback, redline, cost_human, sep + altın testler | A'nın ızgara biçimi (sahte veriyle başlar) |
| C ROS görev | `redline_msgs`, `redline_env`, `redline_planner`, `redline_mission` | FieldTile/RedLine/DoseRate yayını | B |
| D Robot | `redline_gazebo`, `redline_description`, `redline_navigation` | rover Nav2 ile sürer | A'nın ops_box mesh'i |
| E Unreal | `unreal/Redline`, `RedlineBridge` | arazi + overlay + EV1 + uzay havası grafiği | C mesajları (önce `ue_feed.jsonl` ile sahte akış) |
| F Bilim / teslim | `redline_science`, `openmct`, `web`, `docs` | B4/B2 ve Open MCT; teslim belgeleri | C |

Kurallar:
- İlk saat sonunda §5 mesajları ve §4 sözleşmeleri **dondurulur**. Değişiklik yalnız `docs/DECISIONS.md` kaydıyla yapılır.
- Her akış önce sahte veri veya sahte topic ile çalışır (stub), gerçek bağımlılık gelince değiştirir.
- Her akışın kendi dalı olur; `main`'e günde birkaç kez, testler yeşilken birleştirilir.

| Taş | İçerik | Bitti ölçütü |
|---|---|---|
| **T0** | repo iskeleti, AGENTS.md, venv, colcon, `redline_msgs` derlenir, CI (pytest + colcon test) | `colcon build` ve `pytest` yeşil |
| **T1** | veri hattı BXW: catalog → fetch → crs → enu → derive → stac → qa | QA raporu, 3 nokta testi |
| **T2** | `redline_core`: cost_human, walkback, redline, rocks, radiation, pet + altın testler | testler yeşil; BXW için ilk margin haritası PNG |
| **T3** | Gazebo BXW dünyası, rover (Curiosity portu veya yedek), sensörler, ros_gz_bridge, Nav2 ile hedefe sürüş | rover RViz'den verilen hedefe varır |
| **T4** | rosbridge + `RedlineBridge` + arazi içe aktarma + rover pozu Unreal'da + koordinat testleri | UE Automation testleri yeşil; rover Unreal'da doğru yerde |
| **T5** | `cell_store`, `walkback_field`, `RedLine` → `ARedlineOverlay`; EV1 Unreal'dan yürür, çizgi canlı | Unreal'da çizgi ve pay dakikası görünür |
| **T6** | `scenario_player`, `rad_replay`, `env_server`, `sep.py`, `rule_monitor`, `ReturnToShelter`, `WBP_SpaceWeather` | S1 testi geçer; Unreal'da alarm ve çizgi daralması |
| **T7** | `voi_tasker`, `SurveyArea`/`InspectTarget`, drone (`ExecuteScout`), S4 | S4: gözlem → hücre değişimi → yeniden plan; DecisionRecord |
| **T8** | bilim çatısı + B2 (LIBS/otonom hedef) + B1 (temas bilimi) + B4 (DAN GP) + B6 (numune) + B7 (istasyon) | her biri ürün + EvidenceRecord + harita katmanı yazar |
| **T9** | `rover_placer` (PR hayalet konumlar), `ev_sim` EV2, S2 (giysi kaçağı), FR-05, link_manager | S2 testi geçer |
| **T10** | B5 sondaj FDIR, B8 zamanlayıcı, B9 downlink, B3 multispektral, B10 astronot notları | her biri bir senaryoda çalışır |
| **T11** | Open MCT eklentisi + history_server; Web Browser gömme denemesi; web harita ve EVA kartı | Open MCT'de doz ve pay grafikleri |
| **T12** | V1, V2, V3 doğrulamaları; tornado grafiği; debrief (MCAP replay) | `validation/` çıktıları ve figürler |
| **T13** | YKB sahası (T1–T5 tekrarı) + S3 | sol 242 sahnesi |
| **T14** | video çekimi, slaytlar, teslim belgeleri, son QA | §19 dosyaları tamam |

---

## 19. Teslim belgeleri (şablonlar)

**`docs/PRE_EXISTING_WORK.md`**
- 14 Kasım 2026 09:00 öncesi: yalnız araştırma ve tasarım notları (ayrı özel depo).
- Bu depodaki bütün kod hackathon sırasında yazıldı; ilk commit zamanı ve hash'i buraya yazılır.
- Eski ROS demosunun kodu kopyalanmadı.

**`docs/DATA_SOURCES.md`**
- Tablo sütunları: ürün, görev/cihaz, ID/sürüm, URL, erişim tarihi, hash, statü, REDLINE'daki rolü, lisans/kredi.
- `redline-data catalog` çıktısından üretilir.
- DEM'deki ESA HRSC girdisi ayrıca belirtilir.

**`docs/AI_DISCLOSURE.md`**
- Kullanılan AI araçları ve hangi iş için kullanıldıkları: tasarım araştırması, kod yardımı, metin düzenleme.
- AI üretimi görsel/video varsa liste ve görünür "AI-generated" işareti.
- NASA verileri AI tarafından üretilmedi.
- AI içeriğinde NASA logosu yok.

**`docs/THIRD_PARTY_NOTICES.md`**
- 3D modeller, kütüphaneler ve lisansları (kılavuz §8–9).

---

## 20. Açık doğrulamalar (kodlamadan önce)

| Konu | Neden | Nasıl |
|---|---|---|
| space-ros Curiosity modelinin Jazzy/Harmonic uyumu | taşıma süresi | `colcon build` + spawn denemesi |
| gz-sim sistem adları (MulticopterMotorModel, ForceTorque, Contact) | SDF doğruluğu | `gz sim -s` ile örnek dünya |
| rosbridge'in ROS 2 action desteği | Unreal arayüzü | `send_action_goal` denemesi; çalışmazsa servis adaptörü |
| Unreal Web Browser widget'ında Open MCT | gömme | paketlenmiş build'de deneme |
| REMS PDS ürün biçimi | env replay | etiket okuma |
| ChemCam / DAN tekil ürün yolları | B2/B4 kalibrasyonu | PDS Geosciences dizin taraması |
| BXW batı kenarında LRGB/DEM nodata | saha sınırı | QA raporu |
| WSL2 localhost yönlendirmesi | köprü | `ws://localhost:9090` testi |
| Landscape boyut ve Z ofseti | arazi eşleşmesi | 3 nokta testi |
| Teslim saati ve biçimi | plan | resmî sayfa |

---

## 21. Yeni depo için `AGENTS.md` şablonu

```markdown
# REDLINE (Space Apps 2026, Martian Map) — agent rules

Design: REDLINE_V3_KILAVUZU.md (what/why). Implementation: REDLINE_V3_UYGULAMA_SPEKI.md (how).
Follow milestones T0→T14 in order; update docs/PROGRESS.md after each.

Hard rules:
- Never fabricate NASA measurements. Every value carries Provenance.status
  (ARCHIVE/DERIVED/SIMULATED/SCENARIO) and a product id or scenario seed.
- Read CRS from product metadata; no Earth/WGS84 defaults; bbox overlap ≠ alignment.
- eqc→ENU uses x=(E−E0)·cos(φ0). ROS→UE: (100x, −100y, 100z), FQuat(−x, y, −z, w).
- Robot physics/autonomy live in ROS/Gazebo; Unreal renders and sends commands only.
- Algorithms live in python/redline_core; ROS nodes and UI only call it.
- Each core function has unit tests; golden tests in spec §7.14 must pass.
- Sample origin ≠ analysis location; APXS table coords are rover pose.
- Do not copy code from the old research repo.
- Verify [?] items with a small experiment and log in docs/VERIFICATION_LOG.md.
- No secrets in the repo.
```
