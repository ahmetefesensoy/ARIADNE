# PATHFINDER-G · NASA Space Apps 2026

Challenge: Interplanetary Survival Guide: Martian Map

## Dosyalar
| Dosya | Ne |
|---|---|
| index.html | Tanıtım sayfası (Türkçe, siyah tema, 3B Mars girişi). Yayına alınacak ana sayfa. |
| simulasyon.html | Rover simülasyonu (Türkçe). Tanıtım sayfasındaki "Uygulamayı aç" buraya gider, simülasyondaki "← Tanıtım sayfası" geri döner. |
| index.src.html / simulasyon.src.html | Düzenlenecek kaynaklar. Veriler __DEM__ / __CTX__ / __GLOBE__ yer tutucularıyla ayrı durur. |
| build.py | Derleme betiği: `python3 build.py` kaynakları .b64 verileriyle birleştirip index.html ve simulasyon.html üretir. |
| dem.b64 / ctx.b64 / globe.b64 | Gömülü NASA verisi (JPL Mars Trek: HiRISE DEM ve CTX 96×96; Viking MDIM 2.1 renkli küre 1024×512). |
| mars_nasa_viking_8k.jpg / _4k.jpg | NASA JPL Mars Trek Viking MDIM 2.1 renkli mozaiği, 8192×4096 ve 4096×2048 (zoom 4, 512 karo). Sayfa önce gömülü 1024 px'i gösterir, sonra cihaz destekliyorsa 8K'yı, değilse 4K'yı yükler. HTML ile aynı klasörde durmalı. |
| llms.txt, robots.txt, sitemap.xml | Yapay zeka aramaları ve SEO için. sitemap.xml şablon. |
| eski-surumler/ | Önceki sürümler. |

İki HTML dosyası aynı klasörde durmalı; bağlantılar göreli.

## Yayına almadan önce doldurulacaklar
1. Ekip bölümü: index.src.html içinde "EKİP ŞABLONU" yorumunun altındaki "Ad Soyad", rol ve LinkedIn/GitHub href'leri (boş bağlantılar görünmez).
1b. Jüri bağlantıları: index.src.html'de `const PROJECT = { github, video, slides }`. Doldurulanlar sitede (son bölüm ve alt bilgi) otomatik görünür.
2. Alan adı: index.src.html'deki "TODO after deploy" satırına canonical, og:url, og:image; sitemap.xml'de ALAN-ADINIZ; robots.txt'deki Sitemap satırı.
3. Uygulama başka bir adresteyse: index.src.html'de APP_URL.

## Simülasyon notları
- Hedefler doğrulanmış koordinatlarda: Pahrump Hills 4,676°G 137,379°D (HiRISE ESP_039280_1755), boxwork bölgesi 4,843°G 137,298°D (HiRISE PSP_001752_1750 merkezi, NASA PIA26306).
- Sol sayısı: sol başına ~100 m otonom sürüş varsayımı (SOL_M sabiti).
- Radyasyon: MSL RAD 0,67 mSv/gün, gökyüzü görüş faktörü (12 azimut) ve varsayılan +%4/km yükseklik terimiyle ölçeklenir.
- Mobilde Mars yürüyüşü paneli artık görünür.
