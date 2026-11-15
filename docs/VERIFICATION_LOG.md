# Doğrulama günlüğü

## 15 Kasım 2026, 04:00 (+03:00) — Genel görev ve robot incelemesi

Kaynak/kayıt incelemesi; yeni simülasyon veya kabul testi çalıştırılmadı.
T3/T4/T5 tarihli teknik kabulleri ile anlatı önizlemesi ayrı değerlendirildi.
Standart EVA akışı PRECURSOR/bilim kampanyasını açmıyor; drone SIMULATED stub.
Son S4 yalnız v1; keşif alanı engeli 4 m ile kaçırdığı için v2 kabulü yok.
Güncel koridor düzeltmesi sonrasında S4/S4c kaydı bulunmadı. Scout aksiyon
sonucu denetimi ve stub evre koruması kaynak açığı olarak kaydedildi; canlı
hata üretildiği iddia edilmez. Son ROS snapshot'ındaki 59 test hatasız;
daha eski 604 core testi güncel yeniden koşu sayılmadı. Kilometre taşı
kapatılmadı. [Bulgular ve kanıtlar](GENEL_DURUM_KONTROLU.md).

14 Kasım 2026 · Europe/Istanbul · Yeni depo hazırlığı. Aşağıdakiler bu aktarım sırasında alınan sonuçlardır; tarihsel araştırma bulguları yeni doğrulama sayılmaz.

## Aktarım ve bütünlük

| Kontrol | Sonuç | Kanıt / sınır |
|---|---|---|
| Hedef repo | GEÇTİ | `git remote -v`: `https://github.com/ahmetefesensoy/redline.git`; `main...origin/main`. Aktarım öncesi çalışma ağacı temiz, yalnız `.git` mevcut. |
| Paket | GEÇTİ | 562 ZIP girdisi; 7.911.552 bayt açılmış içerik; manifest hariç 561 payload dosyası. |
| ZIP yol güvenliği | GEÇTİ | Hedef kökten çıkış, `.git` girdisi, Windows sürücü yolu, mevcut dosyayı ezme, case-insensitive tekrar ve symlink kontrolü. |
| Payload bütünlüğü | GEÇTİ | Manifestteki 561 dosyanın tamamında boyut ve SHA256 eşleşti; 0 sorun. |
| Proje skill bütünlüğü | GEÇTİ | `python -X utf8 tools/verify_skill_installation.py`: `Project skills checked: 18`, `Recorded files checked: 428`, `Issues: 0`; exit 0. |
| Yeni uygulama kodu | HENÜZ YOK | Paket eski ROS/web/rover uygulamasını içermiyor. `önceki deneme` altında yalnız araştırma Markdown ve provenance kayıtları var. Skill helper'ları uygulama kodu değildir. |

Kaynak arşiv: `C:\Users\USER\Desktop\space apps\output\handoff\REDLINE_V3_BASLANGIC_PAKETI.zip`.

Arşiv SHA256: `3B4554361A7CE998168B4F7AC9AF92B6A602ACC352F2DC110F4F53E523E33DAE`.

`HANDOFF_MANIFEST.json` orijinal payload'ı tanımlar. Bu günlük ve diğer yeni kayıtlar aktarım sonrasında oluşturulduğundan özgün payload manifestine eklenmedi.

## Windows envanteri

| Bileşen | Gözlenen sonuç | Doğrulamanın sınırı |
|---|---|---|
| Python | 3.12.10 | `python --version`, `py -0p`; yeni proje venv'i oluşturulmadı. |
| Node / npm | v24.22.1 / 11.19.1 | Mevcut sürümler; spekteki Node 20 [?] yerine pin seçilmedi. Open MCT engine gereksinimleri uygulama aşamasında kontrol edilecek. |
| Git / gh / uv | 2.56.0.windows.3 / 2.103.3 / 0.13.6 | Sürüm komutları çalıştı. |
| WSL | Ubuntu-24.04, WSL2, Running | `wsl --list --verbose`; docker-desktop ayrıca listede, Stopped. |
| Unreal | 5.8.4, changelist 58902052 | `C:\Users\USER\Desktop\UE_5.8\Engine\Build\Build.version` okundu; editör veya build çalıştırılmadı. |
| Visual Studio C++ | VS 2022 Community | `vswhere` ile VC.Tools.x86.x64 bileşenine sahip kurulum bulundu. UE uyumlu toolset/SDK ve gerçek derleme henüz denenmedi. |
| Yeni UE projesi | YOK | `unreal/Redline/Redline.uproject` mevcut değil. |
| Blender ortak referansları | EKSİK | `C:\Users\USER\.codex\skills\references` yok; aktarımda belirtilen eksik devam ediyor. |

## WSL temel ortamı

Ubuntu 24.04.5 LTS; kullanıcı `ahmetefesensoy`; kernel `6.18.33.2-microsoft-standard-WSL2`; Python 3.12.3.

ROS ortamı `/opt/ros/jazzy/setup.bash` ile yüklendikten sonra:

| Bileşen | Gözlenen sonuç |
|---|---|
| ROS_DISTRO / rclpy | jazzy / `/opt/ros/jazzy` |
| colcon | `/usr/bin/colcon`; common extensions 0.3.0-100 |
| ROS base | 0.11.0 |
| ros_gz_bridge | 1.0.24 |
| navigation2 / nav2_bringup | 1.3.13 / 1.3.13 |
| ros2_control / gz_ros2_control | 4.48.1 / 1.2.20 |
| Gazebo | `gz sim --version`: 8.15.0 (Harmonic); ROS vendor yolu üzerinden erişiliyor. |
| Gazebo meta paketi | `gz-harmonic` adlı paket bulunmadı. Bu, çalışan `gz sim` sürüm kontrolünü geçersiz kılmaz. |
| rosbridge / MoveIt / Foxglove | İlgili `ros-jazzy-rosbridge-server`, `ros-jazzy-moveit`, `ros-jazzy-foxglove-bridge` Debian paketleri bulunamadı. Diğer workspace'lerde source kurulumu araştırılmadı. |
| GDAL/GIS | `gdalinfo` PATH'te yok; `gdal-bin` sürüm döndürmedi. Temel Python'da `pip show` GDAL, rasterio, pyproj, pystac, spiceypy, pvl, pds4-tools bulamadı. Diğer venv'ler hakkında sonuç çıkarılmadı. |
| numpy / scipy | 1.26.4 / 1.11.4, WSL temel Python ortamı. |
| WSL GPU aygıtı | `/dev/dxg` var. GPU/sensör render testi yapılmadı. |

İlk WSL envanter komutunda `set -u`, ROS setup dosyasındaki opsiyonel `AMENT_TRACE_SETUP_FILES` değişkeninde durdu. Envanter komutu `set -u` olmadan tekrar çalıştırıldı; ROS_DISTRO, rclpy ve Gazebo sonuçları bu ikinci çalışmadan alındı. Sistem/ROS setup dosyaları değiştirilmedi.

## Windows → WSL localhost deneyi

WSL Python `http.server` ile yalnız `127.0.0.1` üzerinde boş port seçilerek tek istek alan geçici sunucu açıldı. Windows PowerShell'den `Invoke-WebRequest` çağrısı yapıldı.

- Son test portu: 46153.
- HTTP: 200.
- Gövde: `REDLINE_T0_NETWORK_OK`.
- Doğrulama komutu exit 0; sunucu tek isteğin ardından kapanarak exit 0 verdi.
- İlk denemede HTTP 200 ve doğru byte dizisi geldi; testin byte[]/string karşılaştırması hatalıydı. Content-Type ve UTF-8 çözümü eklenerek deney tekrarlandı ve geçti.
- Bu sonuç yalnız HTTP localhost erişimini gösterir; rosbridge/WebSocket, DDS, QoS veya gerçek ROS topic testi değildir. `.wslconfig` değiştirilmedi.

Windows TCP dinleyici kontrolünde 9090, 8765, 8080, 8081 ve 8082 portlarında dinleyici görülmedi. WSL tarafındaki tüm portların boş olduğu iddia edilmez.

## Açık işler / henüz test edilmedi

- T0: yeni venv, uygulama/ROS paketleri, `redline_msgs` derlemesi, pytest, colcon test ve CI.
- Yeni Unreal C++ proje/toolset/SDK build doğrulaması; oyun ve bridge Automation testleri.
- Rosbridge WebSocket ve ROS–Unreal dönüşüm/saat/tazelik sözleşmeleri.
- Mars ürünlerinin gerçek indirilmesi, CRS/label incelemesi, piksel hizalaması ve APXS koordinat anlamı.
- GIS venv bağımlılıkları ve GDAL ≥3.8.
- Ham BXW/YKB/RAD ürünleri bu aktarım paketinde sağlanmadı.
- Spek/araştırmadaki [?] maddeler kendi uygulama aşamasında küçük deneylerle doğrulanacak.

İlk aktarım anında kaynak verisi veya yeni uygulama olmadığı için pytest/colcon sonuçları üretilmedi ve T0 yeşil işaretlenmedi. Aşağıdaki tarihli T0 kaydı bu başlangıç durumundan sonra elde edildi.

## T0 — 14 Kasım 2026, 12:52 (+03:00)

Kullanıcının uygulama başlangıcı yönlendirmesiyle `docs/proje.md` §4/5/18 esas alınarak Python paketleri, ROS arayüz paketi, bootstrap/test script'leri ve CI sıfırdan yazıldı. [Yerel sonuç kaydı](verification/T0_LOCAL_2026-11-14.json) test raporlarının hash'lerini içerir.

| Gerçek kontrol | Sonuç |
|---|---|
| Saf Python pytest | 53 geçti, 0 hata/başarısız/atlanan; Python 3.12.3, pytest 8.3.5. |
| ROS arayüz build | Jazzy `colcon build` başarılı; 22 msg, 5 srv, 11 action. |
| Üretilmiş typesupport/CDR testleri | 98 geçti; pytest 7.4.4, sistem Python. |
| Colcon/CTest toplamı | 99 test (98 pytest + CTest wrapper), 0 hata/başarısız/atlanan. |
| Kaynak kopya kökeni | Snapshot ve güncel 42 ROS paket dosyasının SHA256 değerleri eşleşti; eski overlay kullanılmadı. |
| CLI kurulumu | Gerçek venv console entrypoint: `redline-data --version` → `redline-data 0.1.0`. |

İlk denemede ROS ortamının `PYTHONPATH` değeri saf venv'e `launch_testing` eklentisini sızdırdı; yaml import hatası nedeniyle test başlamadı. Saf pip/pytest çağrılarında ROS Python yolu temizlendi, pytest otomatik eklenti yüklemesi yalnız saf test çağrısında kapatıldı. ROS test ortamı bu ayarla değiştirilmedi.

İkinci denemede 50 saf test geçti; ROS configure işlemi Windows yolundaki `İ` karakterini keserek `rosidl_generate_interfaces.cmake:234` hatası verdi. Sistem ROS'u yamalamadan, kaynak hash'i doğrulanan yeni ASCII Linux workspace yoluna geçildi. Son testte eklenen UTC taşma regresyonlarıyla 53 saf test, ROS build ve 98 ROS arayüz testi geçti.

İlk GitHub CI koşusu [43582459866](https://github.com/ahmetefesensoy/redline/actions/runs/43582459866), `rosdep: error: no such option: --yes` nedeniyle bağımlılık adımında durdu. Yerel `rosdep install --help` ile desteklenen `-y` doğrulandı ve workflow düzeltildi. Yeni CI sonucu ayrıca kaydedilecek; bu ilk koşu yeşil değildir.

Sınır: Bu kanıt saf sözleşme testleri ve arayüz build/codec testleridir (ROS skill L1 ve build kısmı L2). Çalışan bir ROS düğümü/DDS grafiği, Gazebo görevi, Unreal köprüsü veya uçtan uca görev testi yapılmadı. T1 veri QA'sı ve T2 rota/altın testleri henüz yoktur.

## T1 — 14 Kasım 2026, 13:20 (+03:00)

Kullanıcının “GitHub'a dokunma, koda başla” yönlendirmesiyle yalnız yerel geliştirme yapıldı. Önceki CI sonucu bu aşamada sorgulanmadı, commit/push yapılmadı. [T1 çalışma kaydı](../journal/log/2026-11-14-t1-veri-hatti.md), [kaynak ön kontrolü](verification/T1_SOURCE_PROBE.md), [veri kaynakları](DATA_SOURCES.md).

| Kontrol | Gözlenen sonuç |
|---|---|
| Gerçek GIS venv | Python 3.12.3, NumPy 1.26.4, Rasterio 1.4.3 / GDAL 3.9.3, PyProj 3.7.1 / PROJ 9.5.1. Sistem ROS/Python değiştirilmedi. |
| Katalog | Gale HEAD 200, 3.868.256.546 bayt; ETag ve tarih kayıtlı; HTTP zamanı çekim zamanı sayılmıyor. |
| Pencere | Range 206, source WKT eşleşmesi, boyut/blok bütçesi; BXW 3.001 × 3.011; nodata %0. |
| ENU | cos(phi0)=0,9964855531857645; 1 m 3.000² ve 4 m 750²; local [-1500,1500] m; ikisinde nodata %0. |
| Orijin | E0=8.142.565,198776576 m; N0=−284.814,9215994864 m; H0=0 senaryo seçimi. Düşey datum doğrulanmadı. |
| Derive | 2/5 m eğim (derece), 2 m yarıçaplı düzlem-artığı RMS (metre). İkinci kayıtlı DTM yok; sigma rasterı üretilmedi. |
| 3 nokta sayısal QA | 1 m max fark 0,0000410851 m; 4 m max fark 0,0000565671 m; ≤0,1 m kapısı geçti. Bu sonuç gerçek arazi/feature hizası veya doğruluğu değildir. |
| Test | `bash scripts/test-data.sh`: 224 geçti, 0 hata/başarısız/atlanan; 9,66 s. |
| Raporlar | `test-results/data-run-1k6K8jYU/python.xml`; yerel HTML/PNG/histogram; 15 artifact hash'i `data/stac/BXW/run_manifest.json` içinde. |

İlk genişletilmiş testte 217 geçti, 3 başarısız: malformed WKT, PyProj `CRSError` fırlatıyor ve CLI'nin açık veri-hatası sözleşmesine dönüşmüyordu. `check_wkt` bunu `ValueError` olarak raporlayacak biçimde düzeltildi. Eklenen uçtan uca dizi/raster QA testleriyle son koşu 224/224 geçti. NaN/Inf-only pencerenin kabul edilmesi, hatalı TIFF header/range total'i ve integer olmayan okuma bütçesinin sınırı aşması regresyonları da düzeltildi.

İki pytest uyarısı, yalnız coğrafi referansı olmayan QA PNG yazma/okumada Rasterio `NotGeoreferencedWarning`; önizlemeler coğrafi veri değildir ve gerçek TIFF/sidecar yerine kullanılamaz. Bu uyarılar saklanmadı. DEM önizleme PNG'si görsel olarak da açıldı; nihai görüntü ölçek/datum/örnekleme bilgisi HTML başlığında yer alır.

**T1 tamamlanmadı:** Gale düşey datumunun ürün etiketi, ikinci DTM'nin eşkayıt/fark analizi, slope_sigma'nın birim/tanım kontrolü ve STAC Collection/Item + şema doğrulaması bekliyor. T2 algoritmalarına veya 3D tasarıma geçilmedi. Bu oturumda yeni ROS build gerektiren değişiklik yapılmadı; önceki 98 ROS testi yeniden çalıştırılmış gibi sunulmaz.

## T1 yerel kabul — 14 Kasım 2026, 13:44 (+03:00)

Önceki ara durumdan sonra §18 T1 zinciri tamamlandı. **`bash scripts/run-t1.sh` exit 0; sekiz kabul kapısı geçti.** [Günlük](../journal/log/2026-11-14-t1-kabul.md), [taşınabilir kabul JSON'u](../data/stac/BXW/t1-run-lfDo4ErT/t1_acceptance.json).

- **299 test**, hata/başarısız/atlanan 0; 14,27 s. XML `test-results/data-run-YzRRePjG/python.xml`. İki PNG georeference uyarısı öncekiyle aynı kapsamda.
- Gale v3 gerçek FGDC/TIFF yönlendirmesiyle **MOLA/metre** doğrulandı; exact areoid realizasyonu belirtilmiyor. [Metadata kanıtı](verification/T1_VERTICAL_DATUM.json).
- HiRISE özgün IMG→ARD üç noktada negatif/kesirli Float32 aktarımı geçti. Önceden tanımlı eşik 0,1 m; max artık 1,1778e−10 m hesaplama düzeyinde. Dört 206 isteği, 640.264 bayt; tam IMG/GDAL uzak okuması yok. [Aktarım kanıtı](verification/T1_HIRISE_TRANSFER.json).
- Göreli kayıt doğu −30,1927008 m, kuzey +30,4790131 m; medyan düşey ofset −14,4574189 m. Ayrı holdout RMSE 6,836075→1,509365 m. 20 m reddi kaydedildi; tanı taramasıyla gerekçeli çift-özel 80 m kullanıldı, genel varsayılan değişmedi.
- `slope_sigma.tif` derece cinsinden ampirik 5 m eğim farkı proxy'sidir. Bağımsız bir-sigma kalibrasyonu değildir; ortak kaynak/kontrol ve eksik kenar desteği maskeleri kayıtlı.
- Collection + **12 Item**, STAC 1.1.0/Projection 2.1.0/SSYS 1.1.1 resmi şemalarıyla çevrimdışı geçti. Hash sabitli şemalar/lisanslar; bilinmeyen ağ referansına izin yok. İşleme zamanı kayıtlı, çekim zamanı bilinmiyor.
- 39 artifact ve güncel kaynak/config/script hash'leri tekrar karşılaştırıldı; hata 0. Yerel HTML `data/derived/BXW/t1-run-lfDo4ErT/qa_BXW.html`; küçük kabul snapshot'ı `data/stac/BXW/t1-run-lfDo4ErT/t1_acceptance.json`.

Sınır yerel veri mühendisliğidir. Mutlak arazi/feature doğruluğu, bağımsız σ, Unreal/Gazebo eşlemesi ve uçtan uca görev tamamlandı sayılmaz. §6.2'nin T1 zinciri dışındaki horizon/skyview/rocks/env/engine export kabiliyetleri ayrıca eklenecek. T2 henüz başlamadı. GitHub/commit/push veya uzak CI sorgusu yapılmadı.

## T2 çekirdek — 14 Kasım 2026, 14:37 (+03:00)

Claude Code ile T2 uygulaması. [Günlük](../journal/log/2026-11-14-t2-cekirdek.md), [kararlar D008](DECISIONS.md). GitHub/commit/push yapılmadı.

| Kontrol | Gözlenen sonuç |
|---|---|
| Bağımlılık | `scripts/requirements-core.txt`: scipy 1.17.1, numba 0.68.1 / llvmlite 0.50.0, scikit-image 0.26.0, hypothesis 6.170.15, networkx 3.7, matplotlib 3.11.2; numpy 1.26.4 sabiti korundu; `pip check` temiz. Numba bu numpy ile derlendi (küçük njit denemesi). |
| `bash scripts/bootstrap.sh` | exit 0; yeni `requirements-core.txt` adımı dahil. |
| `bash scripts/test.sh` | exit 0. Saf Python **421 test** (redline_core 173 + redline_data 248), 0 başarısız/hata/atlanan, 17,20 s; `test-results/run-69Qk1lQ8/python.xml`. ROS: 5 paket derlendi, colcon **154 test**, 0 hata/başarısız/atlanan. Uyarılar: T1'den bilinen 2 Rasterio `NotGeoreferencedWarning`; 8 CMake "PYTHON_EXECUTABLE kullanılmadı" uyarısı (önceden var, `test.sh` argümanlarından). |
| TDD kanıtı | Uygulamadan önce 10 yeni test modülü, modüller olmadığı için toplanamadı (RED). Mutasyon: çekirdekte yokuş yukarı/aşağı enerji terimleri yer değiştirince 2 test, PET istasyon gücü %10 bozulunca 1 test düştü; geri alınca 169/169 geçti. Eşit tükenme testi düzeltmeden önce kayan nokta gürültüsüyle WATER seçtiğini gösterdi. |
| §7.14 altın testler | Düz düzlem `W = mesafe/v(0)` (16 temel yönde kesin, diğerlerinde ≤ %2,75 üstü); silindirik çukur `F = 1 − sin^(α+1) h`; eğimli düzlemde yokuş aşağı dönüş 46,41 s, yokuş yukarı 65,86 s; Golombek kapalı formu sayısal integralle < %1; 10×10 Dijkstra = networkx; darboğaz DP = kaba kuvvet (K=4, |C|=6, 10 tohum, mesafe eşitlik bozucu dahil); Hypothesis ile `W ≥ 0` ve Bellman/üçgen eşitsizliği; union-find bileşenleri = Dijkstra erişimi. eqc→ENU cos φ0 testi T1'in `redline_data/tests/test_enu.py` dosyasında. |
| Performans | `scripts/bench_walkback.py`, 750×750 @ 4 m, bütün hücreler erişilebilir: düz kararlı 0,839–0,847 s, pürüzlü/karışık durum 0,863–0,871 s; ilk çağrı 1,04 / 0,88 s (numba önbellek yükü). §7.5 hedefi (≤ 1 s) bu makinede (WSL2 Ubuntu 24.04, Python 3.12.3) sağlandı; pay %13–16, daha yavaş CI makinesinde aşılabilir. |
| BXW margin haritası | `scripts/t2_margin_map.py` → `data/derived/BXW/t2-run-20261114T113623Z/` (PNG SHA256 `b02c1c1d802b…d994`, `t2_summary.json`). Beş girdi dosyasının SHA256'sı T1 kabul manifestiyle (`54f6ab5b…4c90`) eşleşti. |
| Harita sonuçları | Yasaklı %38,9; kenar kurallarına göre 4.835 yürünebilir bileşen, en büyüğü 151.401 hücre (ızgaranın %27'si). İstenen habitat (0,0) 3 hücrelik cepteydi, 19 m kaydırılarak (18, −6) m'ye kondu. Bu bileşende walkback 0,24 s. W_ε medyanı 58,8 dk (p95 139,5). SCENARIO anlık görüntü (kalan = rezerv + 40 dk nominal tüketim): pay ≥ 0 alanı %4,76; kırmızı çizgi 1 dış + 630 delik halkası, net 0,465 km²; sarı (30 dk) net 0,0098 km². Sınırlayan O₂: bu senaryoda O₂, CO₂ ve su yapı gereği aynı anda tükeniyor. |

İlk harita koşusunda hücrelerin %99,9995'i erişilemezdi. Hata ayıklama: 4 m DEM ile 1 m DEM blok ortalaması arasındaki medyan fark −0,001 m; blok eğimi ile 4 m DEM gradyanı arasındaki korelasyon 0,989, satırlar ters çevrildiğinde −0,007. Yani yön/hizalama hatası yok. Yasakların %38,3'ü eğim + 1,645·σ kuralından (σ=0 iken %17,3). Habitat, katı köşe kuralı yüzünden 3 hücrelik bir cebe düşmüştü. Kural gevşetilmedi; `walkable_components` testle eklendi ve habitat en büyük bileşene kondu. Şeklin ilk çiziminde W_ε renk skalası `inf` yüzünden bozuktu, 630 küçük delik çizgileri gizliyordu; maskelendi ve 0,01 km² altındaki delik halkaları yalnız şekilden çıkarıldı (hücreler gri maskede). Son PNG açılıp gözle kontrol edildi.

Sınır: Parametreler SCENARIO; gün ışığı ve kaya terimi uygulanmadı; σ bağımsız 1σ değil; ROS düğümü, Unreal veya görev planı yok. Nominal metabolik güç 756 W, bunun 472 W'ı spekteki giysi ağırlık-dışı maliyeti; kalibrasyonu T12'de kontrol edilmeli. Spek §7'nin `orienteering`, `science_value`, `voi`, `localization_fix` modülleri sonraki taşlardadır.

## 3D görsel paket — 14 Kasım 2026

Kullanıcının açık üretim isteğiyle [15 varlık paketi](3D_ASSET_DELIVERY.md) hazırlandı. Blender 5.2.3 LTS ile master/GLB, FBX 7400 LOD0/1/2, PNG materyaller, sade OBJ ve basit collision proxy’leri üretildi. Robot/uygulama kodu değiştirilmedi.

- 15/15 master ve FBX/OBJ tekrar yükleme kontrolü geçti; NaN/Inf vertex yok. FBX max boyut farkı 2,3841858e-7 m; sade OBJ farkı 0,0117523 m. Bunlar dosya/geometri kontrolleridir.
- 1 m küp Blender FBX dönüşünde (1,000000119, 1,000000119, 1) m. X/Y/Z eksen okları ayrı teslimdir; iki motor içi ölçüm NOT_RUN.
- Rover 6, SEV 12 ayrı teker; drone 4 rotor grubu. 90° dönüşte pivot drift 0 m; gerçek vertex yer değiştirmesi ölçüldü. Motor joint binding ve uçuş/dinamik doğruluğu kabul edilmedi.
- Astronot 80 kemik, max 4 skin etkisi; FBX tekrar yüklemede idle/walk aksiyonları mevcut. Her klipte dört ayrı poz sonlu vertex üretti; önizlemeler ve ayrı animasyon FBX’leri teslimde. EV2 kaplamasında yüz/boyun UV alanı korunur.
- Tripo rover adayı yanlış teker düzeni nedeniyle asıl teslim seçilmedi. Native NASA rover kaynağının açılmış 180. pozu kullanıldı. Son görsel kontrolde parent bağlama sırasında montaj kayması bulundu; bağımsız parça dönüşümleri korunarak giderildi ve native kaynakla vertex karşılaştırması eklendi.
- İlk OBJ kontrol komutu dosyaya uygulanmayan ek bir importer eksen dönüşümü yaptı. Ham XYZ için Blender importer’ın +Y/Z bazını kullanarak kontrol tekrarlandı; kaynak OBJ eksenleri değiştirilmedi.
- Tripo drone’un önceki görev kimliği bağlı hesapta 404 döndü. 44 MB dosya yüklemesi /v3/files zaman aşımına uğradı; o aşamada görev/kredi oluşmadı. Korunan özgün GLB’den 55 bin üçgenlik türev hazırlanıp segmentation tamamlandı. 256 fragman 1 gövde/4 rotor grubuna alındı; kaynak UV’ler geri aktarıldı.
- Tripo görevi/parametre/prompt/gerçek harcama [CREDIT_LEDGER.json](../assets/CREDIT_LEDGER.json) içinde: 305 yeni kredi, 625 bakiye, frozen 0. Süreli indirme URL’leri ve API anahtarı kaydedilmedi.

[Makine raporu](../assets/verification.json), [manifest](../assets/MANIFEST.json), [kaynak ve sınırlar](../assets/README.md). Unreal/Gazebo import, 100 cm/1 m motor ölçümü, PBR/normal bağlantıları, collision/ingress, rig’in Unreal uyumu, Nav2, uçuş ve ROS köprüsü test edilmedi. Uygulama pytest/colcon testleri bu varlık-only değişiklik için tekrar çalıştırılmış gibi sunulmaz; kilometre taşı durumu değiştirilmedi.

Son rover karşılaştırması: 82 parça, native NASA kaynak geometrisi ile max vertex farkı 1,80477e-7 m; geçti. Son teslim manifesti 1.033 dosyada SHA256 doğrulandı, hash uyuşmazlığı ve kırık katalog bağlantısı yok.

## T3 arazi — 14 Kasım 2026, 15:10 (+03:00)

Kullanıcı T3'ü paralel, ardından gerçek ve görünür Mars yüzeyini istedi.
[Çalışma kaydı](../journal/log/2026-11-14-t3-arazi.md),
[paket/kullanım](T3_ARAZI_KULLANIMI.md),
[kanıt snapshot'ı](verification/T3_LOCAL_2026-11-14.json).

17 mesh / 3.003.000 üçgen; 1 km merkez 1 m, 3 km çevre 4 m. LRGB TIFF gerçek
Mars WKT, 0,25 m RGB/JPEG COG ve dahili maske ile doğrulandı. İki 4096² atlasın
geçerli oranı sağlayıcı maskesine göre %100. Görsel/collision geometri imzası
17/17 aynı; collision byte'ları korundu. Sayısal QA mutlak feature hizası değildir.

ROS build: 49 gerçek test + 7 CTest wrapper (56 toplam). Terrain/imagery/UV:
18 test. Hata/başarısız/atlanan yok. Gazebo 8.15.0 GUI'de dokulu yüzey gözle
görüldü; ogre2 D3D12/NVIDIA RTX 5080 logu alındı. Kamera, negatif Mars kotundaki
yüzeye bakar. Programatik Nav2 goal: status 4, fiziksel hareket 9,495 m, hedef
hatası 0,4995 m, z/zemin artık 0,00523 m. Lokalizasyon wheel/IMU EKF; ground
truth yalnız değerlendirmede. Beş gerçek sensör/odom akışı raporda.

Blender 5.2.3 LTS: 17/17 FBX roundtrip, max fark 0,244 mm. Unreal 5.8.4:
merkez karo + halka gerçek import, cm/örnek vertex ekseni/üçgen/UV/kayıtlı
PNG→BaseColor bağlantısı geçti. NullRHI, GPU render veya scene collision kabulü
değildir; smoothing uyarısı ve ilk kontrol hataları kayıtta korunur.

**T3 tam kabul değil:** RViz/WSLg görünüm/yakalama sorunu nedeniyle gerçek
RViz-click koşuları hedef almadan zaman aşımına uğradı. Başarılı programatik
goal, RViz hedefi diye sunulmadı. T4, drone/PR, görev costmap katmanı, insan
collision'ı ve nihai sanat/mikroayrıntı tamamlanmış değildir.

## T3 RViz kabul — 14 Kasım 2026, 16:00 (+03:00)

Önceki açık RViz kabulü yeni canlı koşuda geçti. `t3-runtime-rSbG87au`:
RViz `2D Goal Pose` aracıyla `(144,975, −299)` map hedefi verildi. C++ salt
gözlemci gerçek rmw publisher GID'sini `/rover_1/rviz_navigation` endpoint'iyle
eşledi; Python gözlemcisi yeni action UUID'sinin status 4 sonucunu aldı.
Fiziksel yer değiştirme **9,496287 m**, tıklanan hedefe hata **0,492101 m**,
zemin yüksekliği artığı **0,005242 m**; EKF hedef hatası 0,491310 m.
[Kabul kanıtı](verification/T3_RVIZ_ACCEPTANCE.json).

Jazzy rclpy callback metadata'sı dict olup publisher GID alanını taşımadığından
ilk doğrulayıcı hata verdi. C++ observer yalnız kanıt topic'i yayımlar; goal
topic'ine yayıncı eklemez ve robotu sürmez. İzole gerçek ROS entegrasyon testi
yanlış publisher reddini, gerçek GID/pose korunmasını ve bounded shutdown'ı
doğruladı. Son ROS build: 55 gerçek test case + 8 CTest wrapper = **63**, hata,
başarısız ve atlanan 0. İlk tıklama DPI/koordinat farkı nedeniyle 1 m kontrollü
hedef kapısının dışında kaldı ve doğru reddedildi; eşik değiştirilmedi.

Başarılı koşunun observer `ros2 run` wrapper'ı kapanışta bounded fallback ile
sonlandırıldı; bu ayrıntı kabul kaydında saklanır. Salt observer'ın doğrudan
binary kapanışı ayrıca test edildi. Bu kabul T3'ün §18 hedef sürüşüdür;
donanım kalibrasyonu, bütün arazi/engel kampanyası, drone, PR veya T4 köprüsü
tamamlandı anlamına gelmez.

## T3 teslim rover / engel denemesi — 14 Kasım 2026, 16:42 (+03:00)

Metre ölçeği ve altı teker pivotu teslim dosyalarından Gazebo/URDF'ye bağlandı.
Gerçek BXW programatik sürüşü geçti: 9,473051 m hareket, 0,503527 m fiziksel
hedef hatası, 0,015058 m z artığı (`t3-runtime-1qxHz434`). Son build
`t3-build-Sf5IGsTj`: 67 kayıt, 0 hata/başarısız/atlanan. Kontrollü yüksek
engelli koşu `t3-runtime-qjvsuibc` status 6 ile başarısız; engelden kaçınma
kanıtlanmadı. 3D zemin ayrımı ve gerçek süspansiyon/direksiyon açık.
[Ölçek/algı günlüğü](../journal/log/2026-11-14-t3-rover-olcek.md).
Kullanıcı isteğiyle WSL kapatıldı; çalışan dağıtım kalmadığı doğrulandı.

## T5 ROS ipliği — 14 Kasım 2026, 17:10 (+03:00)

Claude Code. Yalnız ROS/çekirdek tarafı; **T5 kabulü (Unreal'da çizgi ve pay dakikası görünür) yapılmadı.**

| Kontrol | Komut / kanıt | Gözlenen |
|---|---|---|
| Python | `pytest python/redline_core/tests python/redline_data/tests` → `test-results/t5-python.xml` | 495 geçti, 0 başarısız (2 uyarı T1 veri testinden) |
| T5 ROS paketleri | `bash scripts/build-t5.sh` → `test-results/t5-build-6iY9z9LY` | 4 paket, 13 test fonksiyonu; 0 hata/başarısız/atlanan |
| Planlama ızgarası | `scripts/export_planning_grid.py` | T1 hash'leri eşleşti; npz `c8e02a5116187606480c84eb8aec67a1cdf6ca759f200e04a036341bda60482b`; T2 sonuçları birebir |
| BXW performans | bkz. günlük | pay güncellemesi 11–14 ms (≤ 20 ms), anlık görüntü 42–52 ms, yeniden Dijkstra 0,29 s, karo 51 KB |
| BXW rosbridge koşusu | `bash scripts/run-t5-bxw.sh <ws>` → `test-results/t5-bxw-20261114T140630Z-T5_THREAD_BXW-0` | yakalama geçti; PET 60,01×; `margin_now` 234 → 90 dk; güvenli hücre 151 401 → 112 190; RedLine çerçevesi medyan 294 KB |

Doğrulanmayanlar: Unreal'ın FieldTile/RedLine ayrıştırması ve çizimi, gerçek Unreal istemcisinden poz yayını (koşuda SIMULATED rosbridge istemcisi kullanıldı), T4 kabulü, tam `scripts/test.sh` kapısı. Sözleşmeler [D009](DECISIONS.md), ayrıntı [T5 günlüğü](../journal/log/2026-11-14-t5-ros-iplik.md).

## T3 kontrollü engel ve teslim fizik profili — 14 Kasım 2026, 18:30 (+03:00)

`JS5gnQtK`: gerçek BXW ve teslim rover, varsayılan MPPI, tek komut sahibi;
status 4, fiziksel hedef hatası 0,446163 m, yer değiştirme 9,575615 m,
z artığı 0,052984 m. Örneklenmiş düzlemsel zarf açıklığı en az 0,688183 m;
1695 örnek, arada en büyük 8,704 s duvar-zamanı boşluğu var. Sürekli
çarpışmasızlık iddiası değildir. `UpMtpiHd` RPP karşılaştırması da geçti
(0,196552 m hata); kapanışta watchdog RuntimeError logu var.

`TiSy4OGe`: gerçek DEM, 2 fizik saniyesi yerleşme sonrası 8 s / 0,2 rad/s
komut; gerçek dönüş 1,507443 rad ve 0,026251 m merkez kayması. Pasif düşey
teker taşıyıcıları SCENARIO yedeğidir; rocker-bogie veya gerçek MSL tork/
sürtünme kalibrasyonu değildir. `y1iXPyWC`: 73 kayıt = 63 case + 10 CTest
wrapper, 0 hata/başarısız/atlanan. Ayrı test domain'i 78; canlı domain 77.

Oransal slowdown ile CLOSED_LOOP smoother etkileşimi gerçek düğüm testinde
ayırt edildi: mutlak 0,12 hız limitleri, eski 0,4 × 0,3 maksimumunu korur;
küçük komut küçülmez, Stop ve kaynak kaybı sıfırlar. `collision_limit`
entegrasyon testi bunu sınar. Plan kenarında 253'ün iki kez şişirilmesi,
metre yerine nokta sayısıyla bakış mesafesi ve yumuşatıcıdaki tam footprint
kesişimi düzeltilip regresyonları kaydedildi. Kabul eşikleri gevşetilmedi.

[Hash bağlantılı kabul](verification/T3_OBSTACLE_ACCEPTANCE.json),
[hareket grafiği](verification/T3_ROVER_OBSTACLE_TRAJECTORY.png),
[profil ve açık sınırlar](T3_ROVER_NAVIGASYON.md).
Yüksek tek test engeli, 3D düşük kaya algısı ve yeni RViz tıklama/görsel
kabulü değildir. COPY MODE yeniden görüldü. Gazebo -9/-11 kapanış kayıtları
korunur; faz başarısı temiz süreç kapanışıyla karıştırılmaz.

## T3 3D algı ve T4 son kabul — 14 Kasım 2026, 20:45 (+03:00)

T3 `rBwIyXYE` sabit alçak nesne kabulü: gerçek BXW collision üzerinde .4 m
SCENARIO kutu; 360×32 / 5 Hz ham bulut, 18/18 geçerli ayrım, en çok 5357
zemin noktası, 44 nesne dönüşü; eşzamanlı 2D geçerli dönüş 0. En uzun
sınıflandırma 66,768 ms. Algoritma yalnız gözlenen XYZ ve öz-gövde zarfı
kullanır; world-object listesi, DEM veya gerçek poz kullanmaz. İlk tek düzlem
sürümündeki kıvrımlı arazi işaretlemeleri sonrası gözlenen yerel yüzey
minimumlarıyla düzlem desteği eklendi; kıvrımlı sentetik zemin ve alçak
nesne regresyonu geçti. Kaynak snapshot/hash kaydı korunur.

Alçak engelli Nav2 `8O2IQ2ZF`, `vSXPwYoI`, `ayn453t9` koşuları başarısızdır.
Sonuncuda 124 geçerli segmentasyon / sıfır geçersiz kayıt ve 50 Hz joint
ölçüldü; rota kabulü geçmedi. Deneysel `--lidar-3d` varsayılanın yerine
geçirilmedi. Yüksek engelli varsayılan MPPI kabulü ayrı kalır.
`ehu2vkqW`: 76 ROS kayıt (65 case + 11 CTest wrapper), 0 hata/başarısız/
atlanan. Son core regresyonu 263 test geçti; önceki aynı gün koşusu eşzamanlı
başka çalışma tarafından değiştirilen planning testinde 1 başarısız içerir,
ham `t3-core-regression.xml` korunur, son `t3-core-regression-final.xml` yeşildir.
[3D algı özeti](verification/T3_3D_PERCEPTION.json),
[ölçülen noktalar](verification/T3_LIDAR_3D_RETURNS.png).

T4 §18 teknik kabulü son kaynak üzerinde geçti. `t4-build-final-guard.log`
Unreal build başarılı. `t4-automation-guard9093/index.json`: 9 başarılı,
0 hata/uyarı/atlanan. Gerçek izole ROS statik-cache çelişki/geç-abone testi
ve transport/poz kontrolleri: 4 geçti. Statik durum invalid/bozuk olduğunda
UE aktörü bağlantı boyunca kilitlenir; eski valid geçmişi kilidi açmaz.

Son canlı `5RZwQquS` yalnız sabit tam ROS/Gazebo/Nav2 grafiğidir; T4 hız/hedef
komutu göndermedi. 72 aynı fizik damgasında gerçek aktör karşılaştırması:
konum farkı <=6,50e-11 m, quaternion farkı <=1,52e-6 rad. Son kaynakla eski
canlı kayıt offline oynatıldığında 65 eşleşme geçti. 17 arazi parçası/
3.003.000 üçgenin 3 native UE collision izinin farkı en çok 0,022171 m.
Kaynak/build uyumu ve 18 kabul artifact hash'i doğrulandı.
[T4 kabul](verification/T4_ACCEPTANCE.json), [kullanım](T4_UNREAL_BRIDGE.md).

Sınırlar: gerçek UE aktörü NullRHI altında teknik küptür; final görsel/rig/UI
ve render kabulü değildir. Poz kıyası ROS tahminine göredir; bağımsız
konum doğruluğu değildir. Gazebo temiz kapanış sorunu ayrı açık kalır.
T4 ajanı kullanım sınırına takıldığından son invalidation guard, build,
otomasyon, canlı/replay doğrulaması ve kabul kaydı ana ajan tarafından bitirildi.


### 2026-11-14T17:53:24.976783+00:00 — RViz model incelemesi
Teslim rover parçaları, Orbit kamera ve canlı 3D LiDAR ile 1800 saniyelik hareketsiz inceleme açıldı. Hedef/komut gönderilmedi. Ground topic duvar zamanında yaklaşık 1,60–1,64 Hz gözlendi. WSLg WARN:COPY MODE nedeniyle ekran yakalama alttaki IDE penceresini döndürüyor; modelin ekranda göründüğü kabul edilmedi. RViz zemini ölçülmüş LiDAR noktalarıdır, dokulu arazi mesh gösterimi değildir. Kayıt: test-results/rviz-inspection.json; koşu: test-results/t3-runtime-M3lc8S9e. Supervisor özel RViz config ve en çok 1800 s hold destekler; Python derleme kontrolü ve canlı başlatma geçti.


### 2026-11-14T17:54:36.1401503Z — WSL yeniden başlatma ve RViz
Kullanıcının açık isteğiyle wsl --shutdown uygulandı ve aynı teslim rover + 3D LiDAR incelemesi yeniden açıldı. Koşu: test-results/t3-runtime-zLpRPAaD. WSLg pencere başlığında WARN:COPY MODE yok; CUA ekranında parçalı rover modeli, LiDAR zemin noktaları ve Global Status: Ok gerçekten görüldü. Görsel başlatma doğrulandı; yeni navigasyon kabulü yapılmadı. 1800 s hareketsiz inceleme, hedef gönderilmedi.



### 2026-11-14T17:55:39.9979171Z — Gazebo Mars yüzeyi görünümü
Kullanıcının isteğiyle mevcut redline partition / bxw sunucusuna yalnız GUI (gz sim -g) bağlandı; ikinci fizik sunucusu açılmadı. CUA ekranında dokulu 3D Mars yüzeyi gerçekten görüldü. RViz ayrı açık. Koşu test-results/t3-runtime-zLpRPAaD, GUI log gazebo-inspection.log. Bu gözlem görsel açılış kanıtıdır; yeni navigasyon kabulü değildir.



### 2026-11-14T18:13:51.7995711Z — Kullanıcı WSL kapatma ve yavaşlık geri bildirimi
Kullanıcı isteğiyle WSL kapatıldı; wsl --list --verbose Ubuntu-24.04 ve docker-desktop için Stopped gösterdi. Yeni ROS/Gazebo koşusu başlatılmadı. cUvE4GNZ koşusu sürüş kabulü değildir: hedef yollanmadı, yalnız ComputePathToPose SUCCEEDED; 40 s perception kaydında 130 scan ve sıfır cmd_vel_sim görüldü. Simülasyon/duvar saati oranı doğrudan ölçülmedi; yavaşlık kök nedeni ve performans düzeltmesi doğrulanmış sayılmaz. 3D profil önceki zLpRPAaD ComputePathToPose isteğinde error 208 ile başarısızdır. Son cPhb5OAW incelemesi kullanıcı shutdown isteğiyle kesildi; kabul sayılmadı. Yeni rviz_navigation_view.py yalnız map-frame tanılama kopyalarının kotunu değiştirir, Nav2 veri/komutlarını değiştirmez; iki mesaj koruma/reddetme testi geçti. Üç SCENARIO kutu cUvE4GNZ içinde oluşturuldu, yeni kapatılan dünyaya kalıcı aktarılmış sayılmaz. Unreal inceleme kamera betiği Python Rotator pitch/yaw sırasını keyword ile düzeltir; final malzeme/ışık tasarımı yapılmaz.



### 2026-11-14T18:15:51.9402829Z — Unreal inceleme kamerası doğrulandı
50788 PID ile açılan editörde -ExecCmds py üzerinden t4_focus_inspection.py çalıştı; viewport pozisyonu [14500,30300,-359000] cm, pitch=-30/yaw=-90/roll=0 derece geri okundu. CUA ekranında yakın gri 3D arazi ve işlem penceresinin kalktığı gerçekten görüldü. Unlit tanılama modu kullanıldı; 17 nesnenin ışık build uyarısı hâlâ mevcut, final malzemeler/aydınlatma/robot görsel kabulü yapılmadı. Kaynak varlık/map kaydedilmedi. -ExecutePythonScript otomatik çıkış ve keep-alive işlem penceresi denemeleri loglarda tarihsel kaldı; etkileşimli açılış için -ExecCmds kullanılmalı. WSL kapalı bırakıldı; performans/sürüş kabulü açık.


## T2 v2 kararları ve plan çekirdeği — 14 Kasım 2026, 22:30 (+03:00)

Claude Code. Kararlar [D010](DECISIONS.md), plan çekirdeği [D011](DECISIONS.md), ayrıntı [günlük](../journal/log/2026-11-14-t2-v2-plan-cekirdegi.md).

| Kontrol | Kanıt | Gözlenen |
|---|---|---|
| Python | `test-results/t2v2-python.xml` | 538 geçti (çekirdek 290, veri 248) |
| ROS | `test-results/t5-build-pAiG4PGh` | 22 test sonucu, 0 hata |
| Planlama ızgarası v2 | `bxw_planning_4m_v2.json` | npz `bf2a5f1a…`; yasak %28,9; σ eksik %0,53 (yalnız eğimi olmayan hücreler) |
| Habitat seçimi | `habitat_selection_v1.json` | 194 aday; (290, −454) m; 60 dk erişim 2,16 km² |
| v2 harita | `margin-v2-20261114T174827Z/summary.json` | 40 dk anlık görüntü güvenli oran 0,048 → 0,138 |
| T5 BXW koşusu | `t5-bxw-20261114T175411Z-T5_THREAD_BXW-0` | PET 120×; RedLine ≤ 111 KB; tick 68 ms |
| PlanEva BXW | geçici betik çıktısı (günlükte) | üç hedefte tam çözüme göre boşluk 0 |

Doğrulanmayanlar: Mars giysi modelinin bağımsız verisi, σ'nın yer gerçeği kalibrasyonu, Unreal tarafı.

## T6 SEP hattı — 14 Kasım 2026, 21:50 (+03:00)

Claude Code. Kararlar [D012](DECISIONS.md).

| Kontrol | Kanıt | Gözlenen |
|---|---|---|
| RAD [D] değerleri | `docs/verification/T6_RAD.json` | 9/9 geçti; ilk %25 alarmı gözlem 78 @ 05:21:50, arka plan 5,60 |
| Python | `test-results/t6-python.xml` | 550 geçti |
| ROS (art arda iki kez) | `scripts/build-t5.sh` | 27 test sonucu, 0 hata; S1 launch testi kararlı |
| Gerçek S1 BXW | `test-results/s1-bxw-20261114T184308Z-S1_SEP_4190-42/s1_summary.json` | alarm PET 6715 s, FR-04 0 s, abort 6,02 → 0,41 km², DEBRIEF |

Fark: spek sol 4190 için 186 gözlem / 93 doz bloğu diyor; PDS V00 dosyasında 258 / 129 var, kontrol edilen değerler eşleşiyor. Doğrulanmayanlar: Unreal'da alarm ve çizgi daralmasının görünürlüğü, SPICE gün ışığı, REMS.

## Unreal sunum müziği — 14 Kasım 2026, 23:59 (+03:00)

| Kontrol | Kanıt | Gözlenen |
|---|---|---|
| UE 5.8.4 C++ build | `scripts/build-t4.ps1` / `test-results/t4-build-source.json` | `RedlineMusicSubsystem`, ayarlar ve testler derlendi; exit 0 |
| MP3 → SoundWave | `scripts/import_redline_music.py` | take 01: stereo 59,62898 sn; take 02: stereo 62,41298 sn; iki varlık içerik doğrulamasından geçti |
| Faz yönlendirme, varlıklar ve çalışma zamanı | `test-results/redline-music-automation-v3/index.json` | 3 başarılı, 0 hata, 0 uyarı, 0 atlanan; gerçek game-type `UWorld` içinde sessiz oynatma bileşeni ve 1 → 2 → 1 geçişi |
| Kaynak bütünlüğü | `assets/audio/incoming/redline_sessiz_yorunge/generation.json` | MP3 SHA-256 ve Beatra artifact kimlikleri korunuyor; iki UAsset hash'i kayıtlı |

Otomasyon BRIEFING/PRECURSOR/TRAVERSE/STATION_SCIENCE/DEBRIEF → take 01,
CONTINGENCY/RETURN → take 02 eşlemesini; `DefaultGame.ini` soft asset yollarını;
55–65 sn süre aralığını ve looping'in kapalı olduğunu doğrular. Çalışma zamanı
testi Unreal ses aygıtı açıkken gerçek game-type `UWorld`/`UGameInstance` kurdu,
bridge üzerinden CONTINGENCY → RETURN → DEBRIEF mesajlarını geçirdi ve sessiz
oynatılan `UAudioComponent` üzerinde take 01 → take 02 → take 01 dizisini gözledi.
İşitsel loop dikişi, diyalog/alarm maskelemesi, final seviye ve canlı ROS ile tam
PIE koşusu henüz kabul edilmedi. Müzik yalnız Unreal sunumudur; ROS/Gazebo
yetkisini etkilemez.


### 2026-11-14T19:30:20.1571719Z — Unreal, RViz ve Gazebo birlikte açılış
Kullanıcının üç pencere isteğiyle mevcut xLDgQYDR fizik sunucusuna Gazebo GUI bağlandı, RViz navigation-inspection.rviz açıldı ve yükseklik tanılama adapter'ı başlatıldı. CUA ekranında Gazebo dokulu arazi/teslim rover/SCENARIO engeller ve RViz Global Status Ok/yeşil rota/LiDAR+costmap gerçekten görüldü. Unreal BXW_Autonomy_Showcase canlı fizik sunumuna bağlandı. Yeni hedef akışı test-results/rover-three-views-autonomy.json; ilk üç action status4, fizik hedef farkları ~0,42/0,85/0,84m; yüksek gerçek konum doğruluğu iddiası değildir. Önceki accelerated akış 12/12 aksiyon status4, kaydı korunuyor; zaman adımı .002 s ve hızlandırılmış BT yalnız SCENARIO gösterisi. Kum mikroyapı/teker rig/izler/hareketli engel işi hâlâ açık. Git/GitHub işlemi yapılmadı.


## T6 ortam durumu, gün ışığı ve FR-12 — 14 Kasım 2026, 22:45 (+03:00)

Claude Code. Kararlar [D014](DECISIONS.md).

| Kontrol | Kanıt | Gözlenen |
|---|---|---|
| SPICE tablosu | `docs/verification/T6_SPICE.json` | 3/3: LMST farkı ort. 39,7 s / en büyük 58,1 s (258 RAD damgası); öğle 70,13° az 180,15°; gün batımı 13:00:56 UTC |
| NAIF çekirdekleri | `scripts/build_sun_table.py` | Boş klasöre indirme, sabitlenmiş üç SHA256 ile eşleşti; mevcut çekirdeklerle rapor bayt bayt aynı |
| Python | `test-results/t6-python.xml` | 558 geçti |
| ROS (şimdi `redline_safety` dahil) | `test-results/t5-build-8h5oR782` | 37 test sonucu, 0 hata; `rule_monitor` 6/6, `walkback_field` 5/5 |
| Gerçek S1 + güneş tablosu | `test-results/s1-bxw-20261114T191044Z-S1_SEP_4190-42/s1_summary.json` | `/env/state` 330 mesaj, 1,000 s aralık; LMST 08:53:58 → 14:09:39; alarm/FR-04/alan D012 ile aynı |
| Gerçek S1, alacakaranlık sınırını geçen koşu | `test-results/s1-bxw-20261114T193408Z-S1_SEP_4190-42/s1_summary.json` | FR-12 INFO PET 32 458,6 s (beklenen 32 456,5 s); FR-01 kaydı yok; alarm boyunca alan 0,41 km²; son Güneş el −5,47° |

Düzeltme: önceki T5/T6 kayıtlarındaki ROS sayıları (27, 29, 30) `redline_safety` testlerini içermiyor; `build-t5.sh` varsayılan listesi bu paketi test etmiyordu. Doğrulanmayanlar: arazi ufku, REMS alanları, Unreal'da `/env/state` gösterimi (`WBP_SpaceWeather`).

## Rover görsel güncellemesi ve beyazlaşma — 14 Kasım 2026, 23:18 (+03:00)

Kullanıcı referans görselleriyle aşırı beyaz görüntüyü bildirdi. 5-lux kaynak
önizlemesinden 12.000 lux güneşe geçerken pozlamanın sabitlenmemesi hataydı.
`t4_prepare_atmosphere.py` artık kamera ve sınırsız PostProcessVolume için
manuel fiziksel pozlama kurar: ISO 100, f/4, 1/125 s, EV100 10,97, +0,6 telafi.
Yakın volumetrik sis kapalı; yükseklik sisi 100 m'den sonra başlar. Güneş,
dolgu ışığı, yansıma küpü ve mikro kum görünümü SCENARIO sanat parametreleridir;
T6 SPICE güneş tablosu bağlantısı henüz yapılmadı.

- Canlı CUA oyun görüntüsü, son pencere 17763670: turuncu gökyüzü ve görünür
  güneş, okunur rover gövdesi/tekerleri ve arazi gölgeleri; tam ekran beyazlaşma
  ve önceki eş-prioriteli yön ışığı uyarısı görünmedi. PNG dosyası dışa
  aktarılmadı; kanıt konuşmadaki CUA görüntüsüdür. Ara import `passed=true`
  sonuçları görüntü kabulü sayılmadı. Arada çok koyu kalan denemeler düzeltildi.
- `test-results/t4-build-look-final.log`: build exit 0. Son kaynak/derleme
  snapshot'ının 27 girdisi hash ile eşleşti. Sonraki değişiklikler görsel Python,
  içerik ve belgelerdir; C++ değişmedi.
- `test-results/t4-visual-automation/index.json`: 14 başarılı, 0 hata,
  0 uyarı, 0 atlanan (12 bridge, 2 müzik; 19:53 UTC koşusu).
- `test-results/visual-showcase-python-final.xml`: 7 geçti; fiziksel poz/frame
  reddi, engel yörüngesi, gerçek DDS manual gate ve RViz çizim kopyaları dahil.
- `data/engines/rover-live-parts-v1/verification.json`: mevcut master hash'i
  korundu; gövde + 6 teker FBX turu ve Unreal import birimleri kontrol edildi.
  30 önizleme UAsset/UMap dosyası kaynak projeye kopyalandı ve cache ile eşleşti.
- Fizik/kontrol yalnız ROS/Gazebo'da. Sunum odometrisi/teker ve hareketli nesne
  pozları Nav2/EKF girdisi değildir. En çok 800/90 s decal ve 2 cm shader
  çökmesi fiziksel kum/rocker-bogie doğrulaması değildir. Zaman tuşları yalnız
  kullanıcı tarafından istenen SCENARIO fizik hızını talep eder; PET değişmez.

QA: **SHIP WITH NOTES**, yalnız beyazlaşma düzeltmesi ve teknik önizleme için.
Final referans eşleşmesi **kabul edilmedi**: doğal kayalık sahne, yakın zemin
ayrıntısı ve atmosfer derinliği geliştirmeye açık. Yeni bir otonom sürüş kabulü
iddia edilmiyor: `atmosphere-moving-autonomy.json` ilk hedefi status 6 ile
bitirdi; fiziksel fark ~0,10 m olsa da tek-poz/hedef-hücre sınırı problemi açık.
T3'ün alçak 3D engelli tam sürüşü ve T5/T6 Unreal görev kabulü açık kalır.

Kaynaklar ve yeniden açılış: [ROVER_PREVIEW](ROVER_PREVIEW.md),
[hash/test kaydı](verification/T4_VISUAL_UPDATE.json),
[içerik kaynak notu](../unreal/Redline/Content/VisualShowcase/SOURCE.md).
Git/GitHub işlemi ve ücretli model üretimi yapılmadı. Unreal açık bırakıldı.

## EV1 oynanış, doku/animasyon onarımı ve T5 — 15 Kasım 2026, 01:19 (+03:00)

T5 §18 teknik kabulü gözlendi: gerçek Unreal EV1 yürüyüşü → ROS sarf/dönüş
alanı → canlı FieldTile/RedLine haritası ve pay dakikası. Kullanıcının siyah
kıyafet/animasyonsuz ve hareketsiz model geri bildirimi üzerine hatalar düzeltildi.
İlk import `passed` kayıtları yalnız süreç içi kontrolmüş: yeni süreçte iskelet
ve material slot null döndü. Bağımlılıklar açıkça kaydedildi; UE struct-array
kopyaları yerine güncellenmiş slot listesi atandı. Sonra geometri testi,
102,7778 mesh kök ölçeğine karşı animasyon kökünün 1 kalmasını yakaladı.
Kök anahtarları aynı mesh bind ölçeğine çevrildi; kaynak dosyalar değişmedi.

- `test-results/eva-final-build.log`: UE 5.8.4 build başarılı; güncel snapshot
  40 girdisi hash ile doğrulanır.
- `test-results/eva-final-automation/index.json`: 20 başarılı, 0 hata/uyarı.
  Tam suite iskelet/kök dönüşümü ve giriş düzeltmelerinden sonradır. Sonraki tek
  C++ değişiklik kullanıcıya görünen etkileşim mesajlarıdır; yeniden build geçti.
- `test-results/eva-repaired-animation-tests/index.json`: 5 EVA testi başarılı.
  Geometri: baş–ayak bağlama 151,840 cm; idle 151,949 cm; walk 150,675 cm.
  Bu kontrol önceki 1,46 cm küçülmeyi yakaladı; başarısız rapor silinmedi.
- `test-results/eva-intro-ros-build.log`: 39 ROS test kaydı, 0 hata/başarısız/
  atlanan. Yeni gerçek DDS Trigger testi, konum/tazelik reddini, saat başlangıç
  yanıtını, evre sırasını ve SEP önceliğini doğrular. Mevcut S1/T5 regresyonu geçti.
- `test-results/eva-intro-core.xml`: 14 geçti. `eva_intro.py` yalnız oryantasyon
  etkileşim sırasını/gates'i içerir; yeni bilim veya kaynak tüketim modeli yok.
- `test-results/eva-final-game.log`, `eva-final-unreal-pose.csv`: özgün dokularla
  insan ölçüsünde idle/walk, değişen foot_l pozları, yaklaşık 0,6 m/sn hareket;
  pozların medyan yayın aralığı 0,05 s. Tam sayılar T5_ACCEPTANCE.json'dadır.
- Canlı CUA pencere 4983490: açık renk/kırmızı detaylı kıyafet, doğru ölçekte
  animasyon, hareket, istasyon hedefi, pay ve harita görüldü. Önceki 2558580
  penceresinde E ile BRIEFING→TRAVERSE ve PET başlangıcı gözlendi. PNG dışa
  aktarılmadı; görüntü kanıtı konuşmadadır. Yeni harita/model içerikleri kaynak
  projeye taşındı ve önbellekle karşılaştırıldı.
- `test-results/eva-final-live/capture.json`: 6 topic geldi, hata yok. Kullanıcı
  pencereyi yakalama içinde kapattığından poz yayını bütün 35 s boyunca sürmüş
  sayılmaz; JSON bu kısa poz aralığını ayrıca gösterir. Önceki T5 canlı yakalama
  ve tam native poz kaydı korunur.

Habitat dışı/harita masası/bağlam istasyonu SCENARIO başlangıcıdır. E→servis
kabulü ardından gerçek MissionState beklenir; tam manuel istasyon–habitat
çevriminin görsel kabulü henüz yok. Nominal öncü keşif ve bilim ürünü değildir.
T6'nın tam S1 alarm/çizgi daralması görsel kabulü yapılmadı. Önceki
`t6-eva-live/capture.json`, alerts gelmediği için passed:false kaldı; başarılı
sayılmadı. WBP_SpaceWeather grafiği/ortam gösterimi ve REMS/ufuk açık.

[Oynanış](EVA_PLAYABLE.md), [T5 kabulü](verification/T5_ACCEPTANCE.json),
[D016](DECISIONS.md). Git/GitHub işlemi ve ücretli model üretimi yok.

15 Kasım 2026, 01:20 (+03:00): temiz başlangıç açıldı. CUA pencere 11273568'de dokulu EV1, animasyon, BRIEFING, PET 0, canlı harita ve pay görüldü. Backend test-results/eva-client-nB5WVuG5, hız 1x; otomatik probe kapalı. E onayı kullanıcıya bırakıldı.

## 15 Kasım 2026, 03:02 (+03:00) — Anlatı, koşu, iç mekân ve hedefler

UE 5.8.4 derlemesi geçti. `Redline.EVA`, `Redline.Prologue` ve `Redline.Music`
filtrelerinde 13 test başarılı: kaynak mesh/iskelet, ayak kökeni, saha katmanı,
RAD kaynağı, koordinatlar, koşu sınırları, birinci/üçüncü kişi, oturma geometrisi
ve tekrar üretimi, atlama/kontrol iadesi, müzik varlıkları ve gerçek subsystem
evre değişimleri. Yerel rapor: `test-results/firstperson-tests.stdout` ve ASCII
cache `firstperson-tests/index.json`. Headless testler işitsel kalite kabulü değildir.

`test-results/command-rooms-verification.json` kaydedilmiş haritada üç oda,
bağımsız kapılar, iki geçitli Tripo airlock, dört görev kamera çifti, canlı
ekran parametreleri, komuta içindeki PlayerStart, pozitif arazi açıklığı ve
dokuz sesin hash/süre/PCM denetimini geçirir. Model ölçekleri Unreal'da cm
olarak geri okundu; en büyük hata 0,001 cm'nin altında. Airlock'un kapalı
üretilen arka yaprağı yalnız türev mesh'te açıldı; ham SHA-256 korunuyor.

Sprint hesabı: 19 core ve 15 DDS kontrolü; taze altı paketli snapshot'ta ayrıca
16 installed-node/plan/launch testi geçti. `test-results/sprint-ros-LjcbbqV7/verification.json`
gerçek düğümden 3 m/sn senaryo parametresini okur. Planlayıcı yürüyüş modeli
değişmedi; hızlı hareket tüketimi açıkça SCENARIO extrapolation olarak tanılanır.
Doğrulanmış fiziksel Mars koşusu değildir. Mevcut yürüme klibinin oynatma hızı
hareket hızına uyar; ayrı artistik koşu klibi henüz yok.

CUA penceresinde birinci kişi, V ile üçüncü kişiye geçiş, 2,2 m/sn KOŞU,
Tripo airlock, hedef adı/metre/yön ve J görev günlüğü gözlendi. Native canlı
logda 2,47 m/sn'ye ulaşan gerçek karakter hızı ve devam eden pose yayını var
(`test-results/firstperson-live.log`). Bu değerler oyun hareketidir; robot
otoritesi veya bilim çıktısı değildir. Görev tahtasının Tripo duvarında
gömülü kaldığı görüldü; tam takım 1 m öne alınarak yeniden kaydedildi.

Chatterbox Multilingual V3 yerel RTX 5080 CUDA deneyi ve dokuz Türkçe klip
başarılı; her PCM kaynak sonlu ve tam ölçek kırpılmasız. Sesler oyun içinde
AudioComponent IsPlaying ile gözlendi. Kullanıcı ses çıkışı sorununu kendisi
çözdüğünü bildirdi; işletim sistemi ses ayarları değiştirilmedi. Mimik için
mevcut astronotta yüz kemikleri/blendshape yok, yüz animasyonu hazır sayılmaz.
Kaynak/lisans/kredi ve kontrol açıklaması: [NARRATIVE_PROLOGUE.md](NARRATIVE_PROLOGUE.md).

Bu işler T6/S1 alarmı, SpaceWeather, robot bilim kampanyası, basınç fiziği veya
nihai görsel kalite kabulü değildir. Git/GitHub işlemi yapılmadı.


## 15 Kasım 2026, 03:30 (+03:00) — Ayrı iç mekânların canlı kontrolü

Dinlenme modülünün kopyaları yerine Tripo komuta, laboratuvar ve koridoru
kullanıldı. İlk üretimler yeterli açıklık vermediğinden koridor bağlantıları ve
merkezdeki insan açıklığı UV'ler korunarak yalnız türevde düzeltildi. Ham
model hash'leri değişmedi. Laboratuvarın eksik merkez zemini düz güverteyle
tamamlandı; yeni mimaride query-only üçgen çarpışması var, rigid-body simülasyonu yok.
14 Unreal testi başarılı; InteriorQueryCollision testi kaynak mesh'i değiştirmeden
bağımsız türevde doğru çarpışma türünü ve tekrar hazırlamayı denetler.

Kaydedilmiş oda/ses denetimi geçti. Son CUA ekranında yeni komuta içi, canlı
harita, okunur görev duvarı, PET 0 / dönüş payı / O2 / su / pil ve birinci kişi
görünümü görüldü. Pano parlaması ışık şiddeti ve ışıktan bağımsız koyu yüzeyle
giderildi. Bu, bütün oda-koridor-yüzey güzergâhının kapsül/geçiş kabulü değildir;
topoloji örneklemesi REVIEW_REQUIRED kalan yerleri ayrıca raporlar.

Native content kaynak projeye kopyalandı. Ayrıntılı hash/kanıt durumu
`docs/verification/NARRATIVE_PREVIEW.json` içindedir; hâlâ PARTIAL_PREVIEW'dir.
Derleme kaynağı eşleşir; editörün cache'te yeniden oluşturduğu yerel AFS token
satırı ayrı işaretlenir, değeri rapora alınmaz. T6 veya bütün hikâye tamamlandı
sayılmaz. Git/GitHub'a dokunulmadı.

### 2026-11-15 07:53:45 +03:00 — Kullanıcı için hikâyeli EVA açılışı

Güncel kaynaklarla eşleşen UE derlemesi ve doğrulanmış ROS snapshot kullanılarak
BXW_ORIENTATION açıldı. Backend: test-results/eva-client-6jitoBdr; 1x,
3600 saniyelik oturum. CUA ekranında “Mars · Son alçalma” açılışı gerçekten
görüldü. UE logunda köprü bağlantısı, 11 abonelik, süren EV1 poz yayını ve
canlı saha/çizgi/pay alımı var. Otomatik görev ilerletme veya robot hedefi
verilmedi. Bu açılış yeni kilometre taşı kabulü değildir. Kanıt:
launch-observation.json. Git/GitHub işlemi yok.

### 2026-11-15 08:30 +03:00 — APXS hassasiyet modeli ve kırmızı çizginin bağladığı mesafe

**APXS (B1 kalibrasyonu).** `scripts/fetch_apxs_supplement.py` ile şu tablo indirildi: MSL APXS ekinin ds01 tablosu, sol 0–2301 (Berger vd. 2020, doi:10.1029/2020JE006536; ARCHIVE). CSV'nin SHA-256 değeri, 14 Kasım'da `research/notes/APXS_HEDEF_ON_KONTROL.json`'a yazılan pinle eşleşti.

Etikete göre hata sütunları "Precision Error"dır. 690 ölçüm kullanıldı; "Failed" hazırlıklı 22 satır atıldı. Hata için log-doğrusal bir model uyduruldu, değişkenler süre, bolluk ve standoff.

| Oksit | Süre üssü | Standoff (cm başına) | σ(1 sa)/σ(10 dk) |
|---|---|---|---|
| SiO₂ | -0,095 | +0,063 | 0,84 |
| FeO | -0,042 | +0,060 | 0,93 |
| Cr₂O₃ | -0,432 | +0,265 | 0,46 |

Spesifikasyondaki √t yasası (üs -0,5) 1 sa/10 dk oranını 0,41 öngörür. Uydurulan model 13 oksidin hepsinde bu yasadan daha düşük artıkla uyar.

Sonuç: simüle APXS ürünleri sayım yasasını değil, bu DERIVED modeli kullanmalı. Model dosyası `data/derived/instruments/apxs_precision_v1.json`, rapor `docs/verification/APXS_PRECISION.json`. Çalışma anı modülü `redline_core.apxs_precision`; kalibre aralığın dışında (540–41 657 s, standoff ≤ 5,6 cm) değer üretmeyi reddeder. Testler: 8 çekirdek, 4 veri testi. Python kapısı 650/650.

**Bölüm mesafesi.** `scripts/chapter_reach.py`, gerçek BXW ızgarasında (v2, 4 m) habitata riskli dönüş süresini (T_ε, z 1,645, σ_θ 0,2) ölçtü. FR-03'ün 20 dk sınırıyla karşılaştırma:

| Hedefler | T_ε | FR-03 boşluğu |
|---|---|---|
| Kampanya (`config/targets_BXW.yaml`, 16 m ve 31 m) | 0,6 ve 1,3 dk | 19,4 ve 18,7 dk |
| 12 planlama hedefi | 26,8–119 dk | (hepsi sınırı aşıyor) |

Kampanya hedeflerinde kırmızı çizgi bağlamıyor. 12 planlama hedefi ise SEP sırasında yasak bölgede kalıyor.

T_ε ≤ 20 dk olan yürünebilir alan 0,383 km²; D014'teki 0,41 km² ile tutarlı. 12–18 dk bandı habitata 280 / 356 / 454 m uzaklıkta (p10 / p50 / p90). Bu bandın yürüme süresi muhafazakâr modelde yaklaşık 9–13 dk. SCENARIO koşu sınırında (3 m/s) gerçek süre 2–3 dk. Rapor: `docs/verification/CHAPTER_REACH.json`.

**C1 bölümü.** `config/scenarios/C1_SOL4190_CHAPTER.yaml`: çıkış 05:10:00 UTC, ×1, EV1. Gerçek alarm (05:21:50, T6_RAD.json) PET 11,8 dk'ya düşer; doz verisi kaydırılmaz. Güneş 05:10'da 60,8° yüksekte (sun tablosu). Test: `test_scenario.py` 9/9.

Bu bir analiz ve senaryo dosyası. Canlı Unreal bölüm kabulü yapılmadı. Git/GitHub işlemi yok.

### 2026-11-15 09:46 +03:00 — Sonuç kontrollü EVA kampanyası

D017 uygulaması: 12 adımlı ayrı kampanya, gerçek EV1 poz/tazelik/revizyon
koruması, Nav2 varışı sonrası bilim, kalıcı ürün/kanıt/numune zinciri,
çift panelli kapılar, çömelme/numune sunumu ve büyük komuta konsolu.

Güncel ROS snapshot `dc2376c9106aee04…` (`campaign-build-weuApPL4`):
151 test, 0 hata/başarısız/atlanan. Son ek DDS/TF testi 1 ve scout koruma
testi 8 geçti. Görev/saha/bilim çekirdeği 30, koordinatör DDS testi 6 geçti;
bu sayılar farklı kapsamlar ve örtüşmeler içerir, tek toplama çevrilmez.
UE 5.8.4 derleme ve 20 native test geçti; üç test uyarılı başarılı.
Son kayıt `campaign-wall-final-ue-tests.json`.

`campaign-field-physical-post-recovery/verification.json`: BXW'de fiziksel
scout kalkış/tarama/dönüş/inişi ardından 12 adım tamamlandı; 7 ürün, 35 kanıt,
2 numune, Nav2 status4 ve 6,5878 m gerçek Gazebo rover hareketi. İnsanın
konumu açık SIMULATED fixture'ıydı. Aynı klasördeki uçuş izi doğrulaması:
1.088 gerçek ROS uçuş durumu, 69,48 s fizik uçuşu, evden en uzak 33,74 m,
yere yakın dönüş/iniş. Gözlemler SIMULATED truth adaptörüdür; algı sensörü
kabulü değildir. 14 JSON/XML ürün dosyasının hash'i ayrıca kaydedildi.

Önceki WSL 0x8007274c/eski odom başarısızlığı ve scout zaman aşımı kayıtları
korunur. Güncel koşunun fizik/duvar oranı yaklaşık 0,49×; gerçek zaman
performans hedefi kapatılmadı. Önceki ROS snapshot'ındaki diğer oturumun
giysi kaçağı testi hatası güncel kaynak snapshot'ında geçti; onun müzik,
kaçak veya APXS kodu değiştirilmedi.

CUA'da 12 görev konsolu, bileşim ±1σ grafiği, numune kökeni/analiz yeri ve
sonra yeni oturumun canlı brifingi görüldü. Dünya ekranının ters UV'si ve
parlaması kampanyaya özel unlit malzemeyle düzeltildi. Tam saha yürüyüşü,
numune animasyonunun bütün rotada görsel kabulü ve kapıların bütün bina
geçişleri henüz yapılmadı. Yeni kullanıcı koşusunda otomatik insan poz
fixture'ı yok; görevler brifingden başlar.

Kampanya kapanışındaki alt süreç sızıntısı düzeltildi. 10 s başlat–kapat
probe'unda kendi partition'ında açık süreç kalmadı. Bu kaynak temizliği
kabulüdür; çocuk ROS hata kayıtları nedeniyle tam temiz çocuk çıkışı ayrı
ve başarısızdır (`all_children_graceful=false`). Başka oturum kapatılmadı.

Kapsam, kaynak/ürün/test hash'leri ve açık işler:
`docs/verification/CAMPAIGN_PREVIEW.json`,
`journal/log/2026-11-15-oyunculu-kampanya.md`, `docs/CAMPAIGN_PLAYABLE.md`.
SIMULATED/UNCALIBRATED bilim, fiziksel kol/temas/sondaj, çok noktalı DAN,
aktif istasyon, tam T6/EV2/PR, OpenMCT ve elle kampanya kabulü hâlâ açıktır.
Hiçbir kilometre taşı kapatılmadı. Git/GitHub ve yeni model kredisi yok.

### 2026-11-15 10:10 +03:00 — T7 S4 kabulü (gerçek BXW): drone kanıtı → engelli hücre → plan v2

Koşu öncesi doğrulama:
- Tam ROS kapısı 115/115 (`ws-dc2376c9106aee04-9ar9njv0`, D019 değişiklikleriyle).
- Ağır işten önce WSL yeniden başlatıldı (09:15'teki bellek taşması ve servis hatası nedeniyle). Domain 86, port 9190.

S4 (`test-results/scn-bxw-20261115T065851Z-S4_BLOCKED_CORRIDOR-4/`):
- Drone koridor taraması yapıldı (D015 koridor kuralı).
- Rotada 16 engelli hücre bulundu: (259–262, 458–462), S4-BOULDERS gizli engeli.
- Planlayıcı 1424 kanıt kimliğini uyguladı. "replan after precursor" kararı bu kanıtlara dayanıyor.
- Plan v1 (T11, T01, T10, T05; en dar planlanan pay 58,6 dk) yerini plan v2'ye bıraktı (T05, T11, T01, T10; 64,3 dk).
- Çıkış v2 ile yapıldı. Dört istasyon gezildi, DEBRIEF PET 13 197 s'de.
- Kural ihlali yok; koşu boyunca en dar pay 83,1 dk.

S4c (`test-results/scn-bxw-20261115T055717Z-S4c_CLEAR_CORRIDOR-4/`), aynı tohumla karşı-olgu:
- Kanıt geldi, rota temiz; plan v1 korundu.
- DEBRIEF PET 13 734 s; ihlal yok; en dar pay 101,2 dk.

Sabahki ilk S4 koşusu kabul edilmedi. Görev PRECURSOR'da bekledi: D017 kanıt kapısı 4 deltayı göremedi. Sebep, cell_store'un her gözlemde tam anlık görüntü yayımlamasıydı; D019 ile düzeltildi.

Unreal'da drone sunumu ve canlı S4 kabulü bu kaydın kapsamında değil. Git/GitHub işlemi yok.

### 2026-11-15 10:25 +03:00 — S2 kabulü (gerçek BXW): telemetriden kaçak → eve dönüş, sınırlayan EV2/O₂

Tam ROS kapısı 116/116 (`ws-5dacf41d08de2c4c-hupd88fp`). Bu derleme D019'u ve ev_sim'in kısa CONTINGENCY düzeltmesini içeriyor. Koşu: domain 86 / 9190, başlangıçta 7,4 GB boş bellek.

S2 (`test-results/scn-bxw-20261115T070933Z-S2_SUIT_LEAK-2/`, `s2_acceptance.json`):
- EV2'de ×3 O₂ kaçağı PET 3000 s'de başladı. Telemetri oranı 1,000'dan 3,000'a çıktı.
- rule_monitor kaçağı PET 3036 s'de yakaladı (36,4 s; tutma süresi 30 s).
- mission_manager PET 3048 s'de CONTINGENCY'ye geçti ve ReturnToShelter'ı (EV1, EV2) başlattı. Mürettebat PET 6504 s'de içeride.
- Tespitten sonraki 355 sınırlayan kaydın hepsi EV2/O₂ (§17 S2 ölçütü).
- Yayımlanan pay kayıtlı telemetriden bağımsız olarak yeniden hesaplandı: (O₂ − rezerv − k·ihtiyaç) / O₂ hızı. Telemetrinin sabit olduğu 297 örnekte fark en fazla 0,20 dk. Bütün örneklerde ortanca 1,7×10⁻⁶ dk; yürürken ve giriş anında fark eşleştirme gecikmesinden geliyor.
- FR-01, FR-04 ve FR-12 korundu; tespitten sonra en düşük pay +17,3 dk.
- Beklenen kural sonuçlarının hepsi tuttu (`summary.json`).

Düzeltmeden önceki ilk koşu (`scn-bxw-20261115T065138Z-S2_SUIT_LEAK-2/`, `s2_acceptance_run1.json`) kabul edilmedi. Tespit ve sınırlayan kayıtlar doğruydu, ama ev_sim acil dönüşü kaçırdı: pay −93,6 dk'ya indi ve FR-01 ihlal edildi. Bu kayıt başarı olarak kullanılmaz. Git/GitHub işlemi yok.

### 2026-11-15 10:25 +03:00 — Pasif RViz, robot haritası, animasyon geçişi ve ilk toz

UE5.8.4 build campaign-motion-dust-final-build.log ve 27 native test geçti
(üç uyarılı başarı). 22 Python observer/config/guard testi geçti. Robot
konsolu gerçek fizik izi/Nav2 planı/hız/tazelik, native idle-walk harmanlama
ve 96 elemanlı ilk terrain-temas tozu katmanı eklendi. Bunlar son kum kalitesi,
koşu klibi, fiziksel zemin veya uzun rota kabulü değildir.

D3D12 glxinfo RTX5080/accelerated=yes; CUA'da aynı graph RViz rover modeli,
costmap/footprint ve Global Status Ok görüldü. RViz GLSL başlangıç link hatası
ve yeni WSLg WARN:COPY MODE başlığı korunur; bütün katmanlar veya capture yolu
çözüldü sayılmaz. İlk 5sCXM8p0 Nav2 lifecycle timeout başarısız koşusu korundu;
yeni domain145 KNsxhu6O'da managed nodes active görüldü. Fizik/duvar ~0,48×.

Canlı Unreal robot panelinde güncel poz/hız ve henüz bulunmayan Nav2 planı
doğru gösterildi. Oyunculu oturumda scout COMPLETE ve 28 SIMULATED kanıtla
saha kararı açıldı. Otomatik test hedefi/insan fixture'ı gönderilmedi. Yeni
kısa sürüş test harness'i aktif kullanıcı nedeniyle çalıştırılmadı; bu yüzden
yeni panelde hareketli sürüş ve toz yakın plan kabulü açık. Kaynak/hash/sınırlar:
docs/verification/CAMPAIGN_OBSERVABILITY_AND_MOTION.json.
Ayrıntı: journal/log/2026-11-15-izleme-hareket-toz.md.
Müzik/APXS/kaçak ve Git/GitHub'a dokunulmadı; yeni model kredisi yok.

### 2026-11-15 11:30 +03:00 — Bilim kampanyası yerleri, tablet atlası, 1 m yüzey v2

- **Kampanya** (`config/science_campaign_BXW.yaml`, D020). Yedi istasyon tanımlandı. Doğuda 2 kontrol, batıda 3 test istasyonu var; uzak batı yalnız robot için. Habitat önü ve laboratuvar altyapı istasyonu. Görevler: B1, B2, B3, B4, B5, B6, B7, B10, laboratuvar analizi ve drone keşfi.
  - `redline_core.science_campaign` doğrulayıcısı ve 10 test eklendi. Önce kırmızı koşuldu (modül yoktu). Gerçek BXW kampanyası da test ediliyor.
- **Tablet atlası** (`scripts/build_tablet_atlas.py`, 12 s). 2048 piksellik 6 katman ve `manifest.json` üretildi. Bütün istasyonlar yürünebilir zeminde (eğim 4,9–10,5°).
  - Habitattan dönüş süreleri, T_ε: ST-E1 27 dk, ST-W1 33 dk, ST-E2 52 dk, ST-W2 90 dk, ST-W3 116 dk.
  - Yalnız habitat önü 20 dakikalık SEP sınırının içinde. Önizlemeler `docs/verification/TABLET_ATLAS_PREVIEW_{safety,science}.png`.
  - İlk sürümde bilim birimleri (±0,3 m) ve >60 dk dolgusu haritayı kapatıyordu. Eşik ±1 m'ye çekildi, dönüş süresi kontura çevrildi.
- **Yüzey v2** (`data/engines/BXW/surface-v2-1m`). Mevcut `export_t3_terrain.py` değiştirilmeden `--ops-size 2750 --max-triangles 17000000` ile çalıştırıldı.
  - Sonuç: 121 karo ve dış halka, 15,3 M üçgen, 1,2 GB. Süre 1 dk 58 s, en fazla 1,36 GB bellek.
  - Üç noktalı yükseklik testi geçti (DEM farkı ≤ 2 cm). Yedi istasyon da 1 m bölgede.
  - Unreal'a alınmadı.
- Tripo üretimi yapılmadı: anahtar yok.

Git/GitHub işlemi yok.

### 2026-11-15 12:20 +03:00 — "Nasıl çalışır" anlatım videoları (matkap, APXS, LIBS)

`assets/production/explainer_videos.py`, Blender 5.2 EEVEE, Windows, RTX 5080. Çıktılar `assets/explainers/{drill,apxs,libs}/`: MP4, poster, TR/EN SRT, `explainer.json`.

| Video | Süre ve biçim | Çizim süresi |
|---|---|---|
| drill (B5) | 25,0 s, 1920×1080, 750 kare, H.264 | 219 s |
| apxs (B1) | 24,0 s, 720 kare | 232 s |
| libs (B2) | 24,0 s, 720 kare | 235 s |

Süre ve çözünürlük ffprobe ile doğrulandı. Her videodan beş karelik bir kontrol sayfası çıkarılıp gözle incelendi:
- Matkap ucu kayaya giriyor; derinlik, tork ve mod hikâyeyle birlikte değişiyor.
- APXS'te ± değerleri D018 modelinden geliyor: SiO₂ hatası 2 cm boşluk ve 10 dk'da ±0,79, temasta ±0,71, 60 dk'da ±0,60.
- LIBS'te ışın yalnız atış anında görünüyor, adaylar sarı, hedef camgöbeği halkalı. Spektrum çizgileri NIST dalga boyları.

Deneme karelerinde bulunan ve düzeltilen hatalar günlükte. Videolar sunumdur; Unreal içeriğine dokunulmadı. Git/GitHub işlemi yok.

### 2026-11-15 13:50 +03:00 — Space Apps iddia defteri, C1 gerçek zamanlı fırtına bölümü, duyarlılık, kum malzemesi

Claude Code. Kullanıcının Space Apps sunum isteği ([plan](SPACE_APPS_SUNUM_PLANI.md)).

- **Kum/ayak izi malzemeleri.** 11:39 koşusunun "Failed to compile" uyarıları düğüm bağlanırken araya giren
  derlemelerdi. Temiz editörde yeniden derlemede hata yok. Bütün Custom girişleri bağlı. Kum 673, ayak izi
  decal'ı 297 piksel komutu (lastik izi 293). FPS ölçülmedi. Malzemeler yalnız T4Build snapshot'ında;
  depoya kopyalanmadı.
- **İddia defteri.** `scripts/space_apps_claims.py` + `config/space_apps_claims.yaml` →
  `verification/SPACE_APPS_CLAIMS.json`. Her slayt iddiası kanıt dosyasındaki alanlarla karşılaştırılır.
  Testler 5/5 (önce RED görüldü). Sonuç: 11 iddia PASS; "Unreal'da canlı fırtına" NOT YET. Defter bir
  hatamı yakaladı: APXS aralığını önce %7–18 yazmıştım; altı ana oksitte doğrusu %7–29.
- **Işık süresi.** `scripts/light_time_sol4190.py`: alarm anında Dünya–Mars tek yön 15,84 dk, gidiş-dönüş
  31,67 dk (de440s barycentre). C1 backend'inin `env_server` değeri (950 s) bağımsız olarak aynı.
- **C1 gerçek zamanlı (×1), simüle yürüyücü.** `test-results/c1-bxw-20261115T101234Z-C1_SOL4190_CHAPTER-42/`:
  - Gerçek RAD E alarmı PET 710 s'de (05:21:50 UTC) geldi; FR-04 0 s.
  - Güvenli alan 6,02 → 0,41 km² oldu; DEBRIEF PET 1190 s'de (alarmdan 8 dk sonra).
  - FR-01 ihlali yok. Capture `passed:true`.
  - EV1 SIMULATED istemcidir; Unreal canlı kabulü değildir.
- **Unreal bağlantı hatası (canlı denemeden önce bulundu).** Senaryo launch'ı rosbridge'i yalnız 127.0.0.1'de
  açıyor; Unreal WSL IP'sine bağlanır. `run-c1-live.sh` Unreal modunda rosbridge'i, `run-eva-client-backend.sh`
  gibi ayrı olarak WSL adresinde (`url_path:=/+`) açar. `scripts/start-c1-live.ps1 -BackendOnly` ile Windows'tan
  172.23.20.142:9190 bağlantısı ve capture aboneliği gözlendi; deneme backend'i durduruldu. Oyunla canlı koşu
  yapılmadı.
- **Duyarlılık (T12 alt kümesi).** `scripts/sensitivity_redline.py` → `verification/SENSITIVITY.json`.
  - Fırtına modunda güvenli alan 0,383 km². Parametreler tek tek oynatıldı.
  - Uyarı sınırı 15/30 dk: 0,250/0,825 km².
  - Robotun görmediği arazide hız çarpanı 0,6/0,85: 0,306/0,539 km².
  - Yürüme hızı 5/7 km/sa: 0,293/0,499 km².
  - σθ 0,1/0,3: 0,479/0,322 km².
  - Eğim sınırı 20/30°: 0,327/0,424 km².
  - z 1,282/2,326: 0,422/0,330 km².
  - Yerel duyarlılık; doğrulama değildir. Testler 2/2 (önce RED).
- **Figürler.** `scripts/space_apps_figures.py` → `docs/figures/space_apps/` (RAD fırtınası, APXS, duyarlılık).
  Doğrulanmış iki renkli palet; çakışma gözle kontrol edildi.
- **Testler.** Python 700/700 (`test-results/space-apps-python.xml`). ROS kapısı bu kayıtta yeniden koşulmadı.

Git/GitHub işlemi yok.

### 2026-11-15 14:30 +03:00 — Ham çekimler

12 kaynak MP4 ffprobe ile doğrulandı; yeni açılış, habitat içi deney,
rover/RViz ve C1 kayıt oynatımı ayrı saklandı. Final montaj ertelendi.
Kaynak/sınırlar: docs/verification/RAW_VIDEO_2026-11-15.md ve
journal/log/2026-11-15-ham-cekim.md. Rover hedefi süre sınırında iptal edildi;
hedefe varış kabulü yok. Düz zemin drone testi geçti; BXW çekimi açık.

### 2026-11-15 16:16 +03:00 — V8 video çıktısı

`outputs/submission/REDLINE_30s_v8.mp4` yeniden üretildi ve final dosyası
kontrol edildi: 30,000 sn, 900 kare, 1920×1080, 30 fps, H.264; AAC stereo
48 kHz. Tam decode hata kaydı boş. Ses örnek tepesi −5,3 dBFS; bu ölçüm
bağımsız dinleme veya ses oyunculuğu kabulü değildir. Nihai karelerde alt
satır çakışması düzeltildi. 11 çıktı/kaynak bütünlüğü kontrolü geçti:
`outputs/submission/render/v8-assets/verification.json`.

V7 SHA-256 korundu; bilim CSV'sinin 31 satırı ve uç değerleri değişmedi.
Farklı koşudan gelen `same run` inset'i kaldırıldı; 32 dakika iletişim
süresi gidiş-dönüş olarak açıklandı. Drone mevcut SURVEY kaydıdır; yeni
stabilize uçuş, eşzamanlı üç motor kaydı, rover hedefe varış veya tam
kampanya kabulü iddia edilmez. Kaynak ve sınırlar:
`outputs/submission/CREDITS_AND_AI.md`, `journal/log/2026-11-15-video-v8.md`.

### 2026-11-15 16:22 +03:00 — ARIADNE V9 isim düzeltmesi

Kullanıcının bildirdiği kamuya dönük proje adı ARIADNE olarak kaydedildi.
`outputs/submission/ARIADNE_30s_v9.mp4` kapanış karesi final MP4'ten çıkarılıp
ARIADNE olarak gözle doğrulandı. 10 kontrol geçti: proje adı, 30 sn, 900 kare,
1080p30, 48 kHz stereo AAC, tam decode hatasız, V8 ile aynı timeline ve
ses miks hash'i, V8 korunması ve V9 çıktı hash'i.
Kanıt: `outputs/submission/render/v9-assets/verification.json`.
SHA-256: `9b9c73cfc46b683d32860e2ddb8b87e8c239c04b557af3c9a585781362e66587`.
Teslim belgeleri ve README başlığı güncellendi; teknik ROS/kod isimleri
ve geçmiş kayıtlar yeniden adlandırılmadı. Yeni özellik kabulü değildir.
