# Gale AOI ve Curiosity PLACES kesişimi

> **Araştırma 02 / 16** · Aşama 1 — Araştırma ve aday fikirler · Dosya oluşturulma: 13 Kasım 2026 21:59 · [← 01](01-ilk-arastirma-ve-deney-plani.md) · [Dizin](README.md) · [03 →](03-kapsamli-arastirma-sekiz-aday.md)
>
> Bu bir araştırma/fikir kaydıdır; güncel proje [nihai proje](../2-nihai-proje/README.md) bölümündedir.

13 Kasım 2026 · Salt okunur metadata sorgusu

**Mevcut 2 × 2 km AOI içinde, sorgulanan iki PLACES tablosunda konum örneği bulunmadı.** Bu sonuç Curiosity'nin bu sahaya hiç bakmadığını veya sahada başka görev verisi olmadığını kanıtlamaz. Fotoğrafın çekim konumu ile gördüğü arazinin konumu ayrıca hesaplanmalıdır.

AOI, mevcut `TERRAIN_PROVENANCE.json` dosyasından gelen küresel eşuzak silindirik sınırdır: easting 8.146.000–8.148.000 m, northing −286.000…−284.000 m. Sorguda planetocentric enlem −4.824993…−4.791252°, doğu boylamı 137.427947–137.461688° kullanıldı; planetodetic enlem sütunu kullanılmadı.

| Sorgulanan ürün | Kayıt sayısı | Filtre | AOI eşleşmesi |
|---|---:|---|---:|
| `localized_pos.csv` | 1.470 | `frame=ROVER`, enlem/boylam kutusu | 0 |
| `localized_interp.csv` | 49.315 | Tüm frame'ler, aynı enlem/boylam kutusu | 0 |

Kaynaklar doğrudan JPL PDS arşivinden belleğe indirildi ve CSV başlıklarıyla okundu. Bundle ve interp ürün etiketi sürüm **42.0** bildiriyor. Interp etiketinin tarih aralığı 2012-08-06T05:18:39Z–2026-04-17T00:19:01Z; üretim tarihi 2026-05-01. Tablo içindeki sol alanı −1…4868 aralığında; −1 geçerli yüzey sol numarası gibi yorumlanmamalı. Dizin sayfasındaki 2026-08-01 değiştirme tarihi ölçüm tarihi değildir.

Mevcut yerel başlangıca izdüşüm düzleminde en yakın interp örneği: **site 108 / drive 762 / sol 4255**, enlem −4.787292101°, boylam 137.409190894°, easting 8.144.888,227 m, northing −283.765,291 m. Bu örnek mevcut AOI'nin batı/kuzey tarafında kalıyor. Bu nokta tek başına bir bilim hedefi ilan edilmedi.

Saha seçiminde iki seçenek var: mevcut AOI'ye bakan bir Curiosity görüntüsü/bilim hedefinin gerçek ayak izini doğrulamak; veya doğrulanmış bir PLACES noktasının çevresine yeni bir AOI koyup oradaki yörünge veri kapsamasını denetlemek. Yeni saha için raster indirme veya arazi işleme yapılmadı.

Makinece okunur ayrıntı: [sorgu kaydı](ekler/Gale_PLACES_AOI_KONTROLU.json).

Birincil kaynaklar: [PLACES bundle](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/bundle.xml), [konum tablosu](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_pos.csv), [interp tablo](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv), [interp etiketi](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv.xml), [sürüm notları](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/document/release_notes.txt).
