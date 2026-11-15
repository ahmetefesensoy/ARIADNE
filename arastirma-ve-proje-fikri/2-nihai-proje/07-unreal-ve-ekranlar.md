# 07 · Unreal, RViz, Open MCT ve ana ekran

> REDLINE v3 nihai proje · Kılavuz bölümleri: §7, §17 · [← 06](06-robot-otonomisi.md) · [← Nihai proje](README.md) · [08 →](08-3d-varliklar.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 7. Unreal tarafı

### 7.1 ROS bağlantısı
- **Ana yol:** `rosbridge_suite` (Jazzy dalı mevcut [D]) + Unreal'ın yerleşik WebSockets modülüyle C++ istemci. Protokol JSON'dur, örneğin:
  `{"op":"subscribe","topic":"/rover_1/odom","type":"nav_msgs/msg/Odometry","throttle_rate":100}`
- **WSL ağı:** Windows'tan WSL'deki rosbridge'e `localhost:9090` genelde çalışır (WSL2 localhost yönlendirmesi). Çalışmazsa WSL IP'si veya mirrored networking. İlk saatte test et.
- **Görüntü:** düşük hızda `CompressedImage` base64 akışı. Daha yüksek hız gerekirse `web_video_server` ile ayrı MJPEG [?].
- **Alternatifler:** rclUE (README Windows'u desteklemiyor diyor [K]; ana yol yapılmaz); Zenoh (`rmw_zenoh` veya zenoh-c istemcisi [?]).
- **Replay modu:** rosbag2 kaydı aynı köprüden oynatılır. Video ve sunum deterministik olur; canlı sistem çökse de demo çalışır.

### 7.2 Unreal bileşenleri
| Bileşen | Teknik | İş |
|---|---|---|
| Harita masası (habitat) | UMG + render target, `WBP_MapTable` | katmanlar, hücre kartı, kırmızı/sarı çizgi, robot görevleri |
| Tablet | UMG, aynı veri modeli | brifing, istasyon kartı, PET timeline |
| HUD | minimal UMG | kalan pay, sonraki istasyon, dönüş yönü, alarm |
| Prova görünümü | Landscape/statik mesh + astronot karakteri | astronot gözünden traverse |
| POV swipe | iki render target | Navcam karesi ↔ Unreal render |
| Ölçek merdiveni | Sequencer veya etkileşimli zoom | SIM 3292 → CTX → HiRISE → hücre |
| Duyarlılık grafiği | UMG grafik | "kararı hangi varsayım değiştiriyor" |
| Güncel durum paneli | UMG | kaynakların son kaydı ve yaşı |
| Debrief | Sequencer + rosbag replay | karar noktaları |

- Mars yerçekimi: World Settings'te Z yerçekimi −372,1 cm/s². Astronot animasyonu buna göre ayarlanır.
- Alternatif arazi: Cesium for Unreal + Cesium Mars (Gale için ~1 m arazi ve 25 cm görüntü belirtiliyor [K]). Görsel bağlam için iyidir. Ama Gazebo ile aynı geometri ve çevrimdışı çalışma kontrol edilmeli; ana yol 6.5'tir.

---

## 17. Ekranlar ve grafikler: RViz, Open MCT ve Unreal ana ekran

### 17.1 Kim neyi gösterir

| Araç | Kim için | Ne gösterir | Durum |
|---|---|---|---|
| **Unreal ana kontrol merkezi** | jüri, kullanıcı | harita masası, robot konsolu, bilim masası, görev duvarı | ana ürün |
| **NASA Open MCT** | operasyon/analiz | canlı ve geçmiş telemetri, zaman çizelgeleri, grafikler | gerçek NASA görev yazılımı; Mars 2020 dahil kullanıcıları var [K] |
| **RViz** | geliştirici | TF, LiDAR, costmap, Nav2 planı | geliştirme profili |
| **Foxglove / PlotJuggler** | geliştirici | MCAP kayıtları, zaman serileri, hata ayıklama panoları | geliştirme profili |
| **Web harita** | herkes | statik katmanlar, EVA kartı | dışa aktarım |

### 17.2 Open MCT'yi bağlamak
1. `telemetry_adapter` düğümü seçili topic'leri Open MCT telemetri nesnelerine çevirir: doz hızı, sarflar, pay dakikası, rover durumu, kural ihlalleri.
2. Geçmiş veri için küçük bir depo kullanılır: SQLite veya MCAP okuyucu.
3. Open MCT tarafında bir eklenti (JavaScript) roslibjs ile rosbridge'e veya foxglove_bridge'e bağlanır. Canlı veri `subscribe`, geçmiş veri `request` ile gelir.
4. Görünümler: Plot, Telemetry Table, Time Conductor (LMST ve UTC), Imagery (rover kamerası), Fault Management (kural ihlalleri).
5. **Unreal içine gömme:** Unreal'ın Web Browser eklentisi (CEF) ile Open MCT sayfası habitat ekranında bir widget olarak açılır. UE 5.8.4 paketlenmiş uygulamada çalıştığı test edilmeli [?]. Çalışmazsa grafikler UMG'de yerel olarak çizilir ve Open MCT ayrı monitörde açılır. Temel ekranlar gömmeye bağlı kalmaz.

### 17.3 Unreal ekranlarındaki grafikler

| Ekran | Grafikler |
|---|---|
| Harita masası | katman bindirme, hücre kartı, kırmızı/sarı çizgi, rover hayalet konumları, ölçek merdiveni |
| Görev duvarı | PET zaman çizelgesi, pay dakikası (EV1/EV2), sınırlayan sarf, kural durumu, veri yaşı |
| Uzay havası | RAD doz hızı (gerçek replay) + %25 eşik çizgisi + kümülatif doz, alarm anı |
| Robot konsolu | rover/drone kamera, mod, sağlık, görev kuyruğu, "yardım isteği" |
| Bilim masası | APXS/CheMin hata çubuklu karşılaştırma, istasyon posterior grafiği (§18 M5), numune kaydı |
| Duyarlılık | tornado grafiği ("kararı hangi varsayım değiştiriyor") |
| İletişim | görüş hattı haritası, bağlantı durumu, DTN kuyruğu ve ışık süresi bandı (isteğe bağlı) |
| Habitat sistemleri (isteğe bağlı) | servis hattı şeması, vana, basınç/akış (eski Görev 4) |

### 17.4 Unreal'da dört görünüm
1. **Astronot:** birinci şahıs, HUD/tablet, işaretleme, fotoğraf/not, robota görev verme.
2. **Rover operatörü:** kamera, harita, manuel/destekli/otonom mod, kol ve numune ekranı.
3. **Hava keşfi:** kamera önizlemesi, uçuş koridoru, gözlem kapsamı, dönüş/iniş.
4. **Görev masası:** NASA katmanları, ortak harita, görev bağımlılıkları, olay kaydı, replay.

İlk sürümde tek kullanıcı görünümler arasında geçer. Çok kullanıcılı roller (EV1 oyuncusu, IV operatörü) aynı görev otoritesine sonradan bağlanabilir.

### 17.5 Dünya konsolu ve bilim arka odası (isteğe bağlı, v0.3'ten)
- **MCC görünümü:** "son alınan durum" ile "tahmini şimdi" yan yana durur. Işık süresi bandı ve LMST/UTC saatleri gösterilir.
- **Bilim arka odası:** posterior grafiği, istasyon kartları, gecikmeli not gönderme.
- BASALT ve NASA Ames xGDS iş akışından esinlenmiştir [K].
