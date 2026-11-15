# T1 kaynak ön kontrolü

14 Kasım 2026, 13:01 +03:00 · Europe/Istanbul. Salt okunur ağ sorguları ve küçük HTTP byte-range okumaları. Tam raster indirilmedi; eski demo klasörü okunmadı. Bu rapor T1'in tamamlandığı veya rasterların hizalı olduğu anlamına gelmez.

## Sonuç

Gale DEM v3 kaynağı erişilebilir, HTTP Range çalışıyor ve gömülü GeoTIFF anahtarları Mars küresi / equirectangular / 3.396.190 m yarıçapını doğruluyor. Kaynak **COG değil, satır başına strip kullanan LZW GeoTIFF**. HiRISE BXW adayları erişilebilir ve tiled BigTIFF; arşiv IMG etiketleri bunların düşey referansını açıkça Mars 2000 eşpotansiyel yüzeyine bağlıyor. Gale birleşik mozaiğinin aynı düşey referansa sahip olduğu henüz ürün etiketiyle doğrulanmadı.

Başlıca uygulama sonuçları:

- Gale TIFF `PixelIsPoint`, HiRISE ARD TIFF'ler `PixelIsArea` olarak işaretli. Affine dönüşümü GDAL/Rasterio'dan okuyup piksel merkezlerini ayrıca test et; ham tiepoint'i doğrudan piksel köşesi sayma.
- USGS STAC DTM `datetime` alanları iki aday için de 2006-09-29 gösteriyor; kaynak gözlem sayfaları 2010 ve 2008 tarihleri veriyor. Zaman bölmeli V2 testinde bu STAC tarihini çekim tarihi kabul etme.
- STAC `proj:bbox` derece cinsinden görünüyor; projected metre sınırı olarak kullanılmamalı. `proj:transform` dizisi GDAL sırasına benziyor; STAC affine düzenini doğrulamadan doğrudan Affine constructor'a verme. Rasterın kendi geotransformunu oku.
- İki DTM'nin katalog geometrisinde BXW merkezi var; ikinci DTM'nin geometrisi önerilen 3 km kutunun batı köşelerini kapsamıyor. Bu yalnız aday kapsam kontrolüdür; nodata/piksel hizası veya hata dağılımı kanıtı değildir.

## Gale birleşik DEM v3

Dosya: [MSL_Gale_DEM_Mosaic_1m_v3.tif](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif).

| Gözlem | Sonuç |
|---|---|
| HEAD | HTTP 200; 3.868.256.546 bayt; `Accept-Ranges: bytes` |
| GET `Range: bytes=0-16383` | HTTP 206; `Content-Range: bytes 0-16383/3868256546`; tam 16.384 bayt okundu |
| Last-Modified | 2022-11-09 15:50:28 GMT |
| ETag | `746836824e520f8f0a7fb3987bdef0ff-462`; multipart ETag, dosyanın SHA256'sı değildir |
| TIFF | little-endian klasik TIFF; IFD offset 3.867.795.758; 19 entry |
| Boyut ve değer tipi | 32.980 sütun × 57.440 satır; tek bant; 32-bit IEEE floating point |
| Sıkıştırma/düzen | compression 5=LZW; RowsPerStrip=1; 57.440 strip; tiled değil |
| Grid | ModelPixelScale `(1,1,0)` m; ModelTiepoint raster `(0,0,0)` → `(8127993.992786024,-244781.575189438,0)` |
| Raster yorumu | GTRasterTypeGeoKey=2 (`PixelIsPoint`) |
| Nodata | GDAL_NODATA `-32767` |
| Yatay CRS | `Mars_Equirectangular_clon0`; `GCS_Mars_2000_Sphere`; metre; equirectangular GeoTIFF transform code 17; standard parallel, natural-origin latitude/longitude ve false offsets 0 |
| Küre | SemiMajor=SemiMinor=3.396.190 m; inverse flattening 0 |
| Düşey CRS | Okunan TIFF GeoKeys/GDAL metadata içinde ayrı vertical CRS/areoid tanımı yok |

Tag incelemesi için başlık, uzak IFD ve yalnız gereken metadata değerleri range ile okunarak toplam **1.269 ek bayt** kullanıldı. Strip offset/byte-count dizileri ve raster piksel içeriği indirilmedi. Pencere okuması Range ile mümkündür fakat bir satır strip'i bütün genişliği içerdiğinden ağ maliyeti tiled COG'dan farklıdır. COG adı veya özelliği bu kaynak için varsayılmamalı.

[USGS ürün kaydı](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m) arama hizmetinde erişilen katalog metninde v3, Mars, planetocentric/east-positive koordinatlar, metre düşey birimi ve MOLA kontrol ağı belirtiliyor; yazar kredisi isteniyor, kullanım kısıtı belirtilmiyor. Karışık HRSC/CTX/HiRISE/MOLA girdileri nedeniyle 1 m grid 1 m konum doğruluğu anlamına gelmiyor. Doğrudan sayfa açılışı web aracı ve Python istemcisinde HTTP 403 verdi. Katalogdaki “1 m vertical” genel kontrol ağı ifadesi yeni BXW hata bütçesi veya doğrulanmış düşey datum yerine geçmez.

Aynı S3 tabanında `.lbl`, `.xml` ve `.tif.xml` olası sidecar yollarına sınırlı istekler HTTP 404 verdi. Bunlar tahmini yollar olduğundan “ürünün etiketi yok” sonucu çıkarılmaz; katalogdaki gerçek ancillary bağlantısı çözülmeli. Mars Trek `Gale_DEM_SMG_1m` ile bu v3 dosyanın byte/piksel eşdeğerliği doğrulanmadı.

## BXW HiRISE DTM adayları

Katalog: [mro_hirise_socet_dtms koleksiyonu](https://stac.astrogeology.usgs.gov/api/collections/mro_hirise_socet_dtms). Koleksiyon canlı HTTP 200; hedef Mars, lisans CC0-1.0, kaynak veri kümesi `MRO-M-HIRISE-5-DTM-V1.0`.

| Aday | Item URL | DTM URL | Canlı HEAD / Range |
|---|---|---|---|
| `DTEEC_019698_1750_019988_1750_U01` | [STAC item](https://stac.astrogeology.usgs.gov/api/collections/mro_hirise_socet_dtms/items/DTEEC_019698_1750_019988_1750_U01) | [COG](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/ESP_019698_1750_ESP_019988_1750/DTEEC_019698_1750_019988_1750_U01.tif) | HEAD 200, 265.874.780 bayt; küçük metadata range istekleri 206 |
| `DTEEC_009149_1750_009294_1750_U01` | [STAC item](https://stac.astrogeology.usgs.gov/api/collections/mro_hirise_socet_dtms/items/DTEEC_009149_1750_009294_1750_U01) | [COG](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/PSP_009149_1750_PSP_009294_1750/DTEEC_009149_1750_009294_1750_U01.tif) | HEAD 200, 181.586.808 bayt; küçük metadata range istekleri 206 |

Her iki item JSON'u Python HTTPS istemcisiyle HTTP 200 döndürdü; web open aracı aynı item adreslerini açamadı. Her DTM için TIFF metadata incelemesi yalnız **1.458 bayt** okudu.

| Metadata | 019698/019988 | 009149/009294 |
|---|---|---|
| Boyut | 7.426 × 18.270 | 6.749 × 14.466 |
| Pixel scale | 1.0117467945795104 m | 1.0117467945795113 m |
| TIFF tipi | BigTIFF, IFD offset 200 | BigTIFF, IFD offset 200 |
| Düzen | 512×512 tile, DEFLATE, Float32 | 512×512 tile, DEFLATE, Float32 |
| Nodata | -3.40282265508890445e38 | -3.40282265508890445e38 |
| Raster yorumu | PixelIsArea | PixelIsArea |
| Tiepoint | E=8139139.287483739, N=-280315.578653001 | E=8141577.187319504, N=-277179.16358980455 |
| ETag | `d36cca32e3457b61a9db2c44a5cf3a70-32` | `5082a3da7ac084d2a109ea44a583f30f-22` |
| Last-Modified | 2023-07-08 00:46:10 GMT | 2023-07-08 10:19:41 GMT |

STAC `proj:projjson` ile gerçek TIFF GeoKeys aynı yatay tanımı veriyor: Mars (2015) Sphere/Ocentric, equidistant cylindrical, R=3.396.190 m, merkez boylam ve standard parallel 0°, metre. `proj:epsg` null; Dünya EPSG:4326 etiketi eklenmez. GDALMetadata, Mars hedefi, ürün ID'si ve PDS veri kümesini de içeriyor. TIFF byte yapısının COG yerleşim kurallarına tam uyumu bir COG validator ile henüz test edilmedi; tiled BigTIFF ve baştaki IFD bu dar kontrolde doğrulandı.

### Asıl PDS etiketleri ve düşey referans

[HiRISE ürün sayfası 019698](https://www.uahirise.org/dtm/dtm.php?ID=ESP_019698_1750) ve [009149](https://www.uahirise.org/dtm/dtm.php?ID=PSP_009149_1750) üzerinden çözülen orijinal IMG yolları:

- [019698/019988 PDS IMG](https://www.uahirise.org/PDS/DTM/ESP/ORB_019600_019699/ESP_019698_1750_ESP_019988_1750/DTEEC_019698_1750_019988_1750_U01.IMG)
- [009149/009294 PDS IMG](https://www.uahirise.org/PDS/DTM/PSP/ORB_009100_009199/PSP_009149_1750_PSP_009294_1750/DTEEC_009149_1750_009294_1750_U01.IMG)

Her birinde yalnız ilk 16.384 bayt istendi; HTTP 206 döndü. Gömülü PDS3 etiketleri ürün sürümü 1.0, TARGET_NAME=MARS, SAMPLE_TYPE=PC_REAL, ölçek 1 ve offset 0 veriyor. IMAGE/NOTE, piksel değerlerinin Smith et al. (2001) Mars 2000 eşpotansiyel yüzeyi üzerindeki **metre cinsinden yükseklikler** olduğunu açıkça belirtiyor. Bu, iki DTM'nin ürün-özel düşey referans kanıtıdır; ayrı Gale mozaiğine otomatik aktarılamaz.

Önemli dönüşüm: Orijinal IMG'lerde merkez boylamlar sırasıyla **137.38° ve 137.41°**; ARD GeoTIFF'lerde **0°**. Bu, aynı sayısal koordinatları taşıyan ham kopyalar değildir. USGS provenance kayıtları `gdalwarp` ile `IAU_2015:49910` hedefini gösteriyor. [019698 provenance](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/ESP_019698_1750_ESP_019988_1750/provenance.txt) ve [009149 provenance](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/PSP_009149_1750_PSP_009294_1750/provenance.txt) HTTP 200.

Bu provenance metinlerinde UInt16 çıktı seçeneği geçmesine rağmen gerçek TIFF BitsPerSample=32 ve SampleFormat=3 ile Float32. Dolayısıyla metni tek başına çıktı dtype kanıtı sayma; gerçek TIFF ve STAC bant tipi birlikte kullanılmalı. Bu dar kontrolde piksel sayısal değerleri karşılaştırılmadı.

### Çekim zamanı ve aday kapsamı

STAC'ın iki ürüne verdiği 2006-09-29 tarihi güvenilir kaynak çekim tarihi olarak kullanılamaz. HiRISE gözlem sayfaları [ESP_019698_1750](https://www.uahirise.org/ESP_019698_1750) için **2010-10-09**, [PSP_009149_1750](https://www.uahirise.org/PSP_009149_1750) için **2008-07-09**, [PSP_009294_1750](https://www.uahirise.org/PSP_009294_1750) için **2008-07-20** veriyor. ESP_019988 gözlem tarihi bu kontrolde çözülemedi. Stereo kaynağın her iki acquisition zamanı ve türev üretim tarihi ayrı kaydedilmeli.

BXW önerisi `(lon_east=137.370, lat=-4.805)`, 3.000×3.000 m için R=3.396.190 ve cos(lat0) kullanılarak aday köşeleri hesaplandı. Katalog polygon'unda merkez ve dört köşe 019698 ürününün içinde; 009149 ürününde merkez/doğu köşeler içeride, batı köşeler dışarıda. Bu sonuç tam AOI geçerliliği veya raster eşkayıt kanıtı değildir. Gerçek crop maskesi, seam/nodata ve en az üç karşılaştırma noktası T1 QA'da test edilmeli.

## Uygulama öncesi kalan kontroller

1. Gale v3 gerçek ancillary etiketini bularak düşey referansı ve kontrol ağı dönüşümünü doğrula; aynı sayısal negatif yükseklikler yeterli kanıt değildir.
2. Rasterio/GDAL ile metadata-only açılış, AREA_OR_POINT ve efektif geotransformu kontrol et. [GDAL RFC33](https://gdal.org/en/stable/development/rfc/rfc33_gtiff_pixelispoint.html) PixelIsPoint için yarım piksel düzeltmesini açıklar.
3. Yeni BXW penceresinin nodata, mask, ölçek ve en az üç nokta karşılaştırmasını yap. 1 m kaynak grid'inden 4 m planlama grid'ine türetim, destek ve yöntem kaydedilsin.
4. Bağımsız sigma iddiası kurma: ortak MOLA kontrolü ve örtüşen kaynaklar korelasyon yaratır. Önce eşkayıt ve fark dağılımı değerlendirilir.

## Kullanılan yöntem rehberleri

`planetary-geologist` ile `geomaster` skill'leri gövde/CRS, kaynak ve valid-data ayrımı için kullanıldı. Skill paketinin istediği yazılım/rehber kaydı: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, [doi:10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065). [ArXiv kaydı](https://arxiv.org/abs/2609.00065) canlı açıldı; son sürüm 2 Eylül 2026 revizyonu v2, yayıncı journal reference yok. Bu kaynak gezegen verisinin veya doğruluk sonuçlarının kanıtı olarak kullanılmadı.
