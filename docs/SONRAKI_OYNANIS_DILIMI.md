# EVA'dan saha keşfine geçiş

15 Kasım 2026 · Kullanıcının son yönlendirmesi ve mevcut kaynak denetimi.
Bu belge yeni alanların tamamlandığı anlamına gelmez. Mesafeler ve görsel
hedefler SCENARIO tasarım önerileridir; NASA ölçümü veya onaylı yerleşim değildir.

Çalışan akış, tek EVA'nın 12 adımıdır. Uzun birden fazla bölüm, araçla ulaşım,
gelişmiş robot ekranları ve son görsel kalite henüz bu akışın tamamı değildir.

| Alan | Gözlenen/uygulanmış durum | Sonraki ihtiyaç |
|---|---|---|
| Görev | Brifing, scout, rota kararı, numune, ölçüm, istasyon, rover/LIBS, DAN, sondaj, teslim, değerlendirme, debrief. | Ayrı saha bölümleri, önceki kararların yeni göreve etkisi, birbirinden farklı deneyler. |
| Rover | Gerçek Gazebo hareketi + Nav2 sonucu Unreal'a yansıyor. Son kabulde 6,59 m hareket. | Habitat–saha uzun rota, alçak engel algısı/yeniden plan kabulü, performans. |
| Scout | Fiziksel kalkış/tarama/dönüş/iniş geçti. Gözlem adaptörü açık SIMULATED truth kullanıyor. | Sensör algısı, mobil operasyon noktasından yeni sorti, güvenli iptal/dönüş. |
| Veri ekranı | Görev, bileşim ±1σ, numune kökeni/analiz yeri, temel robot durumu ve RAD çizim altyapısı. | Kamera, haritada gerçek/planlanan iz, costmap, DAN posterior ısı haritası, sondaj zaman serileri ve ürün karşılaştırma. |
| Astronot/kapı | Yürüme, senaryo koşusu, numune sunumu, çift panelli kapı. | Koşu klibi, idle/yürüme/koşu harmanlama, dönüş/ayak yerleşimi, kamera ve etkileşim giriş/çıkışları. |
| Kum/atmosfer | Önceki gösteride temel tane/dalga ayrıntısı, iz/decal ve görsel çökme; inişte dört saydam toz düzlemi. | Rüzgâr, rotor, ayak ve teker temasından üretilen parçacıklar; mesafeye göre malzeme ayrıntısı; sahneler arası tutarlı pozlama. |
| Ulaşım | Alan profili hedefleri zaten 280–430 m mesafede seçiyor. Odalar yakında; rover ilk hedefin 10 m batısında ön konuşlanıyor. | Üs ölçeği, uzak saha ve PR ulaşımı. Testteki kısa robot hareketi uzun otonom yolculuk kanıtı değildir. |

## Yerleşim ve yolculuk önerisi

Gerçek rover/astronot/kapı boyutları korunur. Veri tabanlı arazi ölçeği
değiştirilmez. Yerleşim yeni doğrulanmış çarpışma desteği üzerinde taşınır.

| Bölge | Önerilen mesafe/bağlantı | Oynanış ve bağımlılık |
|---|---|---|
| Komuta–yaşam–laboratuvar | Aynı basınçlı üs, 20–40 m koridor geçişleri | Pencereler, farklı oda işlevleri, okunur yönlendirme ve gerçek kapı geçişi. |
| Rover bakım/çıkış noktası | Üsten 80–120 m | Araca hazırlık, ekipman yükleme ve dış saha açılışı. Yer/zaman tüketimi görünür. |
| İlk EVA sahası | Üsten yaklaşık 300–430 m | Mevcut dönüş alanı bandında yaya bölüm; gerçek arazi, güzergâh ve dönüş payı kontrolü. |
| İkinci uzak saha | Yaklaşık 800–1200 m, PR ulaşımı | Önce PR barınak/konum/EV2/link entegrasyonu ve bu alanın ince çarpışma desteği gerekir. Mevcut 20 dk dönüş alanının içinde kabul edilemez. |

Uzun transfer için basınçlı rover ve atlanabilir yolculuk sahnesi önerilir.
Tam sürüş seçilirse Gazebo robot otoritesi sürer. Atlama seçilirse görev
saati, sarflar, RAD eşlemesi ve varış konumu birlikte güncellenir; sıçrama
`SCENARIO / yolculuk atlandı` kaydıyla tutulur. Aktif navigasyon/ölçüm sonucu
atlamadan başarı çıkarılmaz. Bu servis güncel kampanyada uygulanmış değildir.
Temel sözleşme `proje.md` §4.3'tedir; PR/EV2 tarafı §18 T9'a bağlıdır.

Scout yeni saha için yeniden konuşlanmalıdır: güncel ev noktası sabittir ve
uçuş menzili kısıtlıdır. Unreal görselini uzağa taşımak Gazebo sorti başlangıcı
veya yeni TF orijini oluşturmaz. Bir sonraki operasyon noktası kaydedilip
robot/insan mesafesi, pil, fiziksel poz ve kontrol sahipliği yeniden doğrulanır.

## Uygulama sırası ve gözlenebilir bitişler

1. **Aynı oturumda izlenebilir otonomi.** Pasif RViz, aynı ROS domain'i ve tek
   Gazebo dünyası. Gerçek spawn'a kamera; doğru yükseklikte harita/rota kopyaları.
   Model, LiDAR ve costmap güncel görünür. Hedef sahibi kampanya olarak kalır.
   Yeni başlatıcı desteği bu tur uygulanır; hareketli rota ayrıca gözlenmelidir.
2. **Uzun güzergâh ve süre.** Rover ön konuşlanma yerine doğrulanmış bir çıkış
   noktasından saha hedefine gider. Önce uzun rota + engel + iptal/başarısızlık
   + fizik/duvar oranı ölçülür. Yakın çevrede ≥0,9× oranı bir çalışma hedefidir,
   sağlanmış sonuç değildir. Son kabulde yaklaşık 0,49× gözlendi.
3. **Tek tam görev panosu.** Harita, robot kameraları ve durum; ayrı bilim,
   çevre ve numune sayfaları. Kaynak/zaman/birim/eskilik gösterilir. Bir ürün
   kaydını grafiğe çevirmek, bulunmayan sensör serisini üretmek anlamına gelmez.
4. **Hareket ve kum.** Idle/yürüme/koşu geçişleri, ayak teması ve etkileşim
   kamerası; ardından kumun yakın/orta/uzak ayrıntısı ve parçacıklar. Toz miktarı
   hız, teker teması/kayması, ayak basışı ve rotor durumundan sürülür; estetik
   rüzgâr parametreleri SCENARIO olarak kalır. Görsel kum çökmesi arazi DEM'ini
   veya Gazebo zemininin fiziğini değiştirmez.
5. **PR ve yeni bölüm.** Yeni konumda güvenli barınak/dönüş hesabı, ulaşım ve
   atlanabilir görev öncesi sahne. Bu aşamadan sonra ikinci saha açılır.

Bu sırada müzik/APXS/kaçak üzerine çalışan diğer oturumun dosyaları, Git/GitHub
ve yeni model üretim kredileri bu işin kapsamında değildir.

Kanıt tabanı: [kampanya kaydı](verification/CAMPAIGN_PREVIEW.json),
[oynanış](CAMPAIGN_PLAYABLE.md), [önceki kum gösterisi](ROVER_PREVIEW.md).
