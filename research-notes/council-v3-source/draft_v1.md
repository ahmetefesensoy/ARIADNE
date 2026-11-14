# REDLINE v3 — konsey sentezi taslağı (karamsar incelemeye girdi)

Bağlam: NASA Space Apps 2026, "Interplanetary Survival Guide: Martian Map". 48 saat, tam mühendis ekip, yeni depo. Yığın: ROS 2 Jazzy + Gazebo Harmonic (robot fiziği), Unreal 5.8.4 (insan sunumu). Kapsam kısıtı bu incelemenin konusu değil.

## Tez (tek cümle)
"Yörünge haritası EVA ölçeğinde neyi bilmediğini söylemez. REDLINE her bilinmezliği dakika cinsinden marja çevirir, robotları en pahalı bilinmezliğe gönderir ve yöntemini NASA'nın Yellowknife Bay'deki gerçek 2012–2013 kararlarıyla sınar."

## 1. İki saha, iki rol
- **Yellowknife Bay (YKB) = kalibrasyon sahası.** NASA burayı 2012'de yörünge katmanlarıyla seçti (Grotzinger+2014: HiRISE morfolojisi + yüksek termal atalet) ve yerde doğruladı. REDLINE aynı kararı yalnız yörünge verisiyle yeniden üretir ve karne çıkarır.
- **Boxwork-Batı (Mount Sharp) = ileri EVA sahası.** Challenge'ın kendi örneği. Curiosity kampanyası sol 4534–4805, enlem −4,798…−4,809, boylam 137,379–137,386 (MMGIS MSL_waypoints.json; başkan doğruladı). Bilim sorusu: "Doğuda görülen sırt-kil / çukur-karbonat farkı batıda da geçerli mi?" İnsan eşleştirilmiş sırt–çukur istasyonlarıyla birkaç EVA'da test eder.
- **Jezero = gövde-açık manifest testi** (opsiyonel üçüncü): aynı manifestle yüklenir; Perseverance'ta RAD olmadığı "ölçüm yok" rozetiyle beyan edilir.
- Not: eski 2×2 km Gale AOI John Klein'dan ~13 km güneyde; YKB için yeni kırpım gerekir (yeni depoda sıfırdan).

## 2. Katman yığını ve her katmanın karar rolü
| Katman | Ürün (erişim) | Statü | Karar rolü |
|---|---|---|---|
| Topografya | Trek `Gale_DEM_SMG_1m`; 3 HiRISE DTM (USGS STAC `mro_hirise_socet_dtms`, ör. DTEEC_010573_1755_010639_1755_U01); CTX DTM + `intersection_error` | ölçüm/türetilmiş | eğim, viewshed, ampirik σ |
| Optik | HiRISE ortho 0,25 m; HiRISE zaman serisi (ESP_030313, ESP_032436 rover'ı yörüngeden gösterir) | ölçüm | morfoloji, tespit sınırı (~0,75–1 m kaya) |
| Termal | THEMIS TI 100 m (±%20) | türetilmiş | kum vs pekişmiş kayaç önseli |
| Spektral | CRISM MTRDR (ID doğrulanmadı) | türetilmiş | mineral önseli; "tespit yok ≠ yok" |
| Jeoloji | USGS SIM 3292 (YKB = AHi, 87.031 km² tek poligon; boxwork = Htu) | yorum | ölçek merdiveni: "global harita burada durur" |
| Kimya | APXS supplement CSV, CheMin RDR (John Klein "preliminary") | ölçüm | istasyon kartı, hata çubuklu |
| Radyasyon | MSL RAD RDR (PDS PPI `MSL-M-RAD-3-RDR-V1.0`) | ölçüm | SEP alarmı |
| Atmosfer | REMS MODRDR | ölçüm | Go/No-Go penceresi |
| Yer gerçeği | PLACES poz + tilt (YKB'de 385 poz); Navcam/Mastcam (CAHV) | ölçüm | eğim RMSE, POV, alt-metre engel |
| Rota bağlamı | "Curiosity's Proposed Path" (PIA23179) + MMGIS gerçekleşen rota | türetilmiş/operasyonel | plan vs gerçekleşen sapması |
| Simüle | Gazebo rover/drone sensörleri | simüle | yeni deltalar (farklı renk) |

Challenge Resources listesindeki 5 kaynağın hepsi işlevsel: Mars Trek (DEM/CTX/THEMIS altlık + WMTS), USGS PGM (birim bağlamı), Proposed Path (rota dili + sapma), Worldview (swipe/zaman çizelgesi etkileşimi + opsiyonel Dünya analoğu), Perseverance Raw Images (Jezero POV, CAHV ile DEM'e izdüşüm).

## 3. Güven katmanı → marj
- Hücre şeması: değer, birim, ürün ID, GSD, edinim zamanı, işlem seviyesi, σ ve kaynağı, durum ∈ {tespit var | tespit yok (duyarlılık sınırlı) | gözlenmedi}, statü ∈ {arşiv | türetilmiş | simüle | senaryo}.
- σ veriden: 3 DTM farkı, CTX intersection_error, DTM eğimi vs PLACES rover tilt RMSE, THEMIS ±%20.
- Bilinmeyen hücre → hız cezası + süre belirsizliği → REDLINE çizgisi. Planlamacı "bilinmeyen bana kaç dakikaya mal oluyor" görür.

## 4. REDLINE çizgisi (operasyonel)
- Her hücre: dönüş süresi × marj ≤ en kısıtlı sarf (O₂, CO₂, soğutma, batarya). Ekranda hangi sarfın sınırladığı yazar.
- İki çizgi: sarı = terminate (düzenli dönüş), kırmızı = abort (hemen dön).
- Metabolik/hız modeli: SEXTANT (BASALT) yapısı, Apollo verisinden; BASALT bulgusu "gerçek süre > tahmin" marj çarpanının kaynağı. Mars giysisi için "Apollo/analog türevi varsayım" etiketi.
- İki astronot: çizgi = daha kötü durumdakine göre. Rover = alet arabası + iletişim rölesi + hareketli sığınak; DEM viewshed ile LOS iletişim katmanı.

## 5. Gerçek kriz: sol 242 SEP, John Klein, güneş kavuşumu
- RAD RDR `RAD_RDR_2013_101_07_02_0242_V00.TXT` (11 Nisan 2013). B dedektörü sol 241 ortalaması 9,163 → %25 eşik 11,454; sol 242 serisi 9,28 → 8,90 → 9,54 → 10,73 → **12,13** → 11,55 …; zirve +%32,4, 2 blok eşik üstü. E dedektörü zirve +%24,1 (eşiği aşmaz). (Başkan dosyadan yeniden hesapladı.)
- Bağlam: güneş kavuşumu → Dünya'dan komut yok → yerel dozimetre alarmı tek uyarı. Kural Löwe+2025 (≥%25, ≥30 dk uyarı).
- Dürüst çerçeve: insan için düşük doz (~50 µGy, Hassler+2014). Çizgiyi daraltan doz değil, "uyarı süresi ≥ sığınağa varış süresi" uçuş kuralı. Ayrı renkte, "karşı-olgusal ×k" etiketli ağır senaryo çizgisi. Eylül 2017 olayı Gale yüzeyindeki en büyük ölçülmüş referans (doğrulanmadı).
- "Hangi dedektör, hangi eşik" ekranda gerçek bir parametre (B alarm verir, E vermez).

## 6. Önce/sonra: önce tarih, sonra simülasyon
- **Birincil (arşiv):** yalnız yörünge önerisi vs Curiosity'nin gerçek izi ve bulguları. Karne: termal atalet → pekişmiş kayaç: isabet; HiRISE → kırıklı açık tonlu birim: isabet; CRISM → kil: **kaçırma** (toz örtüsü; CheMin ~%20 smektit). "Haritamız kili göremezdi ve bunu biliyordu."
- Yörünge vs yer: aynı yamada HiRISE DTM vs Navcam stereo türevleri; fark = yörüngenin bilmediği.
- **İkincil (simüle):** Monte Carlo yalnız duyarlılık analizi, "simüle dünyalar" etiketli.

## 7. Robotların rolü
- Drone ve rover "gözlenmedi / tespit sınırı altı" hücreleri çözer; görev seçimi bilgi değeri ile (hangi hücre en çok dakika marjı kazandırır).
- Her robot deltası bir kararı değiştirmiyorsa gösterilmez.
- Tarihî karşılık: HiRISE'ın rover'ı yörüngeden görmesi; Ingenuity hava görüntüleri (doğrulanmadı).

## 8. Çıktılar ve arayüz
- Üç biçim = üç rol: habitat ekranı = IV operatörü / yerel MCC (Mars gecikmesi); tablet = planlama/brifing; HUD = yalnız marj, sonraki istasyon, dönüş yönü.
- Sistem haritadan EVA zaman çizelgesi (PET) ve "cuff checklist" üretir.
- POV: her istasyonda gerçek Navcam/Mastcam karesi ile aynı CAHV pozundan Unreal render yan yana (swipe).
- "Güncel durum" paneli: her kaynağın son kaydı ve yaşı (MMGIS sol 5073, PDS Release 42 sol 4843 vb.); operasyonel akış vs arşiv ürünü ayrımı.
- Manifest = STAC Item/Collection, ürün başına CRS (Gale eqc R=3.396.190; SIM 3292 Robinson; Jezero CTX 3.396.160).

## 9. Beş görev → tek EVA'nın evreleri
1. Brifing/Go-No-Go (eski eğitim/sınav → prova ve brifing)
2. Robot öncü keşif (drone + rover)
3. Traverse (iki astronot)
4. İstasyon bilimi (numune/sondaj; numune kökeni ≠ analiz yeri; APXS koordinatı rover pozudur, hedef değil)
5. Dönüş/acil durum (eski vana/kaçak → giysi kaçağı acil durumu, çizgiyi doğrudan sürer; SEP alarmı)

## 10. Jüri anlatısı (Impact, Creativity, Validity, Relevance, Presentation)
- Açılış: ölçek merdiveni (SIM 3292 poligonu 87.031 km² → Trek CTX → HiRISE DEM 1 m → robotla güncellenen hücre).
- Orta: YKB karnesi + sol 242 gerçek SEP replay.
- Kapanış: aynı yığınla boxwork-Batı EVA planı, zaman çizelgesi, en belirsiz hücreye giden robot.
