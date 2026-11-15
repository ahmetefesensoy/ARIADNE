# 09 · Kalite, test ve doğrulama durumu

> REDLINE v3 nihai proje · Kılavuz bölümleri: §19, §14 · [← 08](08-3d-varliklar.md) · [← Nihai proje](README.md) · [10 →](10-ekip-akisi-ve-teslim.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 19. Kalite, test ve çalışma profilleri

- **Analitik altın testler:**
  - düz düzlemde walkback = mesafe × birim maliyet
  - silindirik çukurda F = 1 − sin^(α+1) h
  - yokuş yukarı/aşağı walkback asimetrisi
  - Golombek integrali ile kapalı form karşılaştırması
- **Özellik tabanlı testler (Hypothesis):** W ≥ 0, üçgen eşitsizliği, küçük ızgarada Dijkstra = kaba kuvvet.
- **Entegrasyon (`launch_testing`):** nominal senaryoda hiçbir kural tetiklenmez. SEP senaryosunda FR-04 sağlanır.
- **Sözleşme testleri:** eksen/birim, 3 nokta yükseklik, saat dönüşümü, stale komut reddi.
- **Determinizm:** aynı senaryo ve tohum, aynı ihlal dizisini üretir. Her koşu MCAP ile kaydedilir.
- **CI:** Unreal olmadan, görsel arayüzsüz senaryo regresyonu.
- **Performans bütçeleri (v0.3 [K]):**
  - walkback alanı (2 m, 3×3 km) ≤ 1,5 s
  - D* Lite ≤ 0,5 s
  - Monte Carlo 1000 koşu ≤ 60 s
  - HUD 10 Hz
  - Unreal ≥ 30–45 FPS
- **Çalışma profilleri:**
  - **Geliştirme:** RViz + Foxglove + Gazebo GUI.
  - **Kullanıcı:** Gazebo başsız, Unreal + Open MCT.
  - **Kayıt inceleme / zayıf laptop:** yalnız replay; canlı fizik iddia edilmez.
  - **Çevrimdışı:** internet API'si gerekmez.
- **Tek başlatma betiği:** arka uç servislerini hazır olma sırasıyla açar, sonra Unreal'ı başlatır. Hazır olma kontrolü odometri, TF, LiDAR, kamera ve IMU'dur.

### 19.1 Habitat ve saha mekânları (v2'den)

| Kod | Mekân | İşlev |
|---|---|---|
| H01 | Ana kontrol merkezi | harita masası, robot konsolu, bilim masası, görev duvarı |
| H02 | Airlock / hazırlık | çıkış-dönüş önkoşulları, ekipman listesi |
| H03 | Rover garajı | servis, uç takımlar, kap rafı |
| H04 | Drone pad'i | kalkış/iniş |
| H05 | Numune laboratuvarı (isteğe bağlı) | kap kabulü, hazırlık, ölçüm (model etiketli) |
| H06 | Servis modülü (isteğe bağlı) | vana/hat senaryosu |
| S01–S05 | Saha noktaları | ön inceleme, alternatif koridorlar, regolit alanı, sondaj alanı, röle noktası |

### 19.2 Ses ve görsel yön
- **Ses:** NASA Sounds of Mars kaynaklı ambiyans. Fan, sondaj, vana ve UI sesleri kendi kaydımız veya açık lisanslı. MetaSounds ile yüke göre değişir. Alarm her zaman metin ve görsel karşılık da taşır.
- **Görsel:** sıcak toprak tonları, okunur katman ayrımı, kontrollü toz. Görev nesnesinin okunurluğu post-process efektlerinin önünde gelir.
- **Performans:** RTX 5080 / 16 GB VRAM, 30 FPS kararlı hedef [K]. Kamera akışları düşük çözünürlükte tutulur.

---

## 14. Doğrulama durumu

**Bu oturumda doğrulandı [D]:**
- RAD sol 242 ve sol 4190 dosyaları ve değerleri
- boxwork kampanyası ve sol 4190 rover konumları (MMGIS)
- HiRISE DTM kaydı (STAC)
- rosbridge jazzy dalı
- space-ros Curiosity paketleri
- NASA-3D-Resources'ta Curiosity, Astronaut, Habitat Demonstration Unit ve Space Exploration Vehicle
- Perseverance ve Ingenuity 3D sayfaları
- PX4 gazebo modelleri deposu
- "may consider" ifadesi (stage 2'de iki üye)

**Doğrulanmadı [?]:**
- resmî challenge sayfası ve 2026 jüri rehberi
- DONKI ve MAVEN Mayıs 2024 gözlemi
- Golombek kaya bolluğu ürünü
- CRISM gözlem ID'leri
- SEXTANT/BASALT sayıları
- NASA 600 mSv
- Gazebo DEM heightmap desteğinin Mars datumu
- rosbridge ROS 2 action desteği
- `web_video_server` Jazzy
- Space ROS'un Jazzy uyumu
- Cesium Mars'ın çevrimdışı kullanımı
- teslim saatinin kesin değeri

Konsey karar ve değerlendirme çıktılarının [kalıcı araştırma kopyası](../3-arastirma/16-konsey-v3-karari.md). Özgün oturumun TEMP yolu ve dosya hash'leri kaynak kaydında korunur; tekrarlanan uzun prompt kopyaları aktarılmadı.
