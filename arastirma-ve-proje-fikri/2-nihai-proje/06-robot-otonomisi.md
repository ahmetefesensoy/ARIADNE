# 06 · Robot otonomisi (ROS → Unreal)

> REDLINE v3 nihai proje · Kılavuz bölümleri: §15 · [← 05](05-yazilim-mimarisi.md) · [← Nihai proje](README.md) · [07 →](07-unreal-ve-ekranlar.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 15. Robot otonomisi: ROS'ta yazılır, Unreal'da görünür

### 15.1 Bu ayrım mantıklı mı?
Evet. Bu, robotik simülasyonda standart ve doğru ayrımdır:
- **Fizik ve sensörler tek yerde.** Teker teması, eğim, LiDAR ve IMU Gazebo'da hesaplanır. Unreal ikinci bir fizik çalıştırırsa iki dünya ayrışır.
- **Gerçek robot yazılımı.** Nav2, ros2_control ve robot_localization gerçek robotlarda kullanılan yığındır. Aynı otonomi kodu ileride `gz_ros2_control` yerine donanım sürücüsüyle küçük bir gerçek rover'da da (JPL Open Source Rover) çalışabilir.
- **Unreal'ın işi insan:** astronot hareketi, habitat ekranları ve prova görünümü. Robotu ROS pozundan çizer, komutu ROS'a yollar.
- **Kayıt ve tekrar:** rosbag2/MCAP ile her koşu tekrar oynatılır. Unreal aynı kaydı canlıymış gibi gösterir.

Riskler ve karşılıkları:

| Risk | Karşılık |
|---|---|
| İki motorda arazi farklı | §6.5 tek dünya hattı ve 3 nokta yükseklik testi |
| Eksen ve birim hatası | tek dönüşüm fonksiyonu; 1 m küp ve 90° testleri |
| Ağ gecikmesi / kopma | tazelik alanları, watchdog, "güncel değil" gösterimi |
| Görsel ile algı uyumsuzluğu | algı Gazebo kamerasından yapılır; Unreal güzel görüntüsüne algı kutusu konmaz |
| Görev sırasında ROS çökmesi | replay modu; video ve sunum kayıttan |

Tek istisna (isteğe bağlı): **astronotun kask kamerası Unreal'da render edilir** (SceneCapture2D → JPEG → `CompressedImage`, 2 Hz, 640×480) ve ufuk eşleştirmeli konum belirleme için ROS'a gider (§18 M11). Bu durumda Unreal bir sensör kaynağı olur ve kalibrasyonu ayrıca kayıtlanır.

### 15.2 Rover sürüş modları ve komut sahipliği
- **Modlar:**
  - **Manuel:** Unreal'dan klavye/gamepad.
  - **Destekli:** manuel komut + engel yavaşlatma/duruş.
  - **Otonom:** hedef veya koridor; Nav2 sürer.
- Her araçta tek komut sahibi olur. Komutlar aynı sürüş topic'inde yarışmaz: önce `command_authority`, sonra Nav2 Collision Monitor, sonra sürüş.
- **Geçiş sözleşmesi:** otonomi iptal → sıfır komut onayı → yeni sahip onayı. Otonomiye dönüşte güncel poz, hedef ve harita yeniden değerlendirilir. Kopan istemcinin eski komutu yeniden yürütülmez.
- E-stop ve sensör tazeliği denetimi moddan bağımsızdır.

### 15.3 Rover otonomi yığını

| Katman | Paket / yöntem | Not |
|---|---|---|
| Konum | `robot_localization` EKF (teker + IMU + görsel odometri isteğe bağlı) | Mars'ta GPS yok; `map → odom` hizası saha manifestinden |
| Yerel harita | LiDAR yükseklik ızgarası (`grid_map` [?] veya kendi mapper'ımız) | eğim, pürüzlülük, adım yüksekliği |
| Küresel maliyet | DEM eğimi + HiRISE kaya önseli + hücre σ | rover kısıtları insandan ayrıdır |
| Planlayıcı | Nav2 Smac Hybrid-A* veya Smac 2D; uzun rota için redline_core | 6 tekerli dönüş kısıtı |
| Kontrolcü | Nav2 MPPI veya Regulated Pure Pursuit | Mars hızı 0,1–0,5 m/s |
| Davranış | Nav2 Behavior Tree: yeniden plan, geri çekil, yardım iste | "yardım iste" UI'da görünür |
| Güvenlik | Collision Monitor, watchdog, eğim/devrilme sınırı | sertifikalı güvenlik değildir |
| Aktif algı | bilgi değeri (§4.5) ile gözlem noktası seçimi | "nereye bakmalıyım" |

Önceki demo ne öğretti (kod taşınmaz, yeniden yazılır):
- DEM eğimi 18° üzeri kapalı, 8 komşulu A* ve yönlü tırmanma maliyeti.
- LiDAR yakın yükselişte ileri hareketi kesme.
- Konum 1 s veya LiDAR 1,5 s eskirse sıfır komut; 15 s hareketsizlikte görev duraklatma.
- IMU yönüyle teker odometrisi.

Bunlar SLAM, EKF veya dinamik costmap değildi. v3'te Nav2 ve EKF ile değiştirilir.

### 15.4 Drone (scout)
- **Görev evreleri:** kalkış izni → koridor tarama → gözlem → dönüş → iniş. Kalkış ve iniş ayrı görevlerdir; harita üretildi diye uçuş başarılı sayılmaz.
- **Platform:** ilk sürümde duran rover yanındaki pad. Rover üstüne iniş gelecek tasarımıdır; Ingenuity'nin kanıtlanmış özelliği diye sunulmaz.
- **Fizik:** Gazebo multicopter sistemleri; Mars g = 3,721 m/s². İtki katsayısı REMS'ten türetilen ρ ile ölçeklenir (§4.5). Bu basitleştirilmiş modeldir; Mars rotor aerodinamiği doğrulaması iddia edilmez.
- **Konum:** IMU + kamera + altimetre; GPS yok.
- **İşler:** kör geçidi önden görme, yüzlek fotoğrafı, çelişkili hücreyi yeniden gözleme, dönüş koridorunu kontrol, geçici iletişim rölesi (gelecek tasarım).
- **Kural FR-14:** drone EV'lere 30 m'den yakın uçmaz ve her an rezervle iniş noktasına dönebilir [K].
- **Arşiv karşılığı:** Ingenuity'nin Jezero'da Perseverance için keşif uçuşları [K].

### 15.5 Kol ve numune durum makinesi (isteğe bağlı derinlik)
`hedef seçildi → erişim doğrulandı → ön konum → alıma hazır → alım denemesi → alım doğrulandı → kapta → kayıt tamamlandı`. Her aşamanın hata ve iptal sonucu vardır.
- MoveIt 2 erişim ve çarpışmasız yaklaşımı planlar. Temas ve kazma ayrı modeldir. İlk sürümde nesne tabanlıdır: doğru nesne + doğru kap.
- Aynı komut iki kez gelirse ikinci numune alınmaz; komut kimliği ve sonuç uzlaştırması yapılır.

### 15.6 Astronot proxy'si ve refakat
- Unreal astronot pozu `/astronaut_{1,2}/pose` olarak ROS'a gelir. Gazebo'da kinematik proxy olur ve rover sensörleri onu görür.
- Rover insanı kendi sensöründen veya belirsizlik taşıyan ekip konum bildiriminden izler; gizli ground truth kullanmaz.
- **Refakat kuralları:** takip mesafesi, görüş kaybında davranış, insanın yolunu kapatmama.
- **Hareketli sığınak:** basınçlı rover (SEV görseli) istasyon planını `rover_placer`'dan alır (§18 M8). HUD'da rover'ın gelecek konumları "hayalet" olarak görünür.

### 15.7 Unreal'a ne gider, Unreal'dan ne gelir

| ROS → Unreal | Unreal → ROS |
|---|---|
| rover/drone pozu, eklemler, kamera önizlemesi | astronot pozları |
| hücre deltaları, kırmızı/sarı çizgi, rota | manuel sürüş komutu (mod manuelken) |
| görev durumu, alarm, kural ihlali | hedef seçimi, görev isteği, iptal |
| RAD/REMS replay değerleri, güneş yönü | istasyon/numune notu, fotoğraf olayı |
| robot "yardım isteği" | (isteğe bağlı) kask kamerası karesi |
