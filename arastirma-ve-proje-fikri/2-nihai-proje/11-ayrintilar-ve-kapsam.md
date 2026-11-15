# 11 · Kolay unutulan ayrıntılar ve kapsam tablosu

> REDLINE v3 nihai proje · Kılavuz bölümleri: §12, §20 · [← 10](10-ekip-akisi-ve-teslim.md) · [← Nihai proje](README.md) · [12 →](12-gelecek.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 12. Kolay unutulan ayrıntılar

- **Koordinat:** planetosentrik enlem, doğu pozitif boylam; ürünler arasında küre yarıçapı farkı (3.396.190 / 3.396.160). Metadata'dan oku, varsayma.
- **Dikey datum:** DEM yüksekliği hangi areoide göre? APXS yükseklikleri DEM ile tutarlı (−4520 m) [K]. Datum ürün etiketinden alınır.
- **Mars zamanı:** LMST ve sol numarası; Curiosity sol'ü ile Perseverance sol'ü farklı sayaçtır.
- **Işık süresi:** Dünya–Mars tek yön 4–24 dk. Seçilen tarihler için SPICE'tan hesaplanır ve "neden yerel otonomi" gerekçesine sayı olarak konur.
- **Güneş açısı ve gölge:** düşük güneşte uzun gölge, yüksek güneşte kontrast kaybı. EVA penceresine girer.
- **Toz ve görüş:** atmosferik opaklık (tau) kamera görünürlüğünü etkiler. 2018 küresel toz fırtınası bir "No-Go" örneği.
- **Röle:** MAVEN 2025'te kaybedildi [K]; günümüz senaryosunda röle TGO/MRO/Odyssey.
- **Veri hacmi:** COG pencere okuması. Ham büyük dosyalar depoya girmez, yalnız hash ve manifest girer.
- **Çevrimdışı paket:** demo internet API'sine bağlı olmaz; bütün katmanlar yerel paketlenir.
- **Determinizm:** senaryo tohumu ve RunManifest; aynı koşu tekrar oynatılabilir.
- **Erişilebilirlik:** renk tek bilgi taşıyıcısı değil. Sarı/kırmızı çizgi desenle de ayrılır; alarm metinle de gösterilir.
- **Dil:** teslim İngilizce; arayüz metinleri İngilizce tutulur.
- **Performans:** 30 FPS hedefi, kamera akışı düşük çözünürlükte. Kontrol döngüsü UI'a bağlı değil.
- **Güvenlik iddiası:** "güvenli rota" denmez, "model kısıtlarına uygun rota" denir.
- **CheMin "preliminary":** kesin mineral bileşimi gibi sunulmaz.

---

## 20. Önceki projeden ne var, ne yok (tam kapsam tablosu)

Durum: **Taşındı** = v3'te aynen var · **Dönüştü** = v3'te yeni biçimde var · **İsteğe bağlı** = tasarımda duruyor, demo omurgası değil · **Bırakıldı** = v3'te yok, gerekçesiyle.

| Önceki öğe | Kaynak | v3'te durum | Nerede |
|---|---|---|---|
| Rover manuel / destekli / otonom modları, komut sahipliği | PROJE_TANIMI, KILAVUZ §4.5 | Taşındı | §15.2 |
| Nav2, Collision Monitor, EKF, aktif algı | PROJE_TANIMI, GELISTIRME_STRATEJISI | Taşındı | §15.3 |
| Mevcut demonun A*, LiDAR duruşu, watchdog | ros2_ws README | Dönüştü (yeniden yazılır) | §15.3 |
| Drone: kalkış/iniş, rover pad, haritalama dışı işler | ASTRONOT_ROVER_DRONE, TASARIM | Taşındı | §15.4 |
| Kol, numune durum makinesi, MoveIt | ASTRONOT_ROVER_DRONE | İsteğe bağlı derinlik | §15.5, §5 evre 4 |
| Astronot proxy'si, refakat | KILAVUZ §13.1 | Taşındı | §15.6 |
| Hareketli sığınak (basınçlı rover) | REDLINE_RESEARCH M8 | Taşındı | §15.6, §18 |
| Beş görev | BES_ANA_GOREV, KILAVUZ §5–9 | Dönüştü (tek EVA'nın evreleri) | §5 |
| Eğitim/sınav, kalıcı durum, debrief | KILAVUZ §11, TASARIM | Dönüştü (prova/sınav modu, debrief) | §5 evre 1, 5 |
| Karar örnekleri A/B/C (kısa geçit, benzer vanalar, düşük kalite numune) | TASARIM | İsteğe bağlı (senaryo kataloğu) | §5, §17.3 |
| Vana/kaçak, ArUco, servis modülü | KILAVUZ §8 | Dönüştü (giysi kaçağı ana; habitat vanası isteğe bağlı) | §5 evre 5 |
| pH/iletkenlik laboratuvarı | KILAVUZ §6 | İsteğe bağlı ("model" etiketli) | §5 evre 4, H05 |
| Sondaj ekranı (derinlik/tork) | BES grafikleri | İsteğe bağlı | §17.3 |
| Habitat mekânları H01–H06, S01–S05 | KILAVUZ §3 | Taşındı | §19.1 |
| Unreal dört görünüm | ASTRONOT_ROVER_DRONE | Taşındı | §17.4 |
| Open MCT, RViz, PlotJuggler, Foxglove | BES, TASARIM | Taşındı + bağlantı yolu eklendi | §17 |
| Bilinmeyeni bilinmiyor tutmak (gizli gerçek ayrımı) | ASTRONOT_ROVER_DRONE | Taşındı | §16.2 |
| Ortak kayıt sözleşmeleri (EvidenceRecord, DecisionRecord, RunManifest…) | KILAVUZ §13.6 | Taşındı | §6.2 `redline_msgs` |
| Eksen/birim/saat sözleşmesi | KILAVUZ §13.5 | Taşındı + formül | §6.4 |
| Teorik modüller M1–M11 | REDLINE_RESEARCH | Taşındı (özet + referans) | §18 |
| Uçuş kuralları FRET → Ogma → Copilot | REDLINE_RESEARCH M9 | Taşındı | §18, `redline_safety` |
| DTN, ION/HDTN, Dünya konsolu | REDLINE_RESEARCH M10 | İsteğe bağlı | §17.5, §18 |
| GPS'siz konum, ufuk eşleştirme | REDLINE_RESEARCH M11 | İsteğe bağlı | §15.1, §18 |
| Topografik radyasyon (GCR) haritası | REDLINE_RESEARCH M3 | Taşındı (dürüst büyüklükle) | §18 |
| SUITS TSS adaptörü | REDLINE_RESEARCH §6.3 | İsteğe bağlı | §6.2 |
| Cesium Mars (Unreal/CesiumJS) | KATALOG D18, REDLINE_RESEARCH §6.6 | İsteğe bağlı (görsel bağlam) | §7.2 |
| Senaryo motoru, tohum, MCAP, determinizm | REDLINE_RESEARCH §6.8 | Taşındı | §19 |
| Test stratejisi, performans bütçeleri | REDLINE_RESEARCH §6.9–6.10 | Taşındı | §19 |
| Ses, görsel yön, performans hedefi | KILAVUZ §15, KATALOG §4 | Taşındı | §19.2 |
| 3D varlıklar ve lisanslar | KATALOG §2 | Taşındı + NASA-3D-Resources eklendi | §8 |
| Repo ve araçlar | KATALOG §5 | Taşındı | §9 |
| Project Chrono (zemin), ns-3 (ağ) | PROJE_TANIMI | İsteğe bağlı ayrı deney | §9 |
| Manuel / otonom / yalnız harita karşılaştırma deneyi | PROJE_TANIMI, KILAVUZ §16 | Taşındı | §20.1 |
| Bagnold/Gobabeb yedek kampanyası | GELISTIRME_STRATEJISI | Bırakıldı (boxwork ve YKB daha güçlü; HiRISE ürünü kapsamıyor [K]) | — |
| Üç başlangıç profili | KILAVUZ §2.3 | Dönüştü (prova/sınav senaryoları) | §5 evre 1 |
| Ay profili, Salda↔Jezero eklentisi (E-11) | REDLINE_RESEARCH §15 | İsteğe bağlı | §13 |
| NASA ACR 2024 referansı (2 kişilik ekip, basınçlı rover) | REDLINE_RESEARCH §2 | Taşındı (senaryo varsayımı) | §4.2, §15.6 |
| Moon to Mars hedefleri eşlemesi | REDLINE_RESEARCH §1.6 | İsteğe bağlı (slayt) | §11.2 |

### 20.1 İnsan-robot karşılaştırma deneyi (v2'den, korunur)
- Aynı görevin üç koşusu yapılır:
  1. yalnız harita;
  2. manuel rover keşfi;
  3. sistemin seçtiği otonom ön keşif.
- Başlangıç, kaynaklar ve gizli senaryo ortaktır.
- **Ölçümler:** tamamlanan bilim işi, yürünen mesafe, dönüş payı, robot maliyeti, müdahale sayısı, yanlış kabul/ret, karar süresi.
- Drone fayda sağlamıyorsa sistemin onu uçurmaması da geçerli bir sonuçtur.
- Küçük ekip içi deneme yalnız kullanılabilirlik bulgusudur; astronot performansına genellenmez.
