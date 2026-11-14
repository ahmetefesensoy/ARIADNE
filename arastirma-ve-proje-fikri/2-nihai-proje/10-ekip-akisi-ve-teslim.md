# 10 · Ekip akışı ve teslim

> REDLINE v3 nihai proje · Kılavuz bölümleri: §10, §11 · [← 09](09-kalite-test-ve-dogrulama.md) · [← Nihai proje](README.md) · [11 →](11-ayrintilar-ve-kapsam.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 10. Ekip akışı ve birleşme kapıları

**Süre notu:** hafıza kaydına göre hackathon 14 Kasım 09:00 – 15 Kasım 23:59 (Ankara), yani yaklaşık 39 saat [K]. Teslim saatini resmî sayfadan doğrula.

| Akış | Sahibi | İlk teslim |
|---|---|---|
| Veri hattı | veri/GIS | iki saha manifesti, DEM penceresi, σ katmanı, RAD/REMS replay dosyaları |
| Çekirdek model | algoritma | hücre modeli, isokron, PET, SEP kuralı, birim testleri |
| ROS/Gazebo | robotik | dünya, rover Nav2, drone, proxy, action'lar |
| Köprü | ROS + Unreal | rosbridge istemcisi, dönüşüm testi, replay |
| Unreal | UE | arazi, harita masası, HUD, astronot, POV swipe |
| Anlatı ve teslim | ürün | hikâye, çekim listesi, slaytlar, video, teslim dosyaları |

Birleşme kapıları (kapsam kesme değil, entegrasyon kontrolü):
1. **Ortak gerçeklik:** iki motorda aynı arazi, 1 m küp ve 90° testleri, 3 nokta yükseklik testi.
2. **İlk çizgi:** redline_core'un isokronu Unreal harita masasında görünüyor.
3. **Robot deltası:** bir rover gözlemi hücreyi değiştiriyor ve çizgi değişiyor.
4. **Kriz:** sol 4190 replay'i alarm veriyor, çizgi daralıyor, plan yeniden hesaplanıyor.
5. **Kanıt:** V1 karnesi ve V2 zaman bölmeli test tablosu hazır.
6. **Donma:** son saatler yalnız video, slayt ve teslim dosyaları.

---

## 11. Teslim, kurallar ve AI açıklaması

- **Biçim [K]:** 30 sn video veya en fazla 7 slayt, herkese açık bağlantılar, İngilizce, en az bir NASA kaynağı. Resmî sayfadan doğrula.
- **Önceden yapılan iş:** `PRE_EXISTING_WORK.md`. Önceki araştırma ve ROS demosu yarışma çıktısı gibi sunulmaz. GO Team araştırmayı serbest, proje geliştirmeyi diskalifiye riski sayıyor ([tartışma #1827](https://github.com/nasa/spaceapps/discussions/1827)).
- **Kaynaklar:** `DATA_SOURCES.md` (ürün ID, sürüm, erişim tarihi, statü, rol) ve `THIRD_PARTY_NOTICES.md`. DEM'de ESA HRSC girdisi de var; "tamamı NASA" denmez.
- **AI açıklaması — `AI_DISCLOSURE.md` ([GO Team #1849](https://github.com/nasa/spaceapps/discussions/1849)):**
  - AI ile üretilmiş görüntü ve videoda görünür "AI-generated" işareti olur.
  - AI yardımıyla yazılmış kod, veri işleme ve metinler belgede açıkça belirtilir; metadata'da da yer alır.
  - AI üretimi içerikte NASA logosu ve marka öğeleri kullanılmaz veya değiştirilmez.
  - Kaynaklı NASA arşiv görüntüsü ile AI üretimi görüntü ayrı içerik türüdür.
  - Bu projede örnek beyan: tasarım araştırması ve kod yardımı Claude ile yapıldı; bilim verileri NASA/USGS arşivlerinden alındı, AI tarafından üretilmedi.
- **Lisans:** özgün kod ve varlıklar için açık lisans. NASA ve üçüncü taraf malzemeler kendi haklarıyla. Fab/Megascans gibi kısıtlı varlıklar açık pakete konmaz.

### 11.1 30 saniyelik video (3 çekim)
1. **Ölçek merdiveni:** SIM 3292 poligonundan HiRISE hücresine zoom. "Bilinmeyen" hücreler gri.
2. **Robot keşfi ve kırmızı çizgi:** rover bir bilinmeyeni çözer, çizgi genişler.
3. **Gerçek fırtına:** 20 Mayıs 2024 RAD eğrisi yükselir, çizgi daralır. Astronot gözünden dönüş ve "Bilinen · Bilinmeyen · Kırmızı çizgi" kapanışı.

### 11.2 Yedi slayt
1. Kanca ve insan hikâyesi
2. Challenge kapsama matrisi
3. Katmanlar ve statü lejantı (arşiv / türetilmiş / simüle / senaryo)
4. Güven → pay → kırmızı çizgi
5. Gerçek kriz: sol 4190 ve sol 242
6. Kanıt: YKB karnesi ve boxwork zaman bölmeli test
7. Sınırlar, kaynaklar, önceden yapılan iş ve AI beyanı
