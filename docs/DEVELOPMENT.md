# Geliştirme: T0 ve T1 veri hattı

Esas uygulama belgesi [proje.md](proje.md). Fikir/gelişim belgeleri [research/](../research/README.md), çalışma günlüğü [journal/](../journal/README.md) altında. Görsel tasarım, Unreal sahne içeriği ve 3D varlıklar kullanıcıyla birlikte hazırlanacak.

## WSL / Ubuntu 24.04

ROS Jazzy ve Python 3.12 ortamında repo kökünden:

```bash
bash scripts/bootstrap.sh
bash scripts/test.sh
```

Windows PowerShell'den, bu klasörde:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd "/mnt/c/Users/USER/Desktop/SPACE APPS BASKETBEYBİ" && bash scripts/bootstrap.sh && bash scripts/test.sh'
```

Bootstrap sistem Python'unu değiştirmez; Linux kullanıcı önbelleğinde bu checkout'a özel venv oluşturur. Bağımlılıklar `scripts/requirements-test.txt` içinde sabittir. Saf Python testleri ROS'un `PYTHONPATH` ve pytest eklentilerinden ayrıdır. Colcon, Jazzy'nin `/usr/bin/python3` yorumlayıcısını kullanır. Aktif bir venv veya çelişen ROS dağıtımı varsa script durur.

## Türkçe/boşluk içeren Windows yollarında ROS derlemesi

Yerel Jazzy `rosidl` üreticisi bu checkout yolundaki `İ` karakterini keserek configure hatası verdi. `scripts/test.sh`, `ros_ws/src` içeriğini WSL'de kısa ASCII yollu **yeni bir çalışma alanına** kopyalar; kaynak ve kopyanın tüm SHA256 değerlerini karşılaştırır. Eski ROS overlay/build kullanılmaz ve sistem ROS dosyaları yamalanmaz.

Her koşunun kanıtları `test-results/run-*/` altında saklanır:

- `python.xml`: saf Python testleri.
- `ros-workspace.json`: gerçek build yolu, kaynak ağaç hash'i ve dosya hash'leri.
- `ros/build/.../test_results/`: üretilmiş arayüzlerin test raporu.
- `ros/log/`: ilgili build/test koşusunun günlükleri.

Bu dizin Git'e alınmaz; CI aynı raporları artifact olarak yükler. Hash'le doğrulanan Linux workspace yolu test çıktısında yazılır. Ardından ROS komutları kullanmak için yeni WSL shell'inde Jazzy underlay'i ve **o koşunun** `install/local_setup.bash` dosyasını source et. Repo içindeki eski başarısız `ros_ws/build` veya `install` dizini geçerli build değildir.

## Şimdilik çalışanlar

`redline_core`: metre/santimetre, Y ekseni ve quaternion sözleşmeleri; fizik/PET saat tipleri ve açık UTC replay eşlemesi. `redline_data`: `catalog`, `fetch`, `crs`, `enu`, `derive`, `compare`, `stac`, `stac-validate`, `qa`, `qa-final` komutları çalışır. T1 yerel veri kabulü geçti. T2 çekirdeği aşağıdaki bölümde.

`redline_msgs`: 22 mesaj, 5 servis, 11 aksiyon; üretilmiş C/Python typesupport ve CDR serileştirmesi test edilir. Bu testler çalışan DDS topic'leri veya action server'ları olduğunu göstermez.

BXW için gerçek 3 × 3 km Gale DEM penceresi, 1 m yerel arazi, 4 m planlama ızgarası, 2/5 m eğim ve pürüzlülük üretildi. Planner/ROS düğümü veya Unreal köprüsü henüz yazılmadı. `FieldTile` 16-bit nodata sözleşmesi ve tanımsız `CollectSample` adı gerçek üretici yazılmadan netleştirilmeli.

## T1 kurulumu ve test

Tam BXW T1 koşusu:

```bash
bash scripts/bootstrap-data.sh
bash scripts/run-t1.sh
```

Runner kaynak erişimi/crop/CRS/ENU/derive/iki-DTM karşılaştırması/QA/test/manifest/STAC/şema/final kabul sırasını çalıştırır. Her kabul koşusu yeni `data/stac/BXW/t1-run-*/` metadata ve `data/derived/BXW/t1-run-*/qa_BXW.html` üretir. Büyük veri aşamaları istek/hash eşleşen önbelleği kullanır. Pinned metadata ve özgün IMG aktarım kanıtları `docs/verification` altında olmalı; source link, evidence ve kod hash'leri kontrol edilir. GIS bağımlılığı veya test eksikliği yeşil sonuç sayılmaz. Bu runner Git/GitHub veya Tripo çalıştırmaz.

14 Kasım 13:44 kabulü: **299 test**, 0 hata/başarısız/atlanan; 12 STAC Item; sekiz kabul kapısı true. [Snapshot](../data/stac/BXW/t1-run-lfDo4ErT/t1_acceptance.json). Aşağıdaki komutlar tek tek aşama çalıştırmak içindir; eski ara checkpoint `qa.html` dosyaları tam kabulün yerine geçmez.

Repo kökünde WSL shell'i:

```bash
bash scripts/bootstrap-data.sh
bash scripts/test-data.sh
source scripts/common.sh
```

`bootstrap-data.sh` aynı izole Python 3.12 venv'ine sabit NumPy/Rasterio/PyProj bağımlılıklarını ekler. Rasterio wheel'inin GDAL'ı 3.9.3'tür; bu, sistemde `gdalinfo` veya `osgeo` kurulduğu anlamına gelmez. `test-data.sh` GIS modülleri eksikse durur, atlanan testleri kabul etmez ve yeni `test-results/data-run-*/python.xml` üretir.

Ardından, repo kökünde:

```bash
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" catalog --site BXW --product gale_dem_v3 --out data/stac/BXW/catalog.json
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" fetch --site BXW --product gale_dem_v3 --expected-radius-m 3396190 --out data/raw/BXW/gale_dem_v3.tif
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" crs data/raw/BXW/gale_dem_v3.tif --expected-radius-m 3396190 --out data/stac/BXW/crs_report.json
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" enu data/raw/BXW/gale_dem_v3.tif --site BXW --expected-radius-m 3396190 --h0-m 0 --resolution-m 1 --out data/derived/BXW/dem_enu.tif
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" enu data/raw/BXW/gale_dem_v3.tif --site BXW --expected-radius-m 3396190 --h0-m 0 --resolution-m 4 --out data/derived/BXW/dem_plan_4m.tif
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" derive data/derived/BXW/dem_enu.tif --out data/derived/BXW/terrain
env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" qa data/raw/BXW/gale_dem_v3.tif data/derived/BXW/dem_enu.tif --terrain data/derived/BXW/terrain --out data/derived/BXW/qa_1m
```

Gale kaynağı tiled COG değil, satır şeritli TIFF'tir. `fetch`, önce 16 baytlık HTTP Range desteğini kontrol eder; çıktı piksel sayısını ve dokunulan kaynak bloklarının açılmış boyutunu sınırlar. Tam mozaik indirme komutu yoktur. Küçük deneme için `fetch --size-m 128 128` ve farklı çıktı yolu kullanılabilir.

ENU GeoTIFF'leri yerel mühendislik metreleridir; Dünya veya kaynak EQC CRS'i ile etiketlenmez. Zorunlu `.provenance.json` sidecar'ı kaynak Mars WKT'sini, `(E0,N0,H0)` orijinini, cos(enlem) ölçeğini, affine dönüşümünü, sürümleri ve hash'leri saklar. `H0=0` bu koşudaki açık senaryo seçimidir; düşey datumun doğrulandığı anlamına gelmez. 4 m çıktı bilinear örneklemedir; 4 × 4 alan ortalaması değildir.

2/5 m eğimler **1 m yerel grid'den** üretilir. Baseline iki örnek arasındaki toplam fiziksel mesafedir; 5 m uçları doğrusal örneklenir. 4 m grid'den 2/5 m eğim çıkarmak hata verir. Pürüzlülük, 5 × 5 hücrelik yerel düzleme göre RMS yükseklik artığıdır. `derive` ikinci DTM olmadan sigma uydurmaz; sonraki `compare` aşaması iki kayıtlı DTM'den `slope_sigma.tif` üretir. Bu, **derece cinsinden ampirik 5 m eğim farkı proxy'sidir**, bağımsız 1σ değildir. Destek dışı kenarlar bilinmiyor olarak kalır.

Pencere/ENU/derive/QA tekrarları yalnız istek ve dosya SHA256'ları eşleşiyorsa mevcut sonucu kullanır. Değişen istek, bozuk çıktı veya yarım kalmış dizin için yeni yol gerekir; eski sonuç sessizce ezilmez. Canlı kaynak ETag'i bu önbellek kullanımında yeniden sorgulanmaz. Aynı kaynağın yeni sürümünü almak için farklı çıktı yolu seç.

İlk ara QA: `data/derived/BXW/qa_1m/qa.html`. Sayısal üç nokta testi kaynak piksellerinden yerel grid'e dönüşümü sınar; bağımsız arazi, feature hizası veya Unreal doğruluğu değildir. İlk hafif kayıt `data/stac/BXW/run_manifest.json` STAC Collection değildir. Tam runner'ın yeni dizininde `catalog/collection.json` ve 12 Item, şema raporu ve ayrı kabul raporu bulunur. Elle yalnız küçük manifest üretme örneği:

```bash
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/record_data_run.py --site BXW --test-report test-results/data-run-1k6K8jYU/python.xml --out data/stac/BXW/run_manifest-yeni.json
```

Test raporu yolunu kendi koşunla değiştir. Ham/türetilmiş rasterlar `data/raw` ve `data/derived` altında yerelde tutulur; Git'e alınmaz. Kullanıcının 14 Kasım yönlendirmesinden sonra commit/push veya GitHub işlemi yapılmaz.

## T2 çekirdek: dönüş alanı ve kırmızı çizgi

`redline_core` artık §7'nin T2 kısmını içerir: `grid`, `cost_human` (Tobler × Froude hızı, Mars ölçekli Pandolf, sarf dönüşümleri, yasak kuralları, numba kenar çekirdeği), `walkback` (numba yığınlı çok kaynaklı Dijkstra, `leg_cost`, `walkable_components`), `redline` (pay, sınırlayan sarf, SEP kısıtı, çizgi halkaları), `radiation`, `rocks`, `sep`, `shelter` (darboğaz DP), `pet` ve `params`. Parametreler SCENARIO etiketli `config/crew.yaml` ve `config/suit.yaml` dosyalarından okunur.

Bağımlılıklar `scripts/requirements-core.txt` içinde sabittir ve `bash scripts/bootstrap.sh` tarafından wheel olarak kurulur. Testler `bash scripts/test.sh` içinde diğer saf Python testleriyle birlikte koşar. Yalnız çekirdek testleri için repo kökünde:

```bash
source scripts/common.sh
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$REDLINE_VENV/bin/python" -m pytest python/redline_core/tests -q
```

BXW ilk margin haritası (T1 veri bootstrap'ı da gerekir; girdiler T1 kabul manifestinin SHA256 değerleriyle doğrulanır):

```bash
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/t2_margin_map.py
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/bench_walkback.py
```

İlki `data/derived/BXW/t2-run-<UTC>/` altına PNG ve `t2_summary.json` yazar; harita SCENARIO ürünüdür, plan değildir. İkincisi 750 × 750 hücrenin tamamı erişilebilirken walkback süresini ölçer (§7.5 hedefi ≤ 1 s). Numba ilk çağrıda derler ve `__pycache__` altına önbellek yazar; zaman ölçümünde ilk çağrı ayrı raporlanır. Model kararları ve kullanıcı kararı bekleyen maddeler [D008](DECISIONS.md) içinde.

## T5 ROS ipliği: hücre deposu, canlı dönüş alanı, kırmızı çizgi

Gazebo gerektirmez (spek §18.1). Düğümler `redline_core`'u import ettiği için REDLINE venv Python'uyla çalışır; launch dosyası bunu `prefix` ile yapar ve yolu `REDLINE_PYTHON` ya da `REDLINE_VENV`'den alır. Sözleşmeler [D009](DECISIONS.md).

```bash
# Bir kez: T1 ürünlerinden BXW 4 m planlama ızgarası (hash doğrulamalı, DERIVED)
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/export_planning_grid.py
# T5 paketlerini ayrı ASCII çalışma alanında derle ve test et
bash scripts/build-t5.sh            # veya: bash scripts/build-t5.sh redline_planner
# Gerçek BXW + rosbridge (domain 86, port 9190) + Unreal yerine geçen yürüyüş; ue_feed.jsonl üretir
bash scripts/run-t5-bxw.sh <build-t5.sh'nin yazdığı workspace>
```

Unreal'a bağlanmak için ipliği elle başlatma: `ros2 launch redline_planner t5_thread.launch.py rosbridge:=true time_scale:=1.0 redline_root:=$REDLINE_ROOT` (varsayılan rosbridge portu 9090). Unreal `/crew/EV1/pose`'u (`geometry_msgs/msg/PoseStamped`, frame `map`) yayınlar; `/redline/redline` ve `/redline/tiles/margin_min`'e abone olur. `margin_now_min` erişilemez konumda `null` gelir.

## T6 SEP hattı: S1 senaryosu, RAD tekrarı, ortam durumu

Gazebo gerektirmez. Kararlar [D012](DECISIONS.md) ve [D014](DECISIONS.md). `data/raw/` ve `data/env/` git dışıdır; iki betik bunları kaynaktan yeniden üretir.

```bash
# Bir kez: PDS PPI RAD sol 4189–4191 (ARCHIVE) → data/env/rad_*.csv, [D] değer kontrolü
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/fetch_rad.py
# Bir kez: NAIF çekirdekleri (SHA256 sabitli) → SPICE güneş tablosu (DERIVED) ve LMST/öğle/gün batımı kontrolü
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/build_sun_table.py
bash scripts/build-t5.sh
# Gerçek S1: BXW + RAD sol 4190 + güneş tablosu, 60× PET, rosbridge (domain 86, port 9190)
bash scripts/run-s1-bxw.sh <build-t5.sh'nin yazdığı workspace>
```

Özet `test-results/s1-bxw-<run_id>/s1_summary.json`, Unreal beslemesi `runs/<run_id>/ue_feed.jsonl` dosyasına yazılır. Elle başlatma: `t5_thread.launch.py` için `scenario_file:=` ve `sun_table:=` argümanları. `env_server` ve FR-12 gün ışığı terimi ikisi birlikte verilince açılır; `sun_table` yoksa ikisi de kapalıdır ve S1 geri kalanı aynı çalışır. Unreal için topic'ler: `/env/state` (EnvState, 1 Hz; REMS alanları şimdilik `null`), `/env/dose_rate`, `/redline/mission/state`, `/redline/alerts`, `/safety/violations`, `/redline/scenario/control` (servis).
