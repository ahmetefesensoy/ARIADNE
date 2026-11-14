# REDLINE v3 — konsey sonucu (final)

Süreç: stage 1 (4 persona: opus veri bilimcisi, sonnet ürün/jüri, fable EVA ops, haiku red-team) → stage 2 anonim sıralama (4/4 oy) → başkan taslağı (draft_v1.md) → stage 3 karamsar tur. Stage 3'ün bağımsız alt ajanları API kullanım limitine takıldı (reset 15:00); karamsar tur başkan tarafından aynı bağlamda (Mini mode, bağımsız değil) üç persona ile yapıldı.

## Sıralama
| Üye | Ort. sıra | Kendisi hariç |
|---|---|---|
| opus (veri bilimcisi) | 1,25 | 1,33 |
| fable (EVA ops) | 2,25 | 2,33 |
| haiku (red-team) | 3,0 | 3,67 |
| sonnet (ürün/jüri) | 3,5 | 3,67 |

## Başkanın doğruladıkları (bu oturumda, salt-okunur)
- RAD sol 242 (`RAD_RDR_2013_101_07_02_0242_V00.TXT`): B sol 241 ort. 9,163 (n=24) → eşik 11,454; sol 242 zirve 12,13 (+%32,4); E zirve 10,87 vs 8,762 (+%24,1). 18 blok, ~1 saat kadans.
- RAD sol 4190 (`SOL_04134_04257/RAD_RDR_2024_140_18_30_4190_V00.TXT`): E doz hızı ~5,6 → 351 (≈×60), 93 blok, ~17 dk kadans. Rover o sol lat −4,7855 / lon 137,409 (MMGIS), boxwork kampanya başlangıcına ~1,5 km.
- Boxwork kampanyası (MMGIS, sol 4534–4805): lat −4,798…−4,809, lon 137,379–137,386; MMGIS son sol 5073.
- STAC `DTEEC_010573_1755_010639_1755_U01` mevcut (MRO HiRISE DTM, "Possible MSL landing site in Gale Crater").
- Eski AOI (lat −4,825…−4,791, lon 137,428–137,462) YKB'den ~13 km güneyde, boxwork kampanyasından ~2,5–5 km doğuda (stage 2 bulgusu + başkan hesabı).
- Challenge: "You may consider including at least three kinds of data" → öneri, zorunluluk değil (stage 2'de iki üye hackathlone HTML'inden doğruladı).

## Karamsar tur (3 persona) ve onarımlar
### Şüpheci gezegen bilimci
1. **YKB karnesi geriye bakış yanlılığı** (ciddi). Sonucu bilinen ünlü bir kararı "yeniden üretmek" döngüsel. → Onarım: **zaman bölmeli doğrulama** boxwork'te: yalnız sol 4533 öncesi arşivle plan, sonra Curiosity'nin sol 4534–4805 bulgularıyla (ChemCam/DAN Release 42'de sol 4843'e kadar) karşılaştır. Karar kuralı önceden dondurulur (git commit hash'i ile "önceden kayıt"). YKB yalnız "tutarlılık kontrolü" ve CRISM kaçırması dersi olarak kalır.
2. **σ = 3 DTM farkı bağımsız hata değil** (orta). Ortak MOLA kontrolü, eşkayıt hatası, farklı etkin çözünürlük. → "ampirik uyuşmazlık" de; önce eşkayıt; DTM eğimini rover tabanı (~3 m) ölçeğinde PLACES tilt ile karşılaştır; tek σ değil dağılım raporla.
3. **Sol 242 alarmı yalnız B dedektöründe, E'de değil; ~1 saat kadans 30 dk uyarıyı gösteremez** (ciddi). → Ana kriz **sol 4190 (20 Mayıs 2024)**: E'de ×60, 17 dk kadans, ileri sahanın 1,5 km yakınında, aynı olay MAVEN'le de gözlendi (MAVEN doğrulanmadı). Sol 242 "güneş kavuşumu: Dünya kör, yerel dozimetre tek uyarı" gerekçesine indirgenir.
4. **"Yeni bilim" iddiası** (orta). Takım bilim üretmez. → Çıktı "EVA bilim planı": hipotez, istasyon, cihaz, beklenen ölçüm; sonuç iddiası yok.
5. **Kaya tehlikesi kuralı (~0,75–1 m tespit sınırı) ürün değil, kural** (orta). → Varsa HiRISE gölge tabanlı kaya bolluğu ürünü (MSL iniş elipsi, Golombek ve ark.; doğrulanmadı) yörünge önseli olarak; yoksa kural etiketli.

### Yorgun hackathon jürisi
1. **Kavram çorbası** (ölümcül, Presentation). Güven katmanı, karne, ölçek merdiveni, sarı/kırmızı, STAC, PET, CAHV, Löwe… → Ekranda üç kelime: **Bilinen / Bilinmeyen / Kırmızı çizgi**. Tek kahraman görsel: haritada nefes alan kırmızı çizgi. Gerisi tıklamanın arkasında.
2. **"Harita mı oyun mu?"** (ciddi). Unreal + ROS simülasyon demosu gibi görünür. → Ana ürün haritadır (tablet/web + dışa aktarılan EVA kartı/GeoTIFF/STAC = challenge'ın "tool that generates maps" seçeneği). Unreal = aynı haritanın "prova görünümü". Her sahnede önce harita.
3. **Mars içerdekilere özgü dil** (ciddi). Sol, RDR, YKB… → İnsan hikâyesi: "İki astronot, birkaç saatlik oksijen, Güneş'ten gelen fırtına ve bilmediğini itiraf eden bir harita."
4. **Canlı demo kırılganlığı** (orta). → Deterministik replay modu; teslim zaten video/slayt.
5. **"Survival Guide" nerede?** (orta). → Kırmızı çizginin kendisi hayatta kalma rehberi; ürün adı/slogan buna bağlanır.

### EVA uçuş direktörü
1. **Sürekli "geri dönülebilir alan" gerçek planlamada tek başına kullanılmaz** (ciddi). Planlar zaman çizelgesi, istasyon başına sarf marjı ve karar noktalarıyla yapılır. → Çizgi PET'ten türetilir: her zaman adımında erişilebilir bölge; istasyonlar karar noktası (go/no-go).
2. **Metabolik veri Apollo 1/6 g, Mars 3/8 g, giysi bilinmiyor** (ciddi). → Parametrik giysi modeli + kaydırıcılar + **"kararı hangi varsayım değiştiriyor" duyarlılık grafiği**; Apollo/BASALT kaynakları etiketli.
3. **Robot öncü keşfi saniyeler içinde değil, EVA'dan sol'ler önce olur** (orta). → Zaman çizelgesi: öncü keşif evresi (drone/rover, EVA öncesi sol'ler) + EVA sırasında rover hareketli destek. Değer metriği: "robot saati başına kazanılan marj dakikası".
4. **SEP kuralı ve doz birimi** (orta). Gy ≠ Sv; RAD dozu insan dozu değil. → Kural "uyarı süresi ≥ sığınağa varış süresi"; kümülatif doz çubuğu "dokuya eşdeğer soğurulmuş doz, ölçüm yeri rover" etiketiyle; kariyer limitine kıyas yalnız açık uyarıyla (NASA 600 mSv standardı doğrulanmadı).
5. **İki motor tek dünya değilse senkron kopar** (ciddi). → Tek dünya manifesti: aynı DEM'den Gazebo heightmap ve Unreal arazisi; eqc → yerel ENU → site frame; sol/LMST ↔ UTC ↔ sim saati; sözleşme testleri.

## Final konsept
(Kullanıcıya verilen cevapta özetlendi.)

## Doğrulanmayanlar
Resmî challenge sayfası (SSL hatası) ve 2026 Judging Guide metni; DONKI kayıtları; MAVEN'in Mayıs 2024 gözlemi; Golombek kaya bolluğu ürünü; CRISM gözlem ID'leri; SEXTANT/BASALT bulgularının kesin sayıları; NASA 600 mSv; Navcam türev ürün tipleri; Ingenuity görüntü erişimi; boxwork için APXS/CheMin yayımı.
