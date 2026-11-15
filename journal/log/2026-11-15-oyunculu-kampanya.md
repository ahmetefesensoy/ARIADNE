# Oyunculu görev zinciri, kapılar ve bilim ekranı

15 Kasım 2026, 09:25 (+03:00) · Codex · D017 · Durum: PARTIAL_PREVIEW.

Kullanıcının yalnız hedefte E'ye basılan oryantasyon eleştirisi üzerine ayrı
kampanya başlatıcısı eklendi. Mevcut oryantasyon kaydı tarihsel olarak korunur.
Yeni akış tek EVA içinde 12 adım yürütür: brifing, öncü keşif, rota kararı,
numune, el tipi ölçüm, istasyon, rover/LIBS, DAN, sondaj, laboratuvara teslim,
değerlendirme ve debrief. İlerleme kabul yanıtına veya zamanlayıcıya değil,
aksiyon sonucu ve ilgili ürün/kanıt/numune kaydına bağlıdır.

## Uygulanan davranış

- Çekirdek görev kuralları `redline_core.campaign` içinde; ROS koordinatörü
  güncel gerçek EV1 pozunu, hedefi, revizyonu ve robot sonucunu denetler.
  Kampanya başlatıcısında ikinci `mission_manager` çalışmaz.
- Saha profili T1 ızgarasının gerçek 12–18 dk dönüş alanında iki hedef seçer.
  Örnek seçimler E−30/N−382 ve E30/N−302 m; dönüş süreleri 14,54/15,15 dk.
  XY ve kimya SCENARIO, Z doğrulanmış çarpışma üçgenlerinden DERIVED'dır.
  Rota pini dönüş alanından türetilmiş hücre güzergâhını izler; ters çevrilen
  dönüş rotası en iyi çıkış rotası olarak sunulmaz.
- Rover önceden saha yakınına konuşlandırılır. ROS/Gazebo fizik ve Nav2
  otoritesidir; Unreal yalnız gerçek fiziksel pozu çizer. Nav2 varışından
  önce LIBS başlamaz. Robotlar EVA içinde ışınlanmaz.
- Kapılar kilit/iki panel/kapanma/conta/lamba/konumsal ses kullanır.
  Kapsül açıklığı veya engel kapanmayı durdurur ve yeniden açar. Bu insan
  query collision'ıdır; basınç çevrimi ve robot fiziği değildir.
- Numune sunumu mevcut astronotun ayrı poz gövdesinde çömelme, uzanma ve tüp
  transferini gösterir. Asıl kapsül, ayak kökenli poz yayını ve ROS konum
  denetimi korunur. Sonuç/iptal kamera ve kontrolü geri verir. Tüp/alet
  yerel temsil geometrisidir; yeni Tripo üretimi veya fiziksel tutuş değildir.
- Büyük komuta ekranı ve M/J konsolu aynı güncel durumu gösterir: 12 görev,
  hedef/mesafe, ölçüm ürünleri, bileşim ±1σ grafiği, numune kökeni ve ayrı
  analiz yeri, robot durumu. RAD gelirse B/E serileri ayrı tutulur ve +%25
  eşik çizilir. DAN ısı haritası, derinlik/kuvvet zaman grafiği ve kamera
  akışı henüz uygulanmadı.
- Mevcut sesli iniş/airlock açılışı ve evre klipleri kampanyaya bağlandı;
  Space/Esc ile atlanır. Her görev için yeni bir video üretilmedi.
- Gazebo scout dört rotorlu özgün SCENARIO modelidir; UE gövdesi mevcut
  Tripo paketinden alınır. Fiziksel poz/kontrol UE'de üretilmez. Ziyaret edilen
  noktalardaki truth gözlem adaptörü açıkça SIMULATED'dır; gerçek algı yoktur.

## Gözlenen doğrulamalar

| Kanıt | Gözlenen sonuç ve sınır |
|---|---|
| `campaign-build-weuApPL4` | Güncel ROS snapshot `dc2376c9106aee04…`; 151 test, sıfır hata/başarısız/atlanan. Diğer oturumun yeni giysi kaçağı testi de dahil. |
| `campaign-release-core.xml` | Görev, saha hedefi ve bilim çekirdeği: 30 geçti. |
| `campaign-controller-dds.xml` | Gerçek bilim düğümüyle altı DDS testi; scout/Nav2 açık test fixture'ıdır. |
| `campaign-post-recovery-gates.stdout` | Gerçek DDS/TF robot poz testi 1, fiziksel scout koruma testleri 8 geçti. |
| `campaign-story-ue-build.log` | UE 5.8.4 güncel derleme geçti. |
| `campaign-post-recovery-ue-tests.json` | 20 native test geçti; üç test uyarılı başarılı. Kapı, numune, konsol, RAD ve mevcut müzik testleri dahil. |
| `campaign-flow-first/verification.json` | 12 adım, 7 ürün, 70 kanıt; gerçek Gazebo rover hareketi 6,60 m ve Nav2 SUCCEEDED. İnsan SIMULATED poz stand-in'iydi; elle yürünmüş kampanya kabulü değildir. Scout stub kullanıldı. |
| `scout-physical-action/verification.json` | Gerçek Gazebo + ROS ExecuteScout kalkış/uçuş/iniş; negatif Z orijini. Algı yokken PARTIAL ve boş kanıt doğru korundu. Ayrı düz zemin denemesidir. |
| `campaign-field-physical-post-recovery/verification.json` | 09:30:35'te BXW fiziksel scout ile 12 adım tamamlandı: 7 ürün, 35 kanıt, 2 numune; Nav2 SUCCEEDED ve 6,59 m gerçek rover hareketi. İnsan hâlâ açık poz fixture'ıdır. |
| `campaign-field-physical-post-recovery/scout-trajectory-verification.json` | Aynı ROS akışındaki 1.088 gerçek uçuş durumundan kalkış/tarama/dönüş/iniş/COMPLETE doğrulandı. Fizik uçuşu 69,48 s, evden en uzak mesafe 33,74 m; iniş evin 0,12 m z yakınında. Truth gözlemleri SIMULATED'dır. |
| `t7-fresh-b60oWlir` | S4: 1.424 SIMULATED gözlem → hücre güncellemesi → plan v1→v2; algılanabilir 18/18 hücre. S4c açık alanda plan v1 korundu. Fiziksel algı kabulü değildir. |

## Başarısız denemeler ve açık işler

`campaign-field-physical-acceptance/verification.json`, scout poz akışı
eskidiğinde işlemi başarısız bıraktı. Aynı sırada WSL servis çağrıları
`0x8007274c` ile zaman aşımına düştü. Kök neden kesinleştirilmedi. Sonraki
kontrolde dağıtım Stopped bulundu; kapatma komutu verilmeden yeniden açıldı.
Güncel derleme/testler yukarıdaki kayıtlarda yeniden çalıştırıldı. Eski hata
kayıtları korunur; yeni koşu ayrı dizine yazılır.

`campaign-build-joGj0aPW` içindeki önceki giysi kaçağı testi başarısızlığı da
korunur. O snapshot ile diğer oturumun güncel kaynağı farklıdır; güncel
snapshot'ta aynı test geçti. Başka oturumun müzik/kaçak/APXS kodu bu iş için
değiştirilmedi. Ortak testleri çalıştırmak dosya sahipliğini devralmaz.

09:30:35'teki yeni koşu fiziksel BXW scout zincirini geçti. Önceki başarısız
koşu değiştirilmedi. Simülasyon/duvar oranı yaklaşık 0,49× gözlendi; yük
nedeniyle uçuş duvar saatinde daha uzun sürdü. Bu, performans hedefinin
sağlandığı veya önceki WSL hatasının kök nedeninin çözüldüğü anlamına gelmez.

Bütün kampanyanın Unreal'da elle yürünmesi, gerçek
kol/temas/kuvvet sensörü, adaptif çok noktalı DAN, aktif çevre istasyonu,
tam SEP/acil dönüş bölümü ve OpenMCT/downlink kabulü açıktır. Ölçümler
SIMULATED / UNCALIBRATED_SCENARIO'dur. APXS arşiv hassasiyet modeli ayrı
oturumun işidir; 20 saniyelik demo ürünleri kalibre aralığa taşınmış sayılmaz.
T6/T7/T8/T10 veya bütün oyun bu kayıtla tamamlandı işaretlenmez.

Başlatma ve kontroller: [CAMPAIGN_PLAYABLE.md](../../docs/CAMPAIGN_PLAYABLE.md).
Git/GitHub işlemi veya yeni model üretim kredisi kullanılmadı.

## 09:46 (+03:00) — Son görsel ve süreç kontrolü

CUA'da 12 tamamlanmış görevin konsolu, LIBS bileşim grafiği/±1σ çubukları ve
iki numunenin ayrı köken/analiz yeri görüldü. Kod durumları yerine numune
adımları okunur Türkçe gösterilir. Oda ekranının ters UV yönü düzeltildi;
ayrı `M_CampaignDisplay` unlit malzemesi ışık parlamasını kaldırır. Eski pano
başlıkları yalnız kampanya içinde gizlenir; kaynak iç mekân malzemeleri
değişmez. Görseller `campaign-field-physical-post-recovery/ue-*.png` altındadır.
Son native derleme ve 20 test tekrar geçti: `campaign-wall-final-ue-tests.json`.

Eski üst süreç alt Gazebo/Nav2 gruplarını kapatmadan öldürülebiliyordu.
`t3_supervisor` SIGINT/SIGTERM'i açıkça ele alır; kampanya sahibi onun 12 s
kapatma süresine 25 s pay verir. 10 s sınırlı başlat–kapat denemesinde kendi
partition'ında açık süreç kalmadı (`campaign-shutdown-verification.json`).
Bu yalnız kaynak temizliği kabulüdür: iki ROS çocuk hata kaydı ve kesilmiş
salt-okunur verifier nedeniyle `all_children_graceful=false` ayrıca korunur.

Tamamlanmış test oturumu kapatıldı. `campaign-NlzURU1f` ayrı yeni koşusu ve
UE PID43588 açıldı; CUA'da canlı 01/brifing ve atlanabilir başlangıç görüldü.
Otomatik insan poz fixture'ı veya otomatik görev komutu bu oturumda yok.
Oturum en çok 3600 s sürer. Son kaynaklar doğrulanmış ROS/UE snapshot'larıyla
eşleşir. Hash'li toplu kayıt: `docs/verification/CAMPAIGN_PREVIEW.json`.

### 2026-11-15 09:51:50 +03:00 — Kullanıcı onayıyla WSL yeniden başlatma

Gecikmiş onay üzerine wsl --shutdown uygulandı; dağıtımlar Stopped olarak görüldü. Ubuntu yeniden açıldı ve Running doğrulandı. Önceki kampanya ROS/Gazebo süreçleri bu işlemle durdu; yeniden başlatılmadı. Önceki test/görsel kabul kayıtları tarihsel kanıttır. Kayıt: test-results/campaign-wsl-restart.json.

