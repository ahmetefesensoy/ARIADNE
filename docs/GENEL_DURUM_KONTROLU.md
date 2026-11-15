# Görevler ve robotlar: genel durum

15 Kasım 2026, 04:00 (+03:00) · Kaynak ve kayıt incelemesi.

Bu belge 04:00 durumunu korur. Sonraki kampanya, bilim yürütücüsü ve fiziksel
scout çalışması için [15 Kasım 09:25 kaydına](../journal/log/2026-11-15-oyunculu-kampanya.md)
ve [kampanya kılavuzuna](CAMPAIGN_PLAYABLE.md) bakın; aşağıdaki eksiklerin
bir bölümü o çalışmada uygulandı, kapsamlı kilometre taşı kabulü hâlâ açıktır.

Oynanabilir EV1 başlangıcı var. Tam görev kampanyası, drone uçuşu ve bilim
ürünü üretimi henüz birleşmiş değil. Bu incelemede yeni simülasyon, uçuş,
navigasyon veya Unreal kabul koşusu yapılmadı; aşağıdaki sonuçlar mevcut
kaynaklara ve tarihli kanıtlara dayanır. Hiçbir kilometre taşı kapatılmadı.

| Alan | Doğrulanan | Açık kalan |
|---|---|---|
| Hikâyeli başlangıç | Atlanabilir açılış/evre sahneleri, sesler, ayrı komuta/lab/koridor, koşu, birinci kişi ve J günlüğü önizlemesi. | Bütün oda–koridor–yüzey geçişleri, yüz mimikleri ve ayrı koşu animasyonu. Durum `PARTIAL_PREVIEW`. |
| Oyuncu görevleri | ROS tarafından korunan brifing → bağlam istasyonu → dönüş → debrief oryantasyonu; konum/tazelik denetimi. | Standart başlangıç `planner:=false,intro:=true`; PRECURSOR keşfi ve bilim aksiyonları bu akışa bağlı değil. |
| Rover / T3–T4 | Ayrı Gazebo/RViz hedef sürüşü ve UE poz/koordinat aktarımı teknik kabulü var. | Alçak 3D engelli tam navigasyon kabulü başarısız kaldı. Mevcut EVA başlangıcı Gazebo/Nav2 başlatmıyor. |
| EV1 / T5 | Gerçek UE ayak kökenli ENU pozu, yaklaşık 20 Hz yayın, saha/çizgi/pay gösterimi teknik kabulü var. | Bu kabul bütün hikâye veya bilim kampanyası kabulü değildir. |
| Ortam / T6 | RAD/SPICE, SEP backend alarmı ve dönüş alanı daralması için geçmiş kanıt var. | Tam Unreal S1 alarm + çizgi daralması kabulü; SpaceWeather grafiği, REMS ve arazi ufku. |
| Drone / T7 | VOI önerisi, `ExecuteScout`/`SurveyArea`, SIMULATED kanıt ve yeniden plan altyapısı var. | Gazebo uçuş modeli/kontrol/odom, UE drone sunumu ve oyuncu robot konsolu yok. S4 yeniden plan kabulü açık. |
| Bilim / T8–T10 | Aksiyon sözleşmeleri, hedef seçimi ve bilim değeri/planlama çekirdeği var. | `redline_science` yürütücüsü, LIBS/APXS/DAN/sondaj/numune ürün akışı ve oyun ekranları yok. `STATION_SCIENCE` evresine geçmek ölçüm üretmiyor. |
| EV2 / T9 | Plan izleme, O₂ sızıntı çarpanı, dönüş maliyeti ve FR-05 temel kod/testleri var. | S2 senaryosu/koşusu, telemetriden sızıntı tespiti, `link_manager`, `rover_placer` ve UE EV2/PR bağlantısı. |
| Telemetri / T11 | Mesaj ve kayıt temelleri var. | OpenMCT/web ve `redline_telemetry` uygulaması yok. |

## S4 ve drone kabulündeki boşluk

`test-results/scn-bxw-20261114T234532Z-S4_BLOCKED_CORRIDOR-4/summary.json`
debrief'e ulaşmış; yalnız `plan-BXW-0001` v1 kaydedilmiş. Karar
`route clear, plan kept`. Buradaki `all_expected_ok:true`, beklenen FR
kural sonuçlarına aittir; engelli koridor nedeniyle yeniden planı kanıtlamaz.

Kaydedilmiş keşif alanının x başlangıcı 356 m. Engel merkezi x=342 m,
yarıçapı 10 m olduğundan engel x=352 m'de biter: keşif alanı engeli 4 m ile
kaçırmış. Güncel VOI kaynağında koridor genişletmesi var; bu değişiklikten
sonra S4/S4c kabul koşusu kaydı bulunmadı. Sonraki koşu evidence, cell delta,
task proposal ve plan v1→v2 bağlantısını birlikte saklamalı.

Ek kaynak bulgusu: `mission_manager.py::_on_scout_result`, ROS action durumu
ve `result.outcome` denetlenmeden `settling` evresine geçiyor. Boş kanıtlı
iptal/başarısız sonuç temiz rota gibi işlenebilir; böyle bir canlı hata bu
incelemede üretilmedi. `scout_stub` da PRECURSOR koşulunu kendi içinde
doğrulamıyor. Bunlar başarılı/iptal/başarısız aksiyon testleriyle kapatılmalı.

## Kanıtlar ve çalışma sırası

- [Anlatı kaydı](verification/NARRATIVE_PREVIEW.json),
  [oynanış akışı](EVA_PLAYABLE.md), [T5](verification/T5_ACCEPTANCE.json).
- [T3 sürüş](verification/T3_RVIZ_ACCEPTANCE.json),
  [T3 alçak engel](verification/T3_3D_PERCEPTION.json),
  [T4](verification/T4_ACCEPTANCE.json).
- [T6 çalışma kaydı](../journal/log/2026-11-14-t6-sep-hatti.md),
  `test-results/t6-eva-live/capture.json` (`passed:false`, korunuyor).
- `test-results/t5-build-kd30VpjI`: 59 ROS testi, sıfır hata/başarısız/atlanan.
  İlgili mission/VOI/scout/launch kaynakları snapshot ile eşleşir.
  `test-results/t7-p1-python.xml`: daha önceki tarihli 604 başarılı core testi;
  güncel bütün çekirdeğin yeniden çalıştırıldığı iddia edilmez.

Önce T6'nın gerçek Unreal S1 kabulü kapanmalı. Ardından T7'de aksiyon sonucu
denetimi ve güncel S4/S4c yeniden plan kabulü; fiziksel Gazebo drone ve UE
sunumu gelmeli. Sonraki dikey adım, oyuncu konsolundan robot görevine ve
kanıttan bilim ürününe uzanan akışı aynı kampanyaya bağlamak. T8–T10
bağımlılıkları korunmalı; görsel model veya sinematik görev kabulü sayılmamalı.

Git/GitHub işlemi ve yeni model üretimi yapılmadı.
