# REDLINE: karar, veri ve 39 saatlik kapsam

**Projenin merkezine geri dönüş kararını koyuyoruz.** NASA arazi verisi üzerinde, bir bilim durağına uğramanın dönüş payına etkisini gösteriyoruz. Rover bu haritayı yerel gözlemlerle iyileştiren keşif aracı. Gazebo gösterimi bu kararın hareket eden kanıtı olacak.

## Jüri için çözülmesi gereken fark

Bugünkü gerçek arazi + A* + LiDAR demosu bir robotik başlangıçtır. Tek başına Space Apps'e özgü bir katkıyı göstermeye yetmez. Katkı, aynı başlangıç ve bilim hedefinde şu iki sonucu karşılaştırınca anlaşılır: mesafeyi azaltan rota ve dönüş rezervini koruyan rota. Başarı ölçütü güzel görüntü sayısı değil; hedefe varış, dönüş payı, mesafe/süre farkı ve yeniden kararın nedenidir.

Üç dakikalık gösteri: gerçek haritayı ve kaynaklarını aç; bilim durağı seç; iki rotayı karşılaştır; roverın sensörleriyle yerel durumu göster; süre veya O₂ varsayımını azaltınca sınırın daralmasını ve gerekirse hedefin reddedilmesini göster. Böylece “neden bu yol?” sorusu sayıyla cevaplanır. Hedeflerin bilim değeri ayrıca NASA görüntüsü/günlüğüyle belgelenmeli; mevcut dört demo durağı bu iddiayı taşımaz.

## Verilerin görevleri

| Veri | Kullanım | Bugünkü durum ve sınır |
|---|---|---|
| NASA/JPL–USGS Gale DEM v3 | Yükseklik, eğim, rota ön bilgisi | Gerçek 2 × 2 km kırpım indirildi ve Gazebo'ya işlendi; karma kaynak çözünürlüğü var |
| Kayıtlı HiRISE LRGB mozaiği | Coğrafi bağlam ve arazi dokusu | Aynı koordinat penceresi indirildi; LRGB bir mineral etiketi değildir |
| Simüle LiDAR / kamera / IMU | Yerel gözlem ve denetleyici testi | Çalışıyor; NASA'nın Mars'ta ölçtüğü LiDAR verisi değildir |
| [NASA AI4Mars](https://data.nasa.gov/dataset/ai4mars-a-dataset-for-terrain-aware-autonomous-driving-on-mars) | Kamera görüntüsünde soil/bedrock/sand/big rock ayrımı | Eğitim adayı; eğitim arşivi ve model henüz bu projede yok |
| Curiosity RAD ve uzay havası | Daha sonraki zaman çizelgeli stres senaryosu | Bu sürüme bağlanmadı; ölçüm yeri ile varsayımsal EVA yeri ayrılmalı |

İlk iki ürünün kaynakları: [USGS DEM kataloğu](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), [USGS görüntü kataloğu](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm). Kesin URL, koordinat, hash ve dönüşümler ROS paketindeki `TERRAIN_PROVENANCE.json` içinde. Seçili saha Gale'dedir; doğrulanmadan “boxwork sahası” diye sunulmayacak.

## Eğitilecek model

Kamera için dört sınıflı küçük bir semantik bölütleme modeli seçilir. Başlangıç adayı küçük bir encoder kullanan U-Net; önce düşük çözünürlüklü pilot, sonra gerçek süre/VRAM ölçümü. A* öğrenilmeyecek. DEM fiziksel geometriyi, model zemin türü olasılıklarını, LiDAR da yakın yüzey geometrisini sağlayacak. Kum tahmini maliyeti yükseltebilir; tek başına “geçilir/geçilmez” güvenlik hükmü vermemeli.

[AI4Mars'ın özgün çalışması](https://openaccess.thecvf.com/content/CVPR2021W/AI4Space/html/Swan_AI4MARS_A_Dataset_for_Terrain-Aware_Autonomous_Driving_on_Mars_CVPRW_2021_paper.html) bu dört sınıfı ve uzman etiketli değerlendirmeyi anlatır. NASA kataloğundaki toplam etiket sayısı, indirilecek her sürümün görüntü sayısı değildir. İndirilen sürümün README'si, lisansı, sınıf kodları ve dosya hash'leri eğitim başlamadan kaydedilmeli.

Eğitim planı:

1. Görüntü–maske eşleşmesi ve geçersiz pikseller doğrulanır; mevcut uzman test kümesi eğitimden ayrı tutulur.
2. Geliştirme kümesi görüntüleri rover/sol/saha gruplarına ayrılır. Aynı sahnenin yakın karelerini rastgele train/validation'a dağıtmak engellenir.
3. Önce küçük alt kümede veri hattı sınanır. Etiketler nearest-neighbour ile ölçeklenir; sınıf dengesizliği izlenir.
4. mIoU ve sınıf başına IoU, özellikle sand/big rock geri çağırımı raporlanır. Piksel doğruluğu tek başına kullanılmaz. En az bir başarısız örnek gösterilir.
5. Hedef makinede çıkarım süresi ölçülür. Canlı entegrasyon yetişmezse gerçek görüntü üzerinde kayıtlı çıkarım, ROS demosundan ayrı ve açıkça gösterilir.

Simülasyon kamerası yörünge dokulu yüzeyi görüntüler; gerçek rover NAVCAM verisiyle aynı değildir. Bu yüzden simülasyonda düzgün görünen bir renk maskesi gerçek Mars başarısı kanıtı olamaz. Bir modelin yayımlanmış başarı oranı da bizim sonucumuz olarak kullanılamaz. Mevcut RTX 5080 eğitim için değerlendirilebilir; eğitim süresi ölçülmeden vaat edilmeyecek.

## Sonraki kod işleri

Önce LiDAR noktalarını yerel yükseklik/pürüzlülük gridine dönüştür. Kullanıcının branch'indeki `terrain_mapper` ve `TerrainLayer` bunun için incelendi; mevcut duruş zarfı bunların yerini tutmuyor. Sonra yeni engel gözlemiyle global DEM rotasını yerelde yeniden planla. İlk uzun turda ortaya çıkan ciddi sapma için IMU yönüyle desteklenen teker kestirimi eklendi ve deneysel yan sürtünme artırıldı. Daha uzun rotalar için kayma ölçümü, konumlama ve belirsizlik hesabı hâlâ gerekli.

EVA karar katmanı ayrı bir insan hız/tüketim modeli kullanmalı. Roverın 0,45 m/s hızı astronot hızı değildir. İlk modelde süre ve O₂ tüketimi açık varsayımlardır. Bir nokta için seçilmiş dönüş yolunun bütün kaynak sınırlarını karşıladığı gösterilir. Ayrı ayrı en iyi süre ve en iyi O₂ yollarını tek bir varmış gibi birleştirmek hatalıdır.

## 39 saatlik teslim sırası

| Süre | Teslim |
|---|---|
| 0–5 saat | Tek AOI, provenans, DEM/ortofoto ve tekrarlanabilir açılış |
| 5–12 saat | Hedefe sürüş, LiDAR görünümü, engel/eskimiş veri testi ve rota karşılaştırması |
| 12–21 saat | Açık varsayımlı EVA süre/O₂ hesabı, ortak dönüş yolu ve kırmızı sınır |
| 21–27 saat | Gerçek görüntüde AI4Mars küçük pilotu; yetişmezse çalışan çekirdek korunur |
| 27–33 saat | Belgeli iki bilim hedefi, başarısız senaryo ve ölçüm tabloları |
| 33–39 saat | Kullanıcı akışı, kaynak kartları, açılış provası ve kısa video |

Bu sıralama planlama tahminidir. Yeni ROS altyapısını genişletmek veya sıfırdan büyük ağ eğitmek, dönüş kararının önüne geçmeyecek. Uçuş güvenliği, gerçek O₂ doğruluğu ve gerçek Mars çekişi iddiası bu prototipin dışında kalır.
