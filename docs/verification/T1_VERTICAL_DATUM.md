# Gale v3 düşey referansının kaynak doğrulaması

14 Kasım 2026, 13:32 +03:00 · Europe/Istanbul. Canlı HTTP sorguları; rasterın tamamı indirilmedi. Kod, kaynak raster ve GitHub değiştirilmedi. Bu kayıt [T1 kaynak ön kontrolünü](T1_SOURCE_PROBE.md) tamamlar.

## USGS, v3 ürününün yükseklik datumunu MOLA olarak bildiriyor

Gale v3 için `vertical_datum = MOLA`, `vertical_units = m` artık doğrudan ürün metadata'sıyla destekleniyor. USGS'nin gerçek FGDC XML kaydında `spref/vertdef/altdatum` değeri **MOLA**, `altunits` değeri **Meters**. Önceki kontrolde yalnız HTML sayfasındaki kontrol ağı bilgisi ve TIFF etiketleri görülebildiği için düşey datum açık kalmıştı. Bu yeni bulgu katalogda bildirilen düşey datum belirsizliğini gideriyor. [USGS v3 FGDC XML](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m.xml)

Kaynak, bu alanda belirli bir areoid modelinin adını/sürümünü, gravite modeli kimliğini veya uygulanan dönüşüm gridini vermiyor. Manifestte kanıtın kesinliği korunmalı: **“USGS-declared MOLA altitude datum; exact areoid realization/version unspecified.”** `Mars 2000 Datum` ifadesi ayrı HiRISE ürününün etiketinde var; Gale'ye otomatik aktarılmaz. Küresel yatay CRS adındaki `Mars_2000_Sphere` de tek başına düşey datum tanımı değildir.

MOLA arşiv dokümantasyonu MEGDR topografyasını gezegen yarıçapı ile areoid farkı olarak tanımlar. Bu, MOLA topografyasının genel fiziksel anlamını destekler; Gale mozaiğinin hangi MOLA ürün sürümünü kullandığını belirlemez. [PDS MOLA MEGDR açıklaması](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html)

## Ürün kaydından kullanılan TIFF'e bağlantı doğrulandı

1. [USGS Gale DEM ürün sayfası](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), bu kontrolde `User-Agent: Mozilla/5.0` ile HTTP **200** döndü. Sayfanın Download bağlantısı açıkça `MSL_Gale_DEM_Mosaic_1m_v3.tif` dosyasına gidiyor. FGDC bağlantısı sayfa JavaScript'inde ürün URL'sine `.xml` eklenerek kuruluyor; tahmini S3 sidecar yolu kullanılmadı.
2. [Sayfanın gerçek TIFF bağlantısına](https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif) `Range: bytes=0-63` isteği HTTP **206** verdi; son URL doğrudan uygulamada kullanılan [USGS S3 TIFF'i](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif) oldu. `Content-Range: bytes 0-63/3868256546`, ETag `746836824e520f8f0a7fb3987bdef0ff-462`. Aynı range'i son URL'den okuma aynı 64 baytı verdi. Böylece yalnız dosya adına dayanmayan canlı yönlendirme zinciri kuruldu. Aynı planetarymaps adresine daha önce yapılan HEAD isteği 403 vermişti; aşağıdaki başarılı GET gözlemi esas alındı.
3. Aynı ürün sayfasındaki gerçek PDS3 ve ISIS3 etiket bağlantıları HTTP **200** döndü. İkisi de v3 TIFF dosya adını, 32.980 × 57.440 tek bant rasterı, Mars hedefini ve 3.396.190 m küre/equirectangular yatay tanımı veriyor. İki etikette de ayrıca düşey datum adı yok. Düşey datum kanıtı yukarıdaki ürün-özel FGDC kaydıdır.

FGDC XML içindeki dar kanıt:

```xml
<spref>
  <!-- horizsys omitted -->
  <vertdef>
    <altdatum>MOLA</altdatum>
    <altres>1</altres>
    <altunits>Meters</altunits>
  </vertdef>
</spref>
```

XML `edition=version 3`, başlık `Mars MSL Gale Merged DEM 1m`, yayım tarihi `2016-10-20` veriyor. `metd=2026-11-14` bu erişimde üretilen metadata tarihidir; DEM'in üretim veya çekim tarihi olarak kullanılmaz. Sayfadaki 2011 süreç tarihi, 2017 PDS3 label revizyonu ve S3'ün 2022 Last-Modified zamanı da farklı olayları tanımlar. [FGDC kayıt](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m.xml), [PDS3 etiket](https://astrogeology.usgs.gov/ckan/dataset/b3d63877-8544-49bb-b0f3-532cf2c648d1/resource/cd140a94-1e66-46e0-8d5a-d8f0e4128b7e/download/msl_gale_dem_mosaic_1m_v3_pds3.lbl)

## Küçük metadata dosyaları ve bütünlük kaydı

Hash'ler bu oturumda tamamen okunan küçük dosyaların SHA256 değerleridir. FGDC dinamik olarak üretilebildiğinden hash belirli erişim yanıtını tanımlar. TIFF'in tamamının SHA256'sı hesaplanmadı.

13:34 +03:00'da özgün küçük yanıtlar [source-metadata/](source-metadata/) altında baytları değiştirilmeden kaydedildi; SHA256 değerleri tekrar hesaplanıp doğrulandı. [T1_VERTICAL_DATUM.json](T1_VERTICAL_DATUM.json), iki tam ürün ID'sini datum, birim, gerçek kaynak URL'si ve kanıt dosyası/hash/zamanıyla eşler. [HTTP gözlem kaydı](source-metadata/http-observations.json), istek ve son URL, Range, HTTP durum, yanıt başlıkları ve UTC zamanlarını taşır; Set-Cookie kaydedilmedi. HiRISE'nin dosyası 542.721.784 bayt IMG'nin yalnız ilk 16.384 baytıdır; `partial_artifact=true` olarak işaretlidir. Gale redirect yanıtının 64 baytı HTTP kaydında hex olarak korunur.

| Kanıt | HTTP / bayt | SHA256 |
|---|---|---|
| [FGDC XML](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m.xml) | 200 / 13.786 | `63672068718403653375a817f2cefe40f24901540ddb45ac9963bfccb59f3993` |
| [PDS3 detached label](https://astrogeology.usgs.gov/ckan/dataset/b3d63877-8544-49bb-b0f3-532cf2c648d1/resource/cd140a94-1e66-46e0-8d5a-d8f0e4128b7e/download/msl_gale_dem_mosaic_1m_v3_pds3.lbl) | 200 / 2.188 | `52eaf7a3f5c03812e0e6f3d5305495a329cb64eea65e161b0a6204a8092a9a16` |
| [ISIS3 detached label](https://astrogeology.usgs.gov/ckan/dataset/b3d63877-8544-49bb-b0f3-532cf2c648d1/resource/d1a8afb0-3a48-4dcb-92a8-6c5794bb662f/download/msl_gale_dem_mosaic_1m_v3.lbl) | 200 / 1.391 | `dd55ca3c5256ea7384c06b87279ce2ee8d08ce38cf69eda5dc57af3f11aae2cc` |
| [USGS VRT](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.vrt) | 200 / 1.799 | `b4bea2368d651e01bb041301a2ca45198d121e7f4d1417ab51d8c3c5584fd392` |
| [Yayınlanan TIFF MD5 sidecar](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif.md5) | 200 / 64 | `d0a70c53809078b0b40475600261ce984eef5723b8a71cb8af193382c192d863` |

MD5 sidecar, TIFF için `bc4cbabf8b06d24f3b25400f0468933b` yayımlıyor. Bu **yayıncı tarafından verilen MD5**; tam dosya indirilmediği için burada yeniden hesaplanıp doğrulanmadı. Multipart S3 ETag'i SHA256 veya MD5 yerine kullanılmaz.

USGS VRT, GDAL efektif dönüşümünü `(8127993.4927860238, 1, 0, -244781.0751894380, 0, -1)` ve `AREA_OR_POINT=Point` olarak veriyor; TIFF'teki ham tiepoint'e göre yarım piksel düzeltmesi var. Float32, nodata `-32767`, strip boyutu `32980×1`. VRT'nin WKT'sinde ayrıca dikey CRS yok. Bunlar önceki doğrudan TIFF tag kontrolüyle tutarlı; yatay kontrol olarak kullanılır. [USGS VRT](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.vrt)

Detached PDS3 label'da `^IMAGE=("MSL_Gale_DEM_Mosaic_1m_v3.tif",919904 <BYTES>)`; ISIS3 label'da `StartByte=919904`, `Format=BandSequential` yazıyor. Canlı TIFF ise LZW strip yapısında. Bu tarihsel detached label'ları TIFF piksel baytlarını ham IEEE_REAL dizisi olarak okumak için kullanma; güncel TIFF, GDAL/Rasterio ile açılmalı. Label'ların metadata ilişkisi güçlü olsa da fiziksel depolama varsayımları güncel TIFF yapısını açıklamıyor.

## HiRISE'nin BXW için rolü

`DTEEC_019698_1750_019988_1750_U01` ayrı bir arşiv ürünü olarak daha açık düşey referans sunuyor: orijinal PDS IMG'nin IMAGE/NOTE alanı, değerlerin Smith et al. (2001) tanımlı Mars 2000 eşpotansiyel yüzeyi üzerindeki metre cinsinden yükseklikler olduğunu söylüyor. Ürün ID, sürüm `1.0`, kaynak stereo çift `ESP_019698_1750` / `ESP_019988_1750`, ölçek `1.0`, offset `0.0` da aynı etikette. Bu kontrolde ilk 16.384 bayt HTTP **206** ile yeniden okundu; bütün IMG indirilmedi. [Orijinal IMG ve gömülü PDS etiketi](https://www.uahirise.org/PDS/DTM/ESP/ORB_019600_019699/ESP_019698_1750_ESP_019988_1750/DTEEC_019698_1750_019988_1750_U01.IMG)

Önceki katalog-geometri testinde BXW `(137.370°E, -4.805°)`, 3×3 km alanının merkezi ve dört köşesi bu ürünün ayak izinde kaldı. **Tam BXW geçerli-piksel kapsamı henüz doğrulanmış değildir.** İkinci aday `DTEEC_009149_1750_009294_1750_U01` batı köşelerini katalog geometrisinde kapsamıyor. Ayrıntılar ve iki ürünün gerçek URL'leri [T1_SOURCE_PROBE.md](T1_SOURCE_PROBE.md) içindedir.

HiRISE ARD kopyasının [USGS provenance kaydı](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/ESP_019698_1750_ESP_019988_1750/provenance.txt) orijinal ürün ID'sini ve `IAU_2015:49910` hedefine cubic warp'u gösteriyor. Kaydın UInt16 çıktı komutu ile gerçek TIFF'in Float32 tipi çeliştiğinden, bu metin tek başına sayısal eşdeğerlik kanıtı sayılmaz. Kaynak IMG ile ARD arasındaki piksel karşılaştırması yapılmadan ARD'nin yükseklik değerlerinin değişmediği iddia edilmez.

Gale'nin metadata'da bildirilen MOLA datumunu kullanarak tek kaynaktan yerel `z=H-H0` üretmek için kaynak değiştirmek zorunlu görünmüyor. Belirli areoid sürümü şart koşulursa, orijinal HiRISE IMG daha açık etiketli adaydır; kullanılmadan önce gerçek BXW crop'unda valid mask, nodata, kaynak/çıktı yükseklikleri ve yatay dönüşüm testleri geçmelidir. HiRISE ile Gale farklı yükseklik kaynakları olarak sessizce birleştirilmez.

## T1 uygulamasına aktarılacak karar

- Gale kaynak kaydında `status=ARCHIVE`, ürün adı/sürümü, iki gerçek URL ve MOLA düşey datum kanıt URL'sini sakla. Crop/ENU/derive çıktıları `DERIVED`; `H0` seçimi ayrıca açık `SCENARIO` referansıdır.
- `H0` ile raster `H` aynı yayımlanmış MOLA metre değerleri üzerinden tanımlansın. `H0` küre yarıçapı, sıfır areoid farkı veya dünya elipsoid yüksekliği olarak yorumlanmasın.
- Lokal ENU dönüşümünde `cos(phi0)/cos(lat_ts)` uygulanır; kaynak WKT ve ayrı düşey referans kaydı korunur. Veri kaynağında olmayan bir compound CRS üretilmez.
- Üç nokta testi kaynak piksel/ENU/çıktı dönüşümünü doğrular. Bu testin 10 cm eşiği mutlak arazi konum/yükseklik doğruluğu iddiasına dönüştürülmez; katalogdaki genel MOLA kontrol ağı doğruluğu da bağımsız BXW ölçümü değildir.
- Bu rapor tek başına T1'i bitirmez. Tam 3 km crop, nodata <%2, türev katmanlar, STAC/provenance ve gözlenen QA sonuçları ayrıca gereklidir.

Gezegen verisi değerlendirmesinde `planetary-geologist` ve `geomaster`; rapor düzeninde `llm-writing`, `intent-modeling`, `information-hierarchy` yönergeleri kullanıldı. Yöntem/skill kaynak kaydı önceki [T1_SOURCE_PROBE.md](T1_SOURCE_PROBE.md) belgesindedir.
