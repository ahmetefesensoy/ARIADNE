# 2026-11-14 — T1 BXW veri hattı

14 Kasım 2026, 13:20 (+03:00), Europe/Istanbul.

Kullanıcının son gönderdiği uygulama speki esas alındı. `docs/proje.md` ile karşılaştırmada yerel bağlantılar ve satır sonları dışında metin farkı yok. GitHub işlemleri kullanıcıya bırakıldı; bu kayıttaki çalışma yereldir. Tasarım, 3D, Tripo ve yeni ROS/Unreal düğümü yapılmadı.

**Yapılanlar:** `config/sites.yaml`, `products.yaml`; HEAD-only katalog; HTTP Range ile sınırlı pencere; Mars WKT kontrolü; cos(enlem) içeren yerel ENU yaklaşımı; 1/4 m çıktılar; çok tabanlı eğim, düzleme göre pürüzlülük; kaynak/çıktı hash önbelleği; üç nokta sayısal QA, histogram, PNG ve HTML. Saf dizi `sigma` fonksiyonu yalnız ikinci DTM ve açık hizalama önkoşuluyla çalışır; gerçek sigma katmanı üretilmedi.

**Kanıt:** `bash scripts/test-data.sh` → **224 geçti, 0 hata/başarısız/atlanan**, 9,66 s. Rapor `test-results/data-run-1k6K8jYU/python.xml`. İki uyarı yalnız coğrafi referansı olmayan QA PNG önizlemesini yazma/okumadan geldi; Mars raster CRS hatası değildir. Testlere analitik düzlem, 60° enlemde cos düzeltmesi, nodata/NaN/Inf, bellek sınırları, gerçek loopback HTTP Range, bozuk kaynak/çıktı, hash/idempotence ve source→ENU→derive→QA entegrasyonu dahildir.

Canlı Gale crop: 3.001 × 3.011 Float32, 23.810.074 bayt, SHA256 `f6ad53021e4835cc439cf0848e3c1346bdeffdc4079dd7aa6ea4126d254004be`. Tam 3,87 GB mozaik indirilmedi. Kaynak row-strip olduğu için dokunulan blokların açılmış boyut hesabı 395.891.920 bayt; bu ağdan indirilen byte ölçümü değildir.

1 m ENU 3.000 × 3.000; 4 m planlama 750 × 750; ikisinde nodata %0. Üç nokta sayısal dönüşüm hatası en çok 1 m çıktıda 0,0000411 m, 4 m çıktıda 0,0000566 m. Bunlar bağımsız arazi doğruluğu veya fiziksel feature hizalama ölçümü değildir.

**Dosyalar:** `data/derived/BXW/qa_1m/qa.html`, `qa_4m/qa.html`; hafif metadata ve hash kaydı `data/stac/BXW/run_manifest.json`. Bu manifest STAC Collection değildir. [Kaynak ön kontrolü](../../docs/verification/T1_SOURCE_PROBE.md) ve [çalıştırma rehberi](../../docs/DEVELOPMENT.md).

**Kararlar:** Kaynak tiled COG varsayılmadı; PixelIsPoint için Rasterio/GDAL affine'i kullanıldı. Yerel mühendislik grid'ine sahte Dünya/Mars projeksiyon etiketi konmadı; zorunlu sidecar kaynak WKT ve dönüşümü saklıyor. H0=0 açık senaryo ofseti. STAC çekim tarihiyle kaynak gözlem tarihi arasındaki uyuşmazlık kaydedildi.

**Kalan:** Gale düşey datum; ikinci DTM'nin gerçek eşkayıt/fark analizi; `slope_sigma` tanım/birim doğrulaması; STAC Collection/Item üretim ve şema doğrulaması. T1 bitmiş sayılmaz; T2 başlamadı. Sonraki kodlama buradan devam eder.
