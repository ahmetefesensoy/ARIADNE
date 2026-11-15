# Bilim ve numune işlemleri

15 Kasım 2026 · `redline_science` yerel simülasyon prototipi.

Her başarılı işlem kalıcı JSON ve PDS4 benzeri XML etiket, `InstrumentProduct`
ve `EvidenceRecord` yazar. Numune alma ayrıca ara durumları ve kalıcı
`SampleRecord` üretir. Eylemin kabul edilmesi görevin tamamlanması değildir.

Bu backend açık `SCENARIO` hedeflerden `SIMULATED` ürün üretir.
`config/targets_BXW.yaml` içindeki kimya, sertlik, WEH ve gürültü sayıları
yazılmış senaryo girdileridir; NASA ölçümü veya kalibre edilmiş cihaz değildir.
APXS arşiv koordinatlarının anlamı bu prototipte genellenmez.

## Başlatma ve sınırlar

`science_instruments` bir lifecycle node'dur. Önce configure, sonra activate
gerekir. `auto_activate:=true` yalnız açık `simulated_backend:=true` ve
`physical_mode:=false` ile kullanılabilir. Fiziksel mod, temas/kuvvet/kinematik
kanıtı bulunmadığı için etkinleşmez. Bu node hız, eklem, TF veya robot odometrisi
yayımlamaz. Tek düğümdeki ortak lifecycle bütün simülasyon cihazlarını kapsar;
ayrı fiziksel cihaz lifecycle'ları henüz uygulanmadı.

Gerekli parametreler `targets_file`, `products_dir`, `run_id`.
`products_dir/<run_id>/` ürünleri ve tekrar korumasını tutar.
`operation_duration_s` sunumun duvar saati süresidir (varsayılan 8 s);
`integration_s` ayrı ölçüm modeli parametresidir. Bu node görev/PET saatini
değiştirmez. Cihaz güçleri açık senaryo bütçeleridir; donanım ölçümü değildir.

Pozlar `map` ENU/metre olmalı, son alımı varsayılan 2 s'den yeni olmalı.
EV1/EV2 `/crew/<id>/pose` ile; robot yalnız
`/redline/science/rover_pose` (`PoseStamped`) ile alınır. ROS/Gazebo adaptörü
robot pozunu TF ile `map`'e dönüştürmelidir. Robot pozu bulunmadığında robot
işlemleri reddedilir. `ContactScience.instrument=EV1_XRF` açıkça EV1 pozunu
kullanır. LIBS menzili 7 m; diğer hedef işlemleri 4 m senaryo etkileşim
menzilidir. Bu değerler 2 cm fiziksel temas doğrulaması değildir.

| Action | Uç nokta | Ürün / davranış |
|---|---|---|
| CollectSample | `/redline/science/collect_sample` | Seçim → erişim provası → hazırlık → toplama → alındı → kapta. El ile fiziksel kaya yakalama kanıtı değildir. |
| ContactScience | `/rover_1/contact_science` | APXS veya EV1_XRF senaryo bileşimi ve hata çubukları. Gerçek temas açısı bilinmediği için sonuçta NaN. |
| RemoteLibs | `/rover_1/remote_libs` | Boş hedefte erişilebilir en yakın kayıt seçilir; sınırlı raster provası ve bileşim ürünü. Kamera segmentasyonu henüz yok. |
| NeutronSurvey | `/rover_1/neutron_survey` | Erişilen tek noktada WEH ve 9×9 GP posterior. `max_points=1`; otonom çok noktalı sürüş/adaptif seçim henüz yok. Hedef verilen poligon içinde olmalı. |
| Drill | `/rover_1/drill` | Senaryo sertliğine göre stall/geri çekme/kuvvet azaltma/perküsif toparlama ve ACQUIRED numune. Gazebo kuvvet sensörü doğrulaması değildir. |
| CacheSample | `/redline/science/cache_sample` | ACQUIRED/STOWED numuneyi kapla eşler ve laboratuvar pozunda RECORDED yapar. |
| DeployStation | `/redline/science/deploy_station` | WEATHER/DOSIMETER yerleştirme kaydı. Aktif istasyon hava/doz zaman serisi henüz yok; değer uydurulmaz. |

Numune kökeni her zaman ilk `origin_point`'tir. Laboratuvar teslimi yalnız
`analysis_point`'i günceller. Kapta başka numune varsa işlem reddedilir.
Kabul edilmiş request kimlikleri dosyada tutulur; yeniden başlatmada aynı
istek ikinci kez yürütülmez. Başarısız veya iptal edilen toplama başarı ürünü
yazmaz. Yeni deneme yeni request kimliği ister.

## Yayınlar

- `/redline/science/products`: `InstrumentProduct`, reliable/transient-local.
  `summary_json`: `request_id`, `labels`, `values`, `sigma`, `unit`,
  `noise_calibration`, `seed`, `input_ids`, `limitation`, `status` ve varsa
  `sample` veya `posterior_grid`.
- `/redline/evidence`: reliable olay; ürün kimliği provenance'ta bulunur.
  Kalibrasyon olmadığı için evidence `quality=0` kullanır.
- `/redline/science/samples`: numune durumları, iki ayrı konum ve evidence zinciri.
- `/redline/science/fields`: DAN için küçük `ScalarField`.
- `/redline/science/status`: sınırlandırılmış JSON; current `request_id`, actor,
  instrument, target, phase, progress, wall elapsed ve açık simülasyon etiketi.
- `/power/<instrument>`: `Float32`, W; çalışma sırasında senaryo gücü,
  bitiş/iptal/hata sonunda sıfır.

XML etiket PDS4'e benzer metadatadır; PDS4 şema doğrulaması veya NASA ürünü
iddia edilmez. JSON SHA-256 XML içine yazılır. Analiz ürününün girdilerinde
önceki toplama evidence kimliği korunur.

## Doğrulama

`test-results/science-operations-core.xml`: **15 core testi geçti**.
`test-results/t5-build-no1ZtMcb`: taze snapshot build ve **8 gerçek DDS/action
testi geçti**; ament sarmalayıcıyla raporlanan toplam 9'dur.

DDS kontrolü toplama → kapta → 20 m ötede laboratuvar teslimi → RECORDED
zincirini, origin/analysis ayrımını, tekrar/kap/poz/menzil/lifecycle/güç
korumalarını, iptal ve poz eskimesini; ayrıca LIBS, XRF, DAN alanı, sondaj
stall toparlaması ve istasyon ürünlerini kapsar. Bu sonuç T8/T10'un fiziksel
sensör, MoveIt, çok noktalı otonomi veya tam bilim kabulünü kapatmaz.
