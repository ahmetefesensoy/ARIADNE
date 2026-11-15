# T3 rover, algı ve navigasyon profili

14 Kasım 2026. Teslim görseli metre ölçeğinde korunur; kaynak dosyalar
değiştirilmez. Profil, gerçek direksiyon/rocker-bogie yerine altı pasif dikey
teker taşıyıcılı skid-steer yedeğidir. NASA türevi sanat,
ölçülmüş Mars arazi verisi ve SCENARIO fizik varsayımları ayrı tutulur.

`stage_delivered_rover.py`, altı tekerin pivotlarını hem Gazebo'ya hem ROS
açıklamasına yazar. Mesh/malzeme kopyaları ASCII önbellekte tutulur; kaynak ve
kopya hash'leri doğrulanır. Kaynak NASA/JPL bildirimi kopyalanır. Nav2 footprint,
kol dahil 3,9447 × 2,7772 m dış zarfı kapsar; proxy collision henüz yalnız
gövde kutusu ve altı yuvarlanma silindiridir. Kol/mast teması kabul edilmedi.

`--delivered-rover` profilinde:

- Statik eğim haritası gerçek **4 m** veri desteğinde kalır. Global Nav2
  çalışma penceresi **80 × 80 m / 0,20 m** olup bu katmanı örnekler; LiDAR
  engellerini ayrı ince hücrelerde tutar. Bu, DEM'e yeni detay kazandırmaz.
  Pencere dışındaki uzak hedefler için waypoint entegrasyonu gerekir.
- Local costmap **20 × 20 m / 0,20 m**, odom frame'inde hareketlidir.
- Inflation yarıçapı, footprint çevrel çemberi + padding + 0,20 m'dir.
  Stop/slow sınırları dış zarfın sırasıyla 0,20 / 1,00 m dışındadır.
- Slow bölgesi komutu tekrar tekrar çarpmak yerine mutlak **0,12 m/s /
  0,12 rad/s** sınırı uygular. Eski 0,4 × 0,3 maksimumu korunur. CLOSED_LOOP
  hız düzeltmesiyle oransal .3 ölçeklemenin sabit noktası yaklaşık .0064 m/s
  idi; gerçek Collision Monitor entegrasyon testi küçük komutun korunmasını,
  üst limit, Stop ve veri kaybı duruşunu denetler.
- Smac dönüş yarıçapı, bu yedek kontrol profilindeki `vx_max / wz_max`
  oranıdır (1 m). Önceki 4 m değeri kaba arama hücresi zorunluluğuydu.
  Hiçbiri ölçülmüş Curiosity dönüş yarıçapı olarak sunulmaz.
- MPPI ufku 56 × 0,05 s'dir: 0,4 m/s'de merkez 1,12 m ileriyi değerlendirir;
  her pozda tam footprint hesaba girer. Bu mesafe, 0,4 m/s² frenleme ve
  0,5 s kaynak zaman aşımı için toplam 0,40 m'den uzundur. Kontrol 20 Hz'dir.
- Fizik, teker enkoderi ve IMU Gazebo/ROS'a aittir. Bağımsız Gazebo pozu
  yalnız doğrulamada okunur; konum filtresine/plancıya yayımlanmaz.

Yedekte fiziksel teker merkezlerinin yüksüz ilk pozları ortak düzleme alınır;
teslim art pivotlarındaki yaklaşık 3 mm farkın görsel ilk pozu mesh ofsetiyle
korunur. Yanal / boyuna sürtünme katsayıları 0,5 / 1,0'dır; yön DART'ın
`gz:expressed_in=base_link` uzantısıyla gövde +Y eksenine bağlanır. Tork
tavanı küçük yedeğin kütle/yarıçap oranına göre 444,697 Nm'ye ölçeklenir.
Bu değerler SCENARIO'dur; Mars regolit ölçümü veya gerçek MSL motor/süspansiyon
kalibrasyonu değildir. Yalnız tork artışı ilk izotropik sürtünmeli denemede
dönüşü düzeltmedi; yönlü sürtünme ve teker düzlemiyle birlikte sınanır.
[Gazebo DART sürtünme uygulaması](https://github.com/gazebosim/gz-physics/blob/gz-physics7/dartsim/src/SDFFeatures.cc).

Gövde frame'i orta aksın XY merkezindedir; görsel gövde pivotu ve nominal
CG buna göre ofsetlenir. Teker taşıyıcıları 0,08 m aşağı / 0,12 m yukarı
pasif hareket, 10.000 N/m yay ve 1.000 Ns/m sönüm kullanır. Taşıyıcılar
1 kg'dır ve toplam 899 kg korunur. Bu bağımsız düşey uyumluluk, sabit
tekerlerin engebede boşta kalmasını azaltan SCENARIO yedeğidir. Süspansiyon
kolu görselleri henüz bu hareketi izlemez; gerçek mekanik port açık kalır.

Ara rota denetimi Nav2 1.3.13 ile aynı hücre anlamını kullanır: merkezde
`>=253`, footprint kenarında `>=254` reddedilir. Kenardaki 253, robot
merkezine uygulanan inscribed inflation'dır; bunu kenara yeniden uygulamak
engeli iki kez genişletiyordu. Bilinmeyen 255, gerçek engel 254, harita dışı
ve ara segment çarpışmaları hâlâ reddedilir. Regresyon testi her ayrımı kapsar.
[Nav2 sürüm kaynağı](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/collision_checker.cpp).

roversim27'nin kodu kopyalanmadı. İncelenen akış: 3D bulut → zemin ayrımı →
yerel/global engel katmanları → plan/kontrol → yavaşlama/durma → alt sürücü
watchdog. ERC ölçüleri ve Dünya ayarları taşınmadı. REDLINE'ın mevcut yüksek
tek düzlemli LiDAR'ı düşük kaya algısı veya 3D zemin ayrımı sağlamaz.
Yeni `--lidar-3d` seçeneği bu ayrımı ölçülen XYZ'den yapan, ayrı doğrulanan
32 katmanlı / 360 azimut / 5 Hz SCENARIO sensör ekler; eski kabul koşuları
bu seçeneği kullanmadı.

3D filtrede algoritma `python/redline_core/src/redline_core/ground.py` içindedir.
Yerel 8 m'de, sensör frame'inde `z=a*x+b*y+c` düzlemi hücre minimumlarından
deterministik RANSAC ile bulunur. Destek, beklenen sensör yüksekliği, eğim
ve iki boyutlu uzanım kapıları vardır. 1,5 m komşuluklarda alt yüzeyin
gözlenen hücre minimumlarından yerel düzlem desteği aranır; doğal kıvrımları
tek düzleme göre engel saymayı azaltır. Yerel destek yetersizse ilk düzlem
korunur; eşikler artırılmaz. Artık yüksekliği <=8 cm olanlar zemin,
>=14 cm olanlar engel olarak ayrılır; aradaki bant ve aşağı kırıklar bilinmeyen
kalır. Bu eşikler SCENARIO'dur. Komşuluktan geniş yükseltilmiş platform,
çoklu zemin yüzeyi, uçurum/çukur, dik yamaç
ve genelleştirilmiş kaya sınıflandırması kabulü değildir.

Fit başarısızsa yeni boş engel bulutu yayımlanmaz. Collision Monitor'da 3D
kaynak süresi 0,5 s'dir; eski/tekrarlı damga ve yanlış frame reddedilir.
Ground/obstacle bulutları özgün ölçüm damgası/frame'i taşır. Ground yalnız
ray-clearing, obstacle yalnız marking için kullanılır. Kayaların dünya-listesi,
DEM yüksekliği veya Gazebo gerçek pozu sınıflandırıcıya verilmez. Öz gövde
zarfı kaynak görselden türetilir; zarf içindeki yabancı nesne ayrıca ayırt
edilemez. Ham kaynaklar ve sınıflama özeti topic'lerde ayrı tutulur.

Core dosyaları ASCII workspace'e hash doğrulamalı kopyalanır;
`t3-core-inputs.json` çalıştırılan iki dosyayı kaydeder. T2 algoritmaları
değiştirilmedi. `--lidar-3d --perception-probe --obstacle-fixture
--obstacle-height .4` yalnız sabit sensör kabulünü çalıştırır. 40 cm kutunun
yaklaşık 5 cm'si yerin altındadır; görünen üst yüksekliği senaryodur. Son
dünya üreticisi engeli spawn yüksekliğine değil, kendi XY konumundaki
doğrulanmış 1 m collision üçgenine oturtur. İlk denemelerdeki spawn yüksekliği
varsayımı ham kayıtlarda korunur; eski veriler yeni yerleştirme sayılmaz.

Teknik çalıştırma:

```bash
bash scripts/build-t3.sh
bash scripts/run-t3.sh <çıktıdaki-ASCII-workspace> \
  --terrain /home/ahmetefesensoy/.cache/redline/t3/surface-bxw-v1/manifest.json \
  --delivered-rover --obstacle-fixture
```

İsteğe bağlı `--controller rpp`, aynı fizik/plancı/Stop zincirinde
Regulated Pure Pursuit karşılaştırması açar. MPPI varsayılandır; bu seçenek
MPPI kabulünün yerine geçirilmez. Her koşu `controller_profile` kaydeder.

`--obstacle-fixture`, 5 m ileride açıkça SCENARIO olan 1 × 1 × 3,5 m test
hedefi ekler. Bu hedef, yüksek 2D taramanın görebileceği şekilde seçilmiştir;
doğal kaya tespiti testi değildir. `--smoke --rotation-probe` Nav2 olmadan,
tek komut sahibiyle 8 saniyelik sınırlı yerinde dönüşü sınar.

`perception.log`: sensör, costmap, ilk/son rota ve komut zinciri istatistikleri.
`physical-motion.json`: yalnız değerlendirme için, yaklaşık 10 Hz fiziksel
poz örnekleri. Örnekler sürekli çarpışmasızlık kanıtı değildir.
`navigation_result.json`: gerçek action sonucu, tahmin ve fiziksel varış hatası.
Başarısız denemeler korunur; güncel sonuçlar
[doğrulama günlüğünde](VERIFICATION_LOG.md) ve
[geliştirme kaydında](../journal/log/2026-11-14-t3-rover-olcek.md) tutulur.

Paket testleri domain 78 ve koşuya özel Gazebo partition'ında çalışır;
canlı sürüş domain 77'de kalır. `test-namespace.json` bunu kaydeder.
Bu ayrım eklenmeden eşzamanlı test komutu karışan `t3-runtime-QQWvOR9I`
koşusu kabulden dışlanmıştır; ham başarısız sonuç ve `VALIDITY.json` korunur.
