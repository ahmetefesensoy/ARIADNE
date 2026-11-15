# Oyunculu EVA kampanyası

15 Kasım 2026 · D017 · Görev, kapı, numune ve büyük ekran uygulaması.

Tek EVA, 12 adım: brifing → öncü keşif → sırt/çukur kararı → yüzey numunesi
→ el tipi ölçüm → istasyon → rover/LIBS → DAN → sondaj → laboratuvara teslim
→ veri değerlendirmesi → debrief. Bir servis yanıtı yalnız komut kabulüdür.
Bilim adımı başarılı action sonucu, ilgili kalıcı ürün, ürünün kanıtı ve
gerekiyorsa numune durumu doğrulandığında ilerler. Hata/iptal görevi açık tutar.

| Kontrol | İşlev |
|---|---|
| M / J | Büyük konsol / görev listesi |
| Tab | Konsolda görev/bilim/robot/çevre sayfası |
| E / X | İşlem başlat / iptal iste |
| 1 / 2 | Sırt/çukur veya örüntü desteği/ek ölçüm kararı |
| Sol / sağ ok | Bilim sayfasında ürün seç |
| WASD / Shift / V | Hareket / senaryo koşusu / kamera |

Konsol açıkken insan yürümez; görev saati ve robotlar sürer. Kapılar kilit →
iki panelin yana kayması → conta/kapanma akışı, durum lambası ve konumsal
motor sesi kullanır. Kapsül açıklıktayken kapanmaz, engelde tekrar açılır.
Basınç veya gerçek airlock çevrimi simülasyonu değildir.

Kampanya mevcut sesli iniş/airlock/başlangıç sahnelerini de açar. Boşluk
mevcut çekimi, Esc bütün açılışı atlar. ROS evre geçişlerinde mevcut kısa
klipler gösterilir; her 12 adım için ayrı yeni video üretilmedi.
`-SkipPrologue` açılış kliplerini atlayarak teknik incelemeyi başlatır.

Toplama 1,2 m; ölçüm/yerleştirme 1,5 m yakınlık ister. Güncel Unreal EV1
pozu ROS'a gider. Ayrı sunum gövdesi çömelip uzanır ve tüpü ele alır;
gerçek kapsül yer değiştirmez, poz yayını sürer. Sonuç/iptal kamera ve
kontrolü geri verir. Yüzde100 geri bildirim kendiliğinden başarı üretmez.
Bu, fiziksel kaya yakalama veya motion-capture klibi kabulü değildir.

Komuta duvarı ve tam ekran konsol aynı ROS durumunu kullanır: görevler,
hedef/yön/mesafe, ürünler, bileşim ±1σ grafiği, numune kökeni/analiz yeri ve
robot durumu. RAD aboneliği varsa seçili B/E serisi ve arka plan +%25 çizgisi
çizilir. Dedektör/saat değişiminde seri ayrılır. Varsayılan kampanya RAD
alarm replay'i açmaz; T6'nın tam S1 kabulü ayrı ve açıktır.

Duvar ekranı `scripts/prepare_campaign_display.py` ile hazırlanan ayrı unlit
malzemeyi kullanır. Yatay yön düzeltmesi kampanyada uygulanır; kabin kaynak
malzemesi değiştirilmez. Son CUA görüntüleri ve kaynak/test hash'leri
`docs/verification/CAMPAIGN_PREVIEW.json` içindedir.

## Otorite ve sınırlar

- Tek `campaign_controller`, kampanya MissionState/kararlarını yönetir.
  Oryantasyon/nominal `mission_manager` aynı graph'ta başlatılmaz.
- İnsan Unreal'dadır. Robot fizik/odom/kontrolü ROS/Gazebo'dadır. Rover
  güncel map/TF pozu ve Nav2 varış sonucu olmadan ölçüme geçmez.
- Fiziksel scout özgün dört rotorlu Gazebo modelidir; Mars yoğunluğu/kütle/
  kazançlar SCENARIO'dur. Onaylı Tripo gövde/dört rotor UE sunumudur;
  görsel rotor dönüşü motor komutu değildir.
- Scout gözlem adaptörü ulaşılan gerçek uçuş noktalarında SCENARIO truth'tan
  **SIMULATED** kayıt üretir; kamera/LiDAR algısı değildir. Adaptör yoksa
  başarılı uçuş bile bilim açısından PARTIAL döner.
- Ölçüm/sondajlar **SIMULATED / UNCALIBRATED_SCENARIO**. Fiziksel MoveIt
  kolu, temas/kuvvet sensörlü sondaj ve çok noktalı adaptif DAN kabulü yok.
  İstasyon ürün/konum kaydıdır; yeni hava/doz ölçümü uydurulmaz.

Ürünler `data/products/<run_id>/` içinde JSON + PDS4 benzeri XML'dir.
Kampanya durumu, karar JSONL'ı, numune ve request tekrar koruması aynı koşuya
bağlıdır. Köken değişmez; laboratuvar teslimi analiz konumunu günceller.
APXS arşiv koordinatları bu senaryo hedeflerde genellenmez.
[Bilim kapsamı](SCIENCE_REHEARSAL.md).

## Başlatma

```bash
bash scripts/configure-gazebo-python.sh
bash scripts/build-campaign.sh
CAMPAIGN_SCOUT_MODE=physical bash scripts/run-campaign-backend.sh <dogrulanmis-workspace> 3600
```

Betik yeni partition/kanıt klasörü/güncel WSL URL'sini yazar. Varsayılan
domain137/port9390; `CAMPAIGN_DOMAIN_ID`/`CAMPAIGN_PORT` ile ayrılır. Yalnız
kendi süreçlerini kapatır. `CAMPAIGN_SCOUT_MODE=stub` ayrı simüle gözlem
seçeneğidir; fiziksel scout ile aynı anda çalıştırılmaz.

`CAMPAIGN_RVIZ=1` aynı graph'a pasif RViz ekler; LiDAR, rover modeli ve
costmap izlenir, kampanyayla yarışan SetGoal aracı açılmaz. RViz kamera odağı
koşunun gerçek spawn konumundan üretilir. `CAMPAIGN_RVIZ_DRIVER=d3d12` yalnız
yerel GPU sürücüsü doğrulanmışsa kullanılabilir; varsayılan llvmpipe'dır.
RViz penceresi Unreal'ın yanında bağımsızdır; Unreal'a gömülmüş değildir.

Robot sayfası gerçek fizik izi, Nav2 planı, fizik zamanından hız, son hedef
durumu ve veri yaşını gösterir. Henüz hedef yoksa plan uydurulmaz. Mevcut
idle/walk klipleri yumuşak harmanlanır; gerçek koşu klibi açık iştir.
İlk sınırlı yüzey tozu için `scripts/prepare_surface_dust.py` malzemesi gerekir.
Bu native görsel katmandır; son kum shader'ı veya zemin fiziği kabulü değildir.

Varsayılan `field` profili, gerçek T1 dönüş alanının 12–18 dakika bandında,
280–430 m uzaklıkta, ince çarpışma desteği ve <10° eğim koşuluyla iki hedef
seçer. İlk seçimler E−30/N−382 ve E30/N−302 m; dönüş risk süreleri 14,54 ve
15,15 dk. Hedef sınıfı/kimyası SCENARIO'dur. Rover saha öncesinde ilk hedefin
10 m batısında konuşlandırılır; EVA sırasında oraya ışınlanmaz. Yön pini
core'dan gelen hücre rotasını izler. `CAMPAIGN_FIELD_PROFILE=tutorial`
önceki 16–31 m yakın denemeyi açar. Fizik hızlandırılmaz.

```powershell
./scripts/start-t5-eva.ps1 -Campaign -RosbridgeUrl ws://<guncel-WSL-IP>:9390/
```

Güncel derleme ve `Content/Campaign/scout.json` gerekir.
`prepare_campaign_runtime.py`, hedef Z'sini doğrulanmış T1 çarpışma
üçgenlerinden örnekler; XY/kimya SCENARIO'dur, kaynak mesh değişmez.
`prepare_campaign_scene.py` mevcut scout FBX/PBR'ını cm kontrolüyle içe alır;
yeni model üretmez.

## Kanıt

`test-results/campaign-flow-first/verification.json`: 12 adım, 7 ürün,
70 kanıt ve ayrı numune kökeni/analiz yeri; gerçek Gazebo roverı 6,60 m
ilerleyip Nav2 hedefini tamamladı. İnsan açık SIMULATED poz stand-in'iydi;
bu kayıt bütün güzergâhın manuel yürünmesini kanıtlamaz.

`campaign-controller-dds.xml`: 6 DDS testi; scout/Nav2 açık fixture, bilim
düğümü gerçek. `campaign-robot-pose-dds.xml`: gerçek DDS/TF dönüşümü ve
eski/bozuk frame/quaternion reddi. `Redline.EVA` kapı/numune sunumu;
`Redline.Campaign` konsol/RAD testleridir.

`test-results/scout-physical-action/verification.json`: ayrı gerçek Gazebo
ExecuteScout kalkış/uçuş/iniş, negatif Z orijini ve algı yokken PARTIAL.
Tek başına BXW/algı kabulü değildir. S4/S4c gözlem→hücre→yeniden plan
kanıtları `test-results/t7-fresh-b60oWlir/` altındadır.

`test-results/campaign-field-physical-post-recovery/verification.json`:
BXW'de fiziksel scout ile 12 adım, 7 ürün, 35 kanıt ve 6,59 m gerçek rover
hareketi geçti. Aynı klasördeki `scout-trajectory-verification.json`, gerçek
uçuş durumlarından kalkış/tarama/dönüş/inişi doğrular: 69,48 s fizik uçuşu,
evden en uzak mesafe 33,74 m. İnsan poz fixture'ı ve SIMULATED truth algısı
kullanıldı; bütün EVA'nın elle yürünmesi veya fiziksel algı kabulü değildir.
Önceki `campaign-field-physical-acceptance` kaydı WSL kesintisi/eski odom
nedeniyle başarısız olarak korunur. Güncel koşuda gözlenen ~0,49× fizik/duvar
oranı performans eksikliği olarak açıktır.
T8/T10 fiziksel sensör kabulü, tam manuel kampanya, OpenMCT/downlink açıktır.
