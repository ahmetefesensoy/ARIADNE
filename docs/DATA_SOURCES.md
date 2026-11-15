# Veri kaynakları — T1

İlk kayıt 14 Kasım 2026, 13:20 (+03:00); **13:44 güncellemesiyle T1 yerel kabulü geçti**. Ürün-özel [düşey metadata](verification/T1_VERTICAL_DATUM.md), [özgün IMG→ARD aktarımı](verification/T1_HIRISE_TRANSFER.md) ve [kabul snapshot'ı](../data/stac/BXW/t1-run-lfDo4ErT/t1_acceptance.json). Aşağıdaki ilk kaynak taramasının açık durumları bu tarihli kanıtlarla birlikte okunmalı.

| Ürün | Uygulamadaki rol ve statü | Gözlenen durum |
|---|---|---|
| [MSL_Gale_DEM_Mosaic_1m_v3](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif) | DERIVED; BXW kaynak arazi | HEAD 200, 3.868.256.546 bayt; Range 206. Yerel 3 km pencere alındı. |
| [Gale LRGB](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif) | ARCHIVE katalog girdisi; optik bağlam | Bu uygulama koşusunda indirilmedi/doğrulanmadı. Katalogdaki statü proje spekinden gelir; türev işlem geçmişi ayrıca çözülecek. |
| [PLACES interpolated localization](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv) | ARCHIVE; lokalizasyon | Yapılandırıldı; bu koşuda ingest edilmedi. |
| [MMGIS MSL waypoints](https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json) | ARCHIVE; operasyonel rota | Yapılandırıldı; bu koşuda ingest edilmedi. |
| [HiRISE DTM koleksiyonu](https://stac.astrogeology.usgs.gov/api/collections/mro_hirise_socet_dtms) | DERIVED; kayıt/fark referansı | `DTEEC_019698_1750_019988_1750_U01` gerçek 3 km crop alındı; nodata %0; özgün IMG aktarımı ve Gale ile göreli kayıt/fark yapıldı. İkinci aday metadata düzeyinde kaldı. |

Gale kaynağı tek bant Float32, 1 m post ve row-strip LZW TIFF'tir; COG varsayımı kullanılmaz. Gerçek WKT: Mars_2000 sphere, R=3.396.190 m, eqc, lon_0=lat_ts=0, yatay metre. Rasterio/GDAL efektif affine'i PixelIsPoint yarım piksel davranışını taşır. Multipart ETag tam dosya SHA256'sı değildir.

[USGS ürün kaydı](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m) ilk denemede 403 verdi; sonraki User-Agent sorgusu 200 ile gerçek FGDC bağlantısını açtı. [Ürün-özel FGDC](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m.xml) v3 için **MOLA / Meters** bildiriyor. Resmi TIFF linkinin kullanılan S3 nesnesine yönlendiği doğrulandı. Exact areoid/model sürümü belirtilmiyor; bu sınır korunuyor. 1 m post, 1 m konum/yükseklik doğruluğu değildir. Yayın öncesi ürün yazar kredisi/lisans ve tam üretim zinciri tekrar kontrol edilecek.

Kaynak piksel değerleri uydurulmadı. Yeni ENU/eğim/pürüzlülük çıktıları **DERIVED**; saha sınırı ve H0=0 seçimi **SCENARIO**. Henüz bilim görevi veya yeni NASA ölçümü üretilmedi. Üç nokta testi yalnız sayısal dönüşüm tutarlılığıdır; DTM doğruluğu veya gerçek saha hizası değildir.

İki HiRISE DTM'nin STAC zamanları ile asıl gözlem tarihleri uyuşmuyor; zaman bölmeli doğrulamada bu STAC tarihleri doğrudan kullanılmayacak. İki DTM için Mars 2000 eşpotansiyel yüzeyi etiketle doğrulandı; bu bilgi Gale mozaiğine otomatik aktarılmadı.

İlk [run_manifest.json](../data/stac/BXW/run_manifest.json) hafif ara checkpoint'tir. Tam kabulün [yeni manifesti](../data/stac/BXW/t1-run-lfDo4ErT/run_manifest.json), [Collection'ı](../data/stac/BXW/t1-run-lfDo4ErT/catalog/collection.json) ve [çevrimdışı şema raporu](../data/stac/BXW/t1-run-lfDo4ErT/stac_validation.json) kaynak WKT/orijin/dönüşüm/hash/test zincirini saklar. [Item 1.1.0](https://raw.githubusercontent.com/radiantearth/stac-spec/v1.1.0/item-spec/item-spec.md), [Projection 2.1.0](https://stac-extensions.github.io/projection/v2.1.0/schema.json), [Solar System 1.1.1](https://stac-extensions.github.io/ssys/v1.1.1/schema.json) resmi şemaları ve lisansları hash sabitli, ağsız doğrulamada kullanılır. Mars native sınırları WGS84 gibi sunulmaz; işleme zamanı açıkça bu anlamla kaydedilir, acquisition bilinmiyor. SSYS bütün Mars zarfı muhafazakâr katalog zarfıdır; ayak izi değildir.

Göreli kayıt yöntemi, [Nuth & Kääb (2011)](https://doi.org/10.5194/tc-5-271-2011) yatay öteleme ilkesine dayanır; yayının tam iş akışı veya bağımsız hata modeli uygulanmış sayılmaz. Kayıt sonrası slope_sigma iki 5 m tabanlı eğimin mutlak farkı, derece cinsinden ampirik proxy'dir. Ortak kontrol/kaynak korelasyonu, MOLA realizasyon eşitliği ve bağımsız mutlak doğruluk açık sınır olarak korunur.

Yöntem rehberi atfı: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, [doi:10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065). Canlı kayıt v2 olarak kontrol edildi; bu atıf skill kullanımına aittir, gezegen verisinin doğruluk kanıtı değildir.

## T1 sonrası eklenen kaynaklar — 15 Kasım 2026, 14:30 (+03:00)

Bu tablo T1 tablosunu değiştirmez; sonradan uygulamaya giren ürünleri ekler. SHA-256 değerleri
yerel kanıt dosyalarından okundu (bağlantılı JSON'lar).

| Ürün | Görev / alet | Uygulamadaki rol | Statü | Kanıt / SHA-256 |
|---|---|---|---|---|
| [RAD_RDR_2024_139_17_46_4189_V00](https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_04134_04257/RAD_RDR_2024_139_17_46_4189_V00.TXT) | MSL RAD (PDS PPI) | Fırtına öncesi arka plan | ARCHIVE | `data/env/rad_4189.json` · c8a9a6d6…40232 |
| [RAD_RDR_2024_140_18_30_4190_V00](https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_04134_04257/RAD_RDR_2024_140_18_30_4190_V00.TXT) | MSL RAD | 20 Mayıs 2024 SEP: alarm, FR-04, S1/C1 replay | ARCHIVE | `data/env/rad_4190.json` · 2f4df513…487ff; değerler `verification/T6_RAD.json` |
| [RAD_RDR_2024_141_19_08_4191_V00](https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_04134_04257/RAD_RDR_2024_141_19_08_4191_V00.TXT) | MSL RAD | Fırtına sonrası | ARCHIVE | `data/env/rad_4191.json` · 579b5fc9…4bb41 |
| [MSL APXS supplement ds01](https://pds-geosciences.wustl.edu/msl/urn-nasa-pds-msl_apxs_supplement_sols_0_2301/data/ds01_2020je006536rr.csv) | MSL APXS (PDS Geosciences; Berger vd. 2020, doi:10.1029/2020JE006536) | 690 ölçümden hassasiyet modeli (D018) | ARCHIVE → DERIVED | `verification/APXS_PRECISION.json` · 6a6e4359…4f8c |
| NAIF `naif0012.tls`, `pck00011.tpc`, `de440s.bsp` | NAIF SPICE | Güneş açısı/gün ışığı (D014), Dünya–Mars ışık süresi | DERIVED | `data/env/sun_BXW_2024-05-19_22.json`, `verification/LIGHT_TIME_SOL4190.json` |
| [MSL_Gale_HiRISE-LRGB_78quads_sharp_cog](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif) | MRO HiRISE renk mozaiği (USGS) | Unreal yüzey rengi, tablet atlası | ARCHIVE → DERIVED | `data/engines/BXW/surface-v1/imagery.json` |
| NASA/TP-2009-214796 (EWT) | NASA analog çalışması | 3/8 g giysili yürüme maliyeti parametresi (D010) | literatür → SCENARIO | `config/suit.yaml` |
| Löwe vd. 2025, arXiv 2502.02469 | yayın | %25 doz artışı alarm kuralı | literatür | D012 |

Yalnız referans, ölçüm olarak gösterilmez: Phoenix WCL pH (Kounaves vd. 2010; D020). Yapılandırılıp
ingest edilmeyenler T1 tablosunda: PLACES, MMGIS.
