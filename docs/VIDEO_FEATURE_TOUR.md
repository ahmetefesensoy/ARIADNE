# REDLINE — ayrı oyun içi çekimler

15 Kasım 2026 · Kullanıcı videoları daha sonra birleştirecek. Her çekim ayrı
MP4 olarak teslim edilir; tek kesintisiz, bütünü tamamlanmış EVA iddiası yoktur.
Görüntüler Unreal oyun viewport'undan alınır. Masaüstü, mikrofon veya başka
pencereler kayda girmez. Aşağıdaki görev çekimleri betikli SCENARIO sunumdur;
canlı ROS işlemi yürütmez. Canlı ROS ürün kaydı ve video sunumu ayrı kanıtlardır.

## Teslim edilen dosyalar — 13:31 (+03:00)

Hepsi `outputs/feature-videos/` altında ayrı H.264/AAC MP4, 1280×720 ve gerçek
kare zamanlarıyla VFR'dir. Sayı atlamaları çekim planının kimlikleridir.

| Dosya | Süre | Gerçek kare | Kaynak / müzik |
|---|---:|---:|---|
| `01_acilis.mp4` | 59,782 s | 1001 | Unreal anlatı sahnesi; özgün VO/Foley/caz ve take 01 ile düzenlenmiş ses |
| `03_numune.mp4` | 27,995 s | 444 | Betikli numune/tüp/kapak sunumu; take 01 |
| `04_xrf.mp4` | 27,997 s | 443 | Betikli XRF sunumu; take 01 |
| `05_istasyon.mp4` | 27,966 s | 433 | Betikli istasyon sunumu; take 01 |
| `06_sondaj_v2.mp4` | 27,993 s | 422 | Rover yanında ayrı kaynak parçalarıyla dönen Tripo uç, iyileştirilmiş ışık; take 02 |
| `07_laboratuvar_ph.mp4` | 28,005 s | 457 | Dik ve tam görünen pH/iletkenlik grafikleri, önceki kayıtlı WCL_SCENARIO ürünü; take 01 |
| `08_numune_teslimi.mp4` | 27,984 s | 445 | Betikli teslim sunumu; take 02 |

`verification.json`, ffprobe ile görüntü/ses süresi ve kodekleri, decoded AAC
üzerinden `volumedetect` ile sıfır olmayan sesi doğrular. Ortalama sesler
−25,1…−35,3 dBFS, en yüksek sesler −3,7…−19,5 dBFS'dir; bunlar duyulduğuna
dair kullanıcı onayı veya son ses miksajı kabulü değildir. Ölçülen kare hızı
15,07…16,74 fps; istenen 24 fps elde edilmiş gibi yazılmaz. Eski bağımsız
matkap çekimi `06_sondaj.mp4` korunur; ana kurgu için v2 önerilir.

Her klibin `.encoding.json` ve `.audio-edit.json` dosyası vardır; görev
kliplerinin `.source.json` dosyası “scripted SCENARIO / no ROS commands”
ayrımını korur. Ana kayıt WAV'ı görev kliplerinde yaklaşık 6–7 saniye kalmıştır.
Bu ses hızlandırılmaz veya uzatılmaz: özgün sample zamanında tutulur, eksik
kısım sessizlikle doldurulur ve izin verilen özgün müzik eklenir. Eksik
son uzunluğu her ses kaydında açıkça yazılıdır. Açılışın beş VO/Foley sahnesi
gerçek shot log'una göre yeniden yerleştirilmiştir. Ham PNG/manifest/master
dosyaları korunur; sesler canlı kaydedilmiş gibi sunulmaz.

`07_laboratuvar_ph` için yalnız `13BF906C` son çekimi kullanıldı: ilkinde
grafik görünmüyor, sonraki denemelerde ters duruyordu. Son çekimde dik/tam
grafik görüntüsü doğrulandı. `03_numune ... FAC26AF8` ilk denemesi de sahne çakışması nedeniyle
kullanılmadı. XRF/teslim görüntülerinde koyu astronot ve geniş kamera küçük
aletlerin okunmasını zorlaştırıyor; nihai kurguda yakın çekim iyileştirmesi açık.
Canlı ROS rover/RViz engel kaçınma, gerçek drone uçuşu, yürüyüş ve RAD dönüş
klipleri bu teslim listesine eklenmiş değildir. Lab videosu yeni bir canlı
analiz çalıştırmaz; `tablet-lab-flow/verification.json` içindeki önceki
SIMULATED ürün serisini numune kimliğiyle gösterir.

## Tam video için çekim sırası

Bu tablo mevcut klipler ile henüz çekilecek canlı parçaların hedefini gösterir.

| Klip | Çekilecek hareket ve kontrol | Görünen sonuç / kapsam |
|---|---|---|
| **01 Açılış** | İniş → plak başında dinlenme → veri odası → airlock → çıkış. | Gerçek Unreal sahnesi/animasyonu. Türkçe özgün Chatterbox sesler, yerel Foley, keşif müziği take 01. 60 saniyelik ilk görüntü alındı; ses, kaynak dosyalarından shot log'una göre ayrıca düzenlenir ve “edited mix” kaydı taşır. |
| **02 Saha yürüyüşü ve XRF** | WASD, Shift koşu, V kamera; görev işaretine yaklaş, E; ekrandaki sol fare/temas onayı. | Gerçek astronot ve kaynak `tool_apxs` modeli. Yeni saha işleme kodu derleme ve canlı kontrolden sonra çekilir. Sunumun tamamlanması ölçüm sonucu değildir; `/rover_1/contact_science`, `EV1_XRF` ürünü ayrıca beklenir. |
| **03 Numune ve kapak** | E ile sahada başlat; sol fareyle al, sağ fareyle tüpe aktar, E ile mühürle. | Kaynak tüp ve ayrı kapağın hareketi, numune/kap kimliği. `/redline/science/collect_sample` ve daha sonra `cache_sample`. Fiziksel kaya kavrama veya sızdırmazlık testi değildir. |
| **04 İstasyon kurma** | Hedefte E; sol fareyle yerleştirme, sağ fareyle direk/anten hareketi, E onayı. | Ayrı kaynak anten/sensör/ayak parçaları. `/redline/science/deploy_station` yerleştirme kaydı; istasyonun yeni hava zaman serisi yok. |
| **05 Rover, LiDAR ve engel** | Rover görevi açılınca E ile ROS komutunu başlat; roverı 3D'de izle; T tablette gerçek RViz pikselleri, Tab robot sayfası. | Gazebo/ROS tek fizik sahibi; `/rover_1/navigate_to_pose`, plan ve gerçek odom. Statik engel kaçınma için önceki kabul var; yeni klipte engel/costmap/rota gerçekten görülmeden “yeni kabul” yazılmaz. Aktif kampanyaya ikinci hedef gönderilmez. |
| **06 Drone keşfi** | Görev sırası scout adımındayken E; kalkış/tarama/dönüş/inişi 3D'de ve tablette göster. | `/scout_1/execute_scout`; gerçek Gazebo uçuşu. Gözlemler SIMULATED truth adaptörüdür. Güncel koşuda eski EV1 pozu yüzünden kesilen deneme başarı görüntüsü sayılmaz; ayrı geçerli koşu çekilir. |
| **07 Sondaj ve DAN** | Rover durduğunda ilgili görevi başlat; gerçek kaynak matkap ucunun dönmesi/inişi; Tab DAN/sondaj sayfası. | `/rover_1/drill` senaryo FDIR, `/rover_1/neutron_survey` WEH/GP ürünü. Kuvvet/tork grafiği gerçek sensör yokken üretilmez. Matkap ve APXS/LIBS anlatım videoları ayrı sunum klipleridir. |
| **08 Laboratuvar ve pH** | Numuneyi laboratuvara teslim et; T → Tab laboratuvar; P ile model analizi, ürün gelince pH/iletkenlik grafikleri. | `/redline/science/analyze_sample`; kaynak numune, ayrı analiz yeri, kalıcı JSON/XML. WCL_SCENARIO sonuçları modeldir; Gale/Phoenix ölçümü gibi sunulmaz. |
| **09 Alarm ve dönüş** | Gerçek RAD/S1 bağlantılı ayrı koşuda alarm → pay/çizgi → dönüş; varsa aynı sahnede take 02. | ARCHIVE RAD + DERIVED dönüş alanı. Varsayılan kampanya RAD replay/rule_monitor başlatmadığından, bu çekim o graph'ta varmış gibi yapılmaz. Alarm koşusu yoksa klip eksik kalır; UI uyarısı sahte yayımlanmaz. |

## Kayıt ve ses

Doğrulanmış derlemede `-RedlineShotDir=<mutlak yerel klasör>` ile kayıt aktörü
açılır. `F10` kaydı başlatır/bitirir; klip en çok 120 saniyedir, oyun kapanmaz.
İsteğe bağlı `-RedlineShotName=02_saha`, `-RedlineShotSeconds=45`,
`-RedlineShotFps=24`, `-RedlineShotAutoStart`, `-RedlineShotDelay=5` kullanılır.
PNG'ler gerçek kare zamanlarıyla saklanır; istenen 24/30 fps, ölçülen fps
olarak raporlanmaz. `master.wav` oyun ana ses çıkışıdır.

`scripts/encode_unreal_shot.py <çekim-klasörü> --output <klip.mp4>` gerçek
zaman damgalarıyla VFR MP4 oluşturur, PNG/WAV/hash kayıtlarını korur. Kısa
veya sessiz ana ses otomatik tamamlanmaz. Kullanıcının izin verdiği ses
kurgusu ayrı WAV ve kaynak/hash/zaman/gain kaydıyla verilir; encoder bu
alternatif sesi ancak `--audio-file` ve `--audio-receipt` birlikteyse kabul eder.
Bu durumda çıktı açıkça düzenlenmiş ses olarak kaydedilir.

İki özgün müzik dosyası
`assets/audio/incoming/redline_sessiz_yorunge/redline_sessiz_yorunge_take_01.mp3`
ve `take_02.mp3`'tür. Take 01 açılış/keşfe, take 02 dönüş/krize ayrılır.
Plak sahnesindeki `vardiya_arasi_jazz.wav`, özgün yerel taslaktır; Chet Baker
kaydı değildir. Kaynak ses dosyaları ve mevcut müzik oturumu değiştirilmez.

## Var olan kanıt ve çekim boşlukları

- Gerçek RViz PNG taşıması: `test-results/tablet-rviz-readable-transport/verification.json`; kaynak/ulaşan SHA aynı, 1024×640. Canlı görüntü hâlâ veri tazeliğine bağlıdır.
- Statik engel ve gerçek Nav2: `docs/verification/T3_OBSTACLE_ACCEPTANCE.json`; RPP gerçek hedef hatası 0,197 m, MPPI 0,446 m. Tek simüle rota ve seyrek açıklık örnekleri sürekli çarpışmasızlık kanıtı değildir. Hareketli engelin yeni video kabulü ayrı çekim ister.
- Drone uçuşu: `test-results/campaign-field-physical-post-recovery/scout-trajectory-verification.json`; 69,48 s fizik uçuşu ve 33,74 m evden açılma. İnsan poz fixture'ı ve SIMULATED gözlem sınırı korunur.
- Lab sonucu: `test-results/tablet-lab-flow/verification.json`; gerçek servis/kalıcı ürün/numune zinciri, açık model pH ve iletkenlik.
- Kaynak parçalar: `test-results/sample-tube-parts-import.json`, `science-station-parts-import.json`, `drill-parts-import.json`. Bunlar ölçek/malzeme/ayrı parça kabulüdür; yeni oynanış videosunun çekildiğini göstermez.
- Önceden hazırlanmış ayrı anlatımlar: `assets/explainers/{apxs,libs,drill}/*.mp4` ve TR/EN SRT. Bunlar Blender sunumudur, gerçek Unreal görev kaydı diye etiketlenmez.
- B3 multispektral, B8 zamanlayıcı, B9 downlink ve B10 saha notunun bütün oynanışı; PR karşılaması, güvenli hızlı yolculuk, tam manuel uzun EVA ve son kum fiziği bu turla tamamlanmış sayılmaz.

Aktif kullanıcı oyunu bir çekim için kapatılmaz veya hedefi değiştirilmez.
Yeni denemeler ayrı domain/partition ve açık SCENARIO sahnesinde hazırlanır;
sonuç dosyası üretilmeyen klip “hazır” listesine eklenmez.
