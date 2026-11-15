# Elde tablet, bilim ürünleri, atlas ve yüzey v2

15 Kasım 2026 · Başlangıç 10:25, entegrasyon 12:01 (+03:00) · Codex.

Kullanıcının istediği Tripo tablet üretildi ve Unreal'a alındı. 32 × 22 × 2 cm tasarım ölçüsü, özgün doku ve kaynak GLB korunur. Üretim/dönüşüm 35 kredi; işlem sonrası kayıtlı bakiye 345. Kaldırma/indirme ve mevcut astronot kol IK'sı Unreal'dadır. İlk tutuş ekranı kapatıyordu; eller alt köşelere taşındı ve gerçek RViz ekranı oyunda görüldü. Parmak tutuşunun son cilası açık.

RViz, özel Xvfb üzerinde gerçek ROS/Nav2/LiDAR katmanlarını çizer. PNG, ROS ve rosbridge'den tablete gelir; yeniden çizilmiş temsili harita değildir. Kaynak/taşınan PNG özetleri eşleşti. Akış kesildiğinde eski görüntü canlı gösterilmez. Kaynak dosyası: `scripts/rviz_tablet_stream.py`; sözleşme D021. Fizik saatinin sıfırlanması yeni akış kimliği açar; aynı boyuttaki doku yeniden kullanılır.

Tablette görevler, hata çubuklu bilim/numune ürünleri, robot izi/planı, RAD, drone gözlemleri, DAN/sondaj, pH/iletkenlik ve atlas sayfaları bulunur. Var olmayan ölçüm serileri çizilmez. Ek lab düğümü gerçek kayıtlı numune zincirini denetleyip ürün JSON/XML ve EvidenceRecord yazar. pH/EC açık SCENARIO modelidir; NASA ölçümü değildir. Tam 12 adımlı testte insan pozları açık teleporter fixture, rover ise gerçek Gazebo/Nav2 idi. Yeni lab testi bu koşuda teslim edilen numuneyi kullandı. Bunlar fiziksel el/alet/sondaj kabulü değildir.

Kampanya artık geç bağlanan tablete en çok 128 gerçek alınmış scout kaydını verir. Sonradan açılan drone sayfasının boş görünmesi bu yolla giderilir. Kanıtlar yine SIMULATED truth-adaptörü gözlemleridir; fiziksel kamera algısı sayılmaz.

Diğer oturumun D020 atlası ve görev kartları esas alındı. `stage_tablet_atlas.py`, altı katmanın özet/PNG/harita sözleşmesini yazmadan önce doğrular ve özgün baytlarla iki Unreal içerik köküne taşır. Atlas sayfası kuzeyi yukarıda ENU dönüşümü, katman seçimi, istasyon ve görev kartları sunar. Canlı ROS sınırı yoksa bunun eksik olduğu yazılır; statik dönüş süresi başlangıç durumudur. Kartlarda model, sunum planı, ROS action/uç noktası ve veri etiketi gösterilir. Henüz uygulanmayan kartların seçilmesi işlem başlatmaz.

Yüzey v2 ayrı `BXW_EVA_SurfaceV2` haritasına alındı. 121 ince karo + dış halka, 15.317.568 üçgen. Kaydedilmiş haritanın üç gerçek collision sorgusu DEM'den en çok 0,01965 m ayrıldı. 178 diğer aktör korundu. Mevcut kum malzemesinin üzerine yazılmadı. Geometri 1 m'dir; renk dokusu mevcut 3 km bağlam atlasından gelir. Önbellekte başka oturumun daha yeni ışık/shader düzenlemeleri bulundu; depo/önbellek farkları hash kaydında tutuldu.

Hızlı yolculuk D022 ile tanımlandı, uygulanmadı. Basit PET atlaması mevcut poz modunda yürüyüş sarfını eksik ödetir ve alarmı atlayabilir. Uzak atlas istasyonları canlı kampanyanın bölüm hedeflerinden ayrıdır. ROS'un yolu ve fizyolojiyi birlikte yürüttüğü yetki devri, sığınak/PR ve alarm kabulü sonraki iştir. T taşları bu görsel entegrasyonla topluca tamamlanmış sayılmadı. Git/GitHub işlemi yapılmadı.

Kanıt girişleri: `docs/verification/TABLET_ACCEPTANCE.json`, `SURFACE_V2_IMPORT.md`, `test-results/tablet-*` ve `surface-v2-*`. İlk yanlış kapsamlı native test komutunda eksik bridge mock/EV runtime önkoşulları nedeniyle iki hata vardı; kayıt tutuldu ve ilgili testler doğru profil ile tekrar çalıştırıldı. İlk lab C mesajında float dönüşümü ve kısa FDIR test süresi düzeltildi; başarısız geçmiş koşular korunur.
