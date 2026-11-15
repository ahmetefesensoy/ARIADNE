# HiRISE orijinal IMG → ARD sayısal aktarım kontrolü

14 Kasım 2026, 13:42:39 +03:00 · Europe/Istanbul. Ürün: `DTEEC_019698_1750_019988_1750_U01`. Salt okunur, küçük HTTP Range denemesi; GitHub işlemi yapılmadı.

**Üç ayrı ARD pikseli için orijinal PDS IMG'den hesaplanan yükseklikler uyuştu.** Önceden belirlenen sayısal warp tanı eşiği **0,1 m**; en büyük mutlak artık **1,1778×10⁻¹⁰ m**. Üç ARD değeri de orijinalin en yakın ham Float32 pikseline tam eşit, negatif ve kesirlidir. Bu örneklerde UInt16'ya dönüştürülüp sıfıra kırpılma veya tamsayıya yuvarlama görülmedi. Tam sonuçlar [T1_HIRISE_TRANSFER.json](T1_HIRISE_TRANSFER.json) içindedir.

Bu bir **kaynaklar arası sayısal aktarım tanısıdır**. Bağımsız saha kontrolü, mutlak 10 cm arazi doğruluğu, tüm piksellerin eşitliği veya bağımsız σ ölçümü değildir. Düşey datumun tam areoid model/sürümü bu testten çıkarılmaz.

## Gerçek dosyalar ve yöntem

Kaynak [UArizona PDS IMG](https://www.uahirise.org/PDS/DTM/ESP/ORB_019600_019699/ESP_019698_1750_ESP_019988_1750/DTEEC_019698_1750_019988_1750_U01.IMG). Karşılaştırılan yerel dosya `data/raw/BXW/hirise_dtm_bxw_019698.tif`, [USGS ARD TIFF'inden](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/ESP_019698_1750_ESP_019988_1750/DTEEC_019698_1750_019988_1750_U01.tif) alınan 3 km BXW penceresidir. Yerel dosyanın SHA256'sı `e34ade1cfa0c54034464aced983b78f78fdd6ba0e5d86422fdccb28e13ce6187`; boyutu 2.966 satır × 2.976 sütundur.

1. IMG'nin ilk 16.384 baytı HTTP 206 ile okundu. Tam PDS etiketi bu önekte var; kalan kısım sıfır dolgusudur. Ürün ID ve hedef Mars kontrol edildi.
2. Yalnız bu önek, GDAL'ın `PDS` sürücüsüyle bir Rasterio `MemoryFile` içinde açıldı. Orijinal CRS, affine, ölçek, offset ve nodata etiketten okundu. GDAL'a uzak URL verilmedi. [GDAL PDS sürücüsü](https://gdal.org/en/stable/drivers/raster/pds.html), georeferencing/CRS ve VirtualIO desteğini belgeliyor.
3. PDS kaydı `PC_REAL`, 32 bit, ölçek `1`, offset `0`, `RECORD_BYTES=29704`, `^IMAGE=2` veriyor. Görüntü verisi sıfır tabanlı bayt offset **29.704**'te başlıyor; 7.426×4 baytlık satırlar var. Bu yapı ile 18.270 satır toplam **542.721.784 bayt** yapıyor; HTTP toplam boyutuyla aynı.
4. ARD crop'unda önceden sabitlenen `(satır, sütun)` oranları `(0,2;0,2)`, `(0,5;0,8)`, `(0,8;0,4)` seçildi. Üç nokta aynı doğru üzerinde değildir. Her bir gerçek ARD pikselinin merkezi, ARD'nin kendi CRS'inden orijinal PDS CRS'ine dönüştürüldü.
5. Her kaynak merkezinin çevresindeki 8×8 Float32 destek alanı kontrollü HTTP Range ile okundu. Sekiz satırın arasındaki baytlar dahil tek bitişik range kullanıldı; bu nedenle her pencere için 207.960 bayt okundu. Üç destek alanında da nodata veya sonlu olmayan değer yoktu; hedef piksellerin maskesi geçerliydi.
6. Her kaynak pencere, gerçek kaynak/hedef affine ve CRS'leriyle yalnız karşılık gelen 1×1 ARD pikseline `rasterio.warp.reproject(..., resampling=cubic)` ile taşındı. İki CRS yatay 2B tanımlardır; ayrı bir düşey datum dönüşümü uygulanmadı. [Rasterio reproject sözleşmesi](https://rasterio.readthedocs.io/en/stable/api/rasterio.warp.html#rasterio.warp.reproject)

## Sonuçlar

İndeksler sıfır tabanlıdır; yükseklikler metre cinsindendir. Üç kaynak konumu da orijinal gridde piksel merkezlerine sayısal yuvarlama düzeyinde denk geldi (`kolon+0,5`, `satır+0,5`). Bu durumda cubic öngörü ile ham piksel arasındaki çok küçük fark hesaplama yuvarlaması düzeyindedir; arazi doğruluğu olarak yorumlanmaz.

| Nokta | ARD crop satır/sütun | Orijinal IMG satır/sütun | Orijinal ham Float32 | ARD Float32 | ARD − cubic öngörü |
|---|---|---|---:|---:|---:|
| P1 | 593 / 595 | 3557 / 2493 | -3842,385498046875 | -3842,385498046875 | +5,5024×10⁻¹¹ m |
| P2 | 1483 / 2380 | 4447 / 4278 | -3619,67578125 | -3619,67578125 | +1,1778×10⁻¹⁰ m |
| P3 | 2372 / 1190 | 5336 / 3088 | -3569,7822265625 | -3569,7822265625 | -1,6371×10⁻¹¹ m |

Orijinalin kendi PDS CRS'i küresel equirectangular, `R=3396190 m`, `lon_0=137,38°`, `lat_ts=0°`; efektif GDAL affine'i `(1.0117467945795,0,-4018.6582680699767,0,-1.0117467945795,-280315.578653001)` şeklindedir. ARD'nin kendi TIFF CRS'i aynı yarıçaplı equirectangular, `lon_0=0°`, `lat_ts=0°`; crop affine'i JSON'da ayrı saklanmıştır. Orijinalin CRS'i ARD'den kopyalanmadı; Dünya CRS'i kullanılmadı.

[USGS provenance](https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/ESP_019698_1750_ESP_019988_1750/provenance.txt) içindeki UInt16 komutları, gerçek Float32 TIFF ile çelişmeye devam ediyor. Bu test üreticinin çalıştırdığı komut geçmişini yeniden kurmaz; yalnız üç kontrol noktasında orijinal negatif/kesirli yüksekliklerin ARD'de korunduğunu doğrudan gösterir. Orijinal etiketin Mars 2000 eşpotansiyel yüzeyi açıklaması ve MOLA sınırları için [T1_VERTICAL_DATUM.md](T1_VERTICAL_DATUM.md) okunmalıdır.

## Sınırlı ağ okuması ve tekrar üretim

Başarılı koşuda dört HTTP isteğinin tamamı **206** döndü; uygulamanın okuduğu yanıt gövdeleri toplam **640.264 bayt**, önceden sabitlenen üst sınır **1.000.000 bayt**. Sayı HTTP başlıkları, TLS taşıma maliyeti ve daha önce yapılmış ARD crop indirmesini kapsamaz. Sunucu 206, doğru Content-Range/Content-Length ve tutarlı ETag sağlamazsa helper gövdeyi okumadan durur. İlk yanıttan sonraki istekler `If-Match` kullanır. Tam IMG indirme geri dönüşü yoktur.

[probe_hirise_transfer.py](../../scripts/probe_hirise_transfer.py) yeni bir salt okunur yardımcıdır. Kaynak raster veya crop yazmaz; JSON'u stdout'a basar. WSL içinde depo kökünden:

```bash
source scripts/common.sh
"$REDLINE_VENV/bin/python" scripts/probe_hirise_transfer.py \
  --ard-crop data/raw/BXW/hirise_dtm_bxw_019698.tif
```

Gözlenen ortam: Rasterio **1.4.3**, GDAL **3.9.3**, NumPy **1.26.4**. Helper SHA256: `5eeeb6fa35e936a9e9755ddd9c275641176d5a28849a423a890c2875fc93858f`. Her HTTP range'in offset, boyut, ETag, UTC ve gövde SHA256'sı JSON'da; kaynak pencere ve yerel ARD crop hash'leri de kaydedildi. `source_vertical_evidence` önceki datum JSON'unun değişmeyen hash'ini ayrıca bağlar. Ham range gövdeleri ayrıca diske indirilmedi.
