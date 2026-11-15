# Space Apps sunum planı: review, 5 saatlik iş planı, 7 slayt

15 Kasım 2026, 13:30 (+03:00) · Claude Code · Okur: REDLINE ekibi (sunumu hazırlayan ve yapan kişiler).

Kural: slayta ve videoya yalnız kanıt dosyası olan iddia girer. Denetim otomatik:
`python scripts/space_apps_claims.py` → `docs/verification/SPACE_APPS_CLAIMS.json`
(iddialar `config/space_apps_claims.yaml`). FAIL veren iddia slayttan çıkar; NOT YET olan hedef
yalnız "in progress" diye söylenir. ROS 116/116 sayısının kalıcı raporu deftere bağlanmadığı için
slaytta kullanılmaz. Hedef ile test sonucu ayrı yazılır.
Bitmemiş iş "devam ediyor" diye söylenir. Sayıların hepsi aşağıdaki kanıt sütunundan okundu.

---

## 0. Jürinin üç sorusu: hangi veri, amaç ne, sonuç ne

Bu üç cevap her slaytta aynı kalır. Sunumda üçü de kanıtla söylenir.

### Amaç (tek cümle)

**TR:** Mars'ta yürüyüşe çıkan bir ekibe her an tek bir soruya canlı cevap vermek: "Bildiklerimiz,
bilmediklerimiz ve şu anki radyasyonla ne kadar uzağa gidip zamanında geri dönebiliriz?" Ve önce
hangi bilinmeyene robot gönderilmesi gerektiğini göstermek.

**EN (slayt):** *Tell a Mars space-walk crew, live, how far they can go and still get back to shelter
in time, given what the map knows, what it does not, and today's radiation; and which unknown a robot
should check first.*

### Hangi veri ve ne işe yaradı

Kural: her veri bir karara bağlı. Süs olarak kullanılan katman yok.

| Veri (görev / alet) | Ürün | Ne kararı besliyor | Statü |
|---|---|---|---|
| MRO HiRISE stereo arazi modeli (USGS işlemesi) | `MSL_Gale_DEM_Mosaic_1m_v3` (ESA HRSC ve MOLA kontrol girdili mozaik), BXW 3×3 km kesit | Eğim, yürüme süresi, sığınağa dönüş süresi, 1 m oyun arazisi | ARCHIVE → DERIVED |
| MRO HiRISE ikinci DTM | `DTEEC_019698_1750_019988_1750_U01` | İki DTM farkı = arazi belirsizliği (σ): "bilinmeyen" haritası | ARCHIVE → DERIVED |
| MRO HiRISE renkli mozaik | `MSL_Gale_HiRISE-LRGB_78quads_sharp_cog` | Oyundaki ve tabletteki gerçek yüzey rengi, saha haritası | ARCHIVE → DERIVED |
| MSL RAD radyasyon dedektörü | PDS PPI `MSL-M-RAD-3-RDR-V1.0`: `RAD_RDR_2024_139_17_46_4189_V00`, `…_140_18_30_4190_V00`, `…_141_19_08_4191_V00` | Gerçek 20 Mayıs 2024 fırtınası: alarm, uçuş kuralı, çizginin daralması | ARCHIVE |
| MSL APXS X-ışını spektrometresi | PDS Geosciences `msl_apxs_supplement_sols_0_2301` (690 ölçüm; Berger vd. 2020) | Bilim aletinin ölçüm hatası modeli: istasyonda ne kadar süre, ne kadar yakın | ARCHIVE → DERIVED |
| NAIF SPICE | `naif0012.tls`, `pck00011.tpc`, `de440s.bsp` | Güneş açısı, gün ışığı payı, yerel saat, Dünya'ya ışık süresi (15,8 dk) | DERIVED |
| NASA EWT çalışması (NASA/TP-2009-214796) | 3/8 g giysili yürüme oksijen maliyeti | Oksijen ve pil tüketimi, dönüş payı | literatür → SCENARIO parametre |
| Löwe vd. 2025 (arXiv 2502.02469) | %25 artış alarm kuralı, ≥30 dk uyarı | Fırtına alarmının ne zaman çalacağı | literatür |
| NASA 3D Resources | Curiosity modeli | Yalnız görsel | görsel |

Ayrıntılı, hash'li liste: [DATA_SOURCES.md](DATA_SOURCES.md). Söylenmeyecek: "bütün veri NASA'nın"
(DEM'de ESA HRSC girdisi var), "pH ölçtük", "drone haritaladı" (drone gözlemi simüle).

### Sonuç (kanıtlı, sırayla)

1. **Fırtına:** gerçek 2024 radyasyon verisi tekrar oynatıldığında alarm anında (0 s) sığınak moduna
   geçildi. Fırtına sırasında güvenli dönüş alanı 6,02'den 0,41 km²'ye indi (−%93).
2. **Robot keşfi:** simüle drone rotada 16 engelli hücre buldu. Plan değişti, en dar planlanan pay
   58,6'dan 64,3 dakikaya çıktı. Engel olmayan karşı-olgu koşusunda plan korundu.
3. **Acil durum:** giysi kaçağı yalnız telemetriden 36 saniyede yakalandı. Bütün ekip eve döndü, en
   düşük pay +17 dk kaldı, uçuş kuralı ihlali olmadı.
4. **Veriden çıkan bulgu:** 690 gerçek APXS ölçümü, altı ana oksitte ölçümü 6 kat uzatmanın hatayı
   yalnız %7–29 azalttığını gösteriyor (sayım yasasının beklentisi %59). Aletin her cm uzaklığı hatayı %6–24 artırıyor.
   Yani istasyonda zamanı uzun ölçüme değil, iyi yerleştirmeye harcamak gerekiyor. Modeli buna göre
   değiştirdik.
5. **Neye duyarlı:** fırtına anındaki güvenli alanı en çok uyarı süresi (0,25–0,82 km²) ve robotun
   görmediği arazide ne kadar yavaş yürüdüğümüz (0,31–0,54 km²) değiştiriyor. Bu, bilinmeyeni önce
   robotla çözmenin neden değerli olduğunu sayıyla gösteriyor.
6. **Henüz değil:** Unreal'da canlı fırtına görünümü (C1 bu blokta deneniyor), ikinci saha (YKB)
   kontrolü, fiziksel drone uçuşu.

Kanıt dosyaları: §2.1 tablosu ve `docs/verification/SPACE_APPS_CLAIMS.json`,
`docs/verification/SENSITIVITY.json`.

---

## 1. Tek paragraf sonuç

Teknik temel güçlü: gerçek NASA verisi, köken etiketleri, çalışan ROS 2 zinciri, üç senaryo
kabulü (S1 fırtına, S2 giysi kaçağı, S4 drone keşfi) ve birinci şahıs Unreal provası var.
Sunum açısından üç büyük risk var:

1. **Ürün kimliği kayması.** Kılavuzdaki karar "önce harita, sonra simülasyon". Son iki günün
   emeği oyuna gitti. Jüri "Mars oyunu" görürse Relevance puanı düşer. Challenge bir **harita /
   araç** istiyor.
2. **Kahraman anı Unreal'da kanıtlı değil.** "Gerçek fırtına gelince kırmızı çizgi daralır"
   ROS'ta kanıtlı (6,02 → 0,41 km²). Unreal'daki canlı görünüm (T6) kabul edilmedi:
   `test-results/t6-eva-live/capture.json` `passed:false`. Alarm PET 111,8 dk'da geliyordu.
   Şu anki kampanya launch'ında RAD replay / rule_monitor yok (D022). Çözüm hazır: C1 bölümü
   (aşağıda, P0-2).
3. **Doğrulama (T12) yok.** YKB tutarlılık kontrolü ve duyarlılık analizi yapılmadı. Jüri
   "gerçekten çalışıyor mu, neye duyarlı?" diye sorarsa elimizde senaryo koşuları ve testler var,
   bağımsız doğrulama yok.

---

## 2. Review: ne çalışıyor, ne çalışmıyor

### 2.1 Kanıtlı olanlar (slayta girebilir)

| İddia | Sayı | Kanıt |
|---|---|---|
| Gerçek fırtına verisi | 20 Mayıs 2024, Curiosity RAD E: 5,72 → 351,4 µGy/sa (~61×). İlk %25 alarmı 05:21:50 UTC, tepe 06:15:19 UTC (≈53 dk) | `docs/verification/T6_RAD.json` (all_pass) |
| Dünya'dan yardım geç gelir | O an Dünya–Mars tek yön ışık süresi 15,8 dk, gidiş-dönüş ≈32 dk | SPICE de440s + naif0012, barycentre (DERIVED; bu planda hesaplandı) |
| Fırtına çizgiyi daraltır (ROS) | S1: alarm → FR-04 0 s gecikme; güvenli dönüş alanı 6,02 → 0,41 km² | `journal/PROGRESS.md` T6 kaydı, `journal/log/2026-11-14-t6-sep-hatti.md` |
| Robot bilinmeyeni çözer, plan değişir | S4: drone koridor taraması → 16 engelli hücre → plan v1 → v2 (en dar planlanan pay 58,6 → 64,3 dk); karşı-olgu S4c'de plan korunur | `docs/VERIFICATION_LOG.md` 10:10 kaydı |
| Telemetriden acil durum | S2: EV2 O₂ kaçağı 36,4 s'de yakalandı → herkese eve dönüş; sınırlayan kaynak EV2/O₂; en düşük pay +17,3 dk; FR-01/04/12 korundu | `VERIFICATION_LOG.md` 10:25, `s2_acceptance.json` |
| Veriden öğrendiğimiz bir şey | APXS ölçüm hatası süreyle neredeyse azalmıyor (üs −0,04…−0,1; varsayım −0,5). 690 arşiv ölçümü. Hata, standoff'un her cm'inde %6–30 artıyor → iyi yerleştirme uzun ölçümden değerli | `docs/verification/APXS_PRECISION.json`, D018 |
| Gerçek arazi | BXW 3×3 km, HiRISE DTM'den 1 m ızgara; Unreal'da 2,75 km 1 m yüzey (15,3 M üçgen), 3 noktada DEM farkı ≤ 2 cm | T1 kabulü, `docs/verification/SURFACE_V2_IMPORT.md` |
| Rover otonomisi | Gazebo + Nav2: RViz'den verilen hedefe sürüş kabulü | `docs/verification/T3_RVIZ_ACCEPTANCE.json` |
| Testler | Python 700/700 (15 Kasım 13:20). ROS 116/116 (10:25 derlemesi) | yerel koşu; `ws-5dacf41d08de2c4c-hupd88fp` |

### 2.2 Yapılmadı veya kanıtsız (slayta "bitti" diye girmez)

| Konu | Durum |
|---|---|
| Unreal'da canlı alarm + çizgi daralması (T6) | Kabul yok. C1 ile denenecek (P0-2). |
| YKB tutarlılık kontrolü, V1–V3, duyarlılık (T12–T13) | Yok. Duyarlılık 5 saatte yapılabilir (P1-1); YKB yapılamaz. |
| Drone'un fiziksel uçuşu | Gazebo uçuş modeli yok. Drone gözlemi gizli gerçekten okunan SIMULATED veridir. |
| Bilim ürünleri | SIMULATED. Kimya kalibre edilmemiş SCENARIO; pH `model_only`. "Ölçtük" denmez. |
| Open MCT / operasyon telemetri ekranı (T11) | Yok. |
| EV2 ve basınçlı rover Unreal'da | Bağlı değil. |
| Hızlı yolculuk | Yalnız sözleşme (D022). |
| Oyun içi E etkileşimi, brifing videoları, tablet harita sayfası, ayak izi/toz | Kod derlendi; canlı oyunda görülmedi. Ayak izi/toz otomasyon testi koşulmadı. |
| Yeni kum shader'ı | Materyaller hatasız derleniyor (673 PS komutu; eskisinin yaklaşık iki katı). FPS ölçülmedi. |
| Alçak 3D engelle tam navigasyon | Kabul başarısız kaldı. |

### 2.3 Bulunan hatalar ve riskler (önem sırasıyla)

1. **Relevance:** sunum oyunla açılırsa ürün "oyun" sanılır. Haritayla aç, oyunu "provası" diye göster.
2. **Hero shot:** T6 Unreal görünümü yok (yukarıda). Videonun en önemli 10 saniyesi bu.
3. **AI beyanı:** videoda AI üretimi müzik (Suno 6) ve AI üretimi 3D modeller (Tripo) var.
   Space Apps kuralı ([GO Team #1849](https://github.com/nasa/spaceapps/discussions/1849)): görünür
   "AI-generated" işareti. Videoya sabit alt yazı gerekir. NASA logosu AI içeriğinde kullanılmaz.
4. **Dil:** teslim İngilizce. Oyun arayüzü Türkçe. Slayt ve video alt yazısı İngilizce olmalı.
5. **Kısaltmalar:** eğitim kuralı "açıklanmamış kısaltma yok". EVA, SEP, PET, RAD, APXS, LIBS,
   DAN, ROS, VOI ilk geçtiği yerde açılır ya da hiç kullanılmaz. Slaytlarda "space walk",
   "solar storm", "radiation detector" demek yeterli.
6. **Snapshot ↔ depo farkı:** yeni kum, ayak izi ve metal materyalleri yalnız
   `%LOCALAPPDATA%\Redline\T4Build` içinde. Depodaki `Content/` eski sürüm. Teslimden önce
   bilinçli olarak eşitlenmeli. Codex iki sürümü de korudu; bu karar kullanıcınındır.
7. **Canlı demo riski:** WSL 15,5 GB; Gazebo + Unreal + ROS birlikte bir kez taşma yaptı.
   Sunumda canlı demo yerine kayıtlı video oynatılır; canlı oyun yalnız yedek ya da soru-cevapta.
8. **Commit yok:** depo büyük ölçüde commit'lenmemiş. Public link isteniyorsa kullanıcı commit/push
   yapar; büyük ikili dosyalar ve kısıtlı lisanslı varlıklar için ayrı karar gerekir.

---

## 3. Sorun → çözüm (sunumun omurgası)

**Sorun.** Mars haritaları (Mars Trek, USGS jeoloji haritası) bölgesel ölçekte çalışır. Astronotun
adım attığı ölçekte haritanın neyi bilmediğini söylemez. Oysa ne kadar uzağa gidilebileceği,
oksijene, araziye ve dakikalar içinde değişen radyasyona bağlıdır. 20 Mayıs 2024'te Curiosity'nin
radyasyon dedektörü 53 dakikada 61 kat artış gördü. Dünya'ya soru sorup cevap almak 32 dakika
sürerdi. Karar sahada verilmek zorunda.

**Çözüm.** REDLINE her bilinmeyeni dakika cinsinden dönüş payına çevirir ve tek bir çizgi çizer:
mürettebatın sığınağa zamanında dönebileceği alanın sınırı. Robot bir bilinmeyeni çözünce çizgi
genişler. Güneş fırtınası gelince uçuş kuralı ("uyarı süresi ≥ sığınağa varış süresi") çizgiyi
daraltır. Bunu birinci şahıs bir simülasyonda prova ediyoruz; robotların fiziği ROS 2/Gazebo'da.

**Değer.** Yedi veri katmanı yerine bir sayı (dakika) ve bir çizgi. Her karar kayıtlı ve geri
izlenebilir. Her veri parçasının kökeni ekranda: arşiv / türetilmiş / simüle / senaryo.

---

## 4. Beş ölçüt: durum ve yapılacak

| Ölçüt | Bugün | 5 saatte güçlendiren |
|---|---|---|
| Impact | Hikâye güçlü; kullanıcı ve etki anlatılmadı | Slayt 6: kim kullanır (EVA planlayıcısı, analog saha ekipleri), ne kazanır |
| Creativity | Belirsizliği dakikaya çevirmek, nefes alan çizgi, oyunlaştırılmış prova | Kahraman anının videosu (C1) |
| Validity | Gerçek RAD/APXS/DTM, S1/S2/S4, 700+116 test | Duyarlılık (tornado) grafiği; sınırlar açıkça |
| Relevance | Challenge harita/araç istiyor; biz oyunla görünüyoruz | Harita kartı ile açılış; oyun "prova görünümü" |
| Presentation | Görsel malzeme bol, akış yok | 7 slayt, 240 s, üç prova, yedek video |

---

## 5. Jürinin sekiz sorusu ve cevapları

1. **Neden bu problem?** Mars'ta yürüyüş mesafesini bilinmeyenler ve dakikalar içinde değişen
   radyasyon belirler. Dünya 32 dakikalık gidiş-dönüş uzaklıkta. 2024 fırtınası gerçek bir örnek.
2. **Özgün olan ne?** Harita belirsizliğini dakika cinsinden paya çevirmek; çizginin hem robot
   kanıtına hem uzay havasına tepki vermesi; dozu değil uçuş kuralını sınır yapmak; her verinin
   köken etiketi.
3. **NASA verisi nasıl kullanıldı?** MRO HiRISE DTM ve renkli görüntü → 1 m arazi; MSL RAD sol
   4189–4191 → fırtına replay; MSL APXS 690 ölçüm → bilim aleti gürültü modeli; NAIF SPICE →
   Güneş açısı, gün ışığı, ışık süresi; MMGIS → rover konumları. Liste: `docs/DATA_SOURCES.md`.
   DEM'de ESA HRSC girdisi de var; "tamamı NASA" denmez.
4. **Bilimsel/teknik temel?** Giysili yürüyüş metabolik maliyeti, maliyet-mesafe ile sığınağa
   dönüş süresi alanı, z = 1,645 ile risk düzeltmesi, Löwe vd. 2025 alarm kuralı (%25 artış,
   ≥30 dk uyarı), robot için bilgi değeri. Altın testler spek formüllerinden bağımsız hesaplandı.
5. **Gerçekten çalışıyor mu?** S1, S2, S4 kabul koşuları gerçek BXW ızgarasında geçti (sayılar
   §2.1). Unreal'da canlı fırtına görünümü: P0-2 sonucuna göre "geçti" ya da "devam ediyor".
6. **Kısıtlar?** Giysi parametreleri senaryo. Drone gözlemi simüle. Bilim kimyası kalibre değil.
   Tek saha. RAD soğurulmuş dozu (Gy) ölçer, insan etkin dozunu (Sv) değil. YKB kontrolü yapılmadı.
7. **Nasıl geliştirilir?** YKB tutarlılık kontrolü, Monte Carlo duyarlılık, drone için gerçek algı,
   analog ekiplerle kullanıcı testi, Jezero ve Ay güney kutbu, operasyon ekibi için Open MCT.
8. **En önemli etki?** "Ne kadar uzağa gidebiliriz?" sorusu tek bir sayıya ve canlı bir çizgiye
   dönüşüyor; karar izlenebilir. Aynı hat başka sahaya manifestle taşınıyor.

---

## 6. SWOT

| Güçlü | Zayıf |
|---|---|
| Gerçek NASA verisi ve köken etiketleri; uçtan uca çalışan ROS + Unreal; üç kabul koşusu; veriden çıkan gerçek bulgu (APXS); güçlü görsel | Unreal fırtına görünümü kanıtsız; doğrulama ve duyarlılık eksik; drone/bilim simüle; arayüz Türkçe; 4 dakikada anlatması zor |
| **Fırsat** | **Tehdit** |
| Artemis EVA planlaması; analog saha testleri; manifestle yeni sahalar; eğitim simülasyonu; açık veri (STAC) | Jüri oyunu araçtan ayıramaz; abartılı iddia riski; canlı demo çökmesi; zaman; iki ajanın aynı ağaçta çakışması; AI beyanı kuralı |

---

## 7. Beş saatlik iş planı

Sahipler: **C** = Claude Code (ROS/Python/doğrulama/sunum malzemesi), **X** = Codex (Unreal; şu an
saha işleri, tablet ve kayıt aracı üzerinde), **K** = kullanıcı (kayıt, kurgu, sunum, commit).
Her blok sonunda kanıt yazılır; geçmeyen iş slayta "devam ediyor" diye girer.

| Saat | Öncelik | İş | Sahip | Bitti ölçütü |
|---|---|---|---|---|
| 0–1 | P0-1 | İddia defteri: her slayt iddiası → kanıt dosyası → geçti/geçmedi, otomatik kontrol | C | `docs/verification/SPACE_APPS_CLAIMS.json` tümü yeşil ya da kırmızılar slayttan çıkmış |
| 0–1 | P0-2a | C1 canlı backend betiği (gerçek 4190 alarmı PET 11,8 dk; ×1; EV1 Unreal'dan) ve simüle yürüyücüyle başsız deneme | C | alarm + FR-04 + çizgi daralması kaydı |
| 0–1 | P0-3 | E, brifing, tablet harita sayfasının canlı oyunda görülmesi; engel varsa düzeltme | X | oyun içi ekran kaydı |
| 0–1 | P0-4 | Temel klipler: hava kilidi/çıkış, Mars'ta yürüyüş, tablet haritası, RViz sayfası | K | F10 kaydı (`RedlineShotRecorder`) |
| 1–2 | P0-2b | **Kahraman çekimi:** C1 backend + Unreal EV1; ~300 m çık, alarm, çizgi daralır, dön | K + C | kayıt + capture.json `passed:true` → T6 Unreal kabulü güncellenir |
| 1–2 | P1-1 | Duyarlılık (tornado): giysi, yürüme hızı, σ katsayısı, uyarı süresi → güvenli alan ve pay | C | `docs/verification/SENSITIVITY.json` + PNG |
| 2–3 | P1-2 | Harita kartı: tablet atlası katmanları, köken lejantı, istasyonlar, normal ve fırtına çizgisi; tek sayfa, çevrimdışı | C | slayt 3 görseli + açılabilir sayfa |
| 2–3 | P1-3 | Slayt figürleri gerçek veriden: RAD eğrisi, S1 alan, S4 v1→v2, APXS bulgusu | C | PNG'ler + üreten betik |
| 2–3 | P1-4 | Bilim görevi animasyon cilası / drone sunumu (zaman kalırsa) | X | kayıt |
| 3–4 | P0-5 | 7 slaytı İngilizce kur; video kurgusu; AI alt yazısı | K (+C metin) | deste + video |
| 4–5 | P0-6 | 3 tam prova (240 s), soru-cevap provası, yedek video, son dürüstlük kontrolü (iddia defteri) | K + C | süre ≤ 240 s |

Bu 5 saatte **yapılmayacaklar:** YKB sahası, Open MCT, Gazebo drone fiziği, hızlı yolculuk,
yeni 3D model. Bunlar slayt 6'da "sonraki adım" olarak geçer.

Durma kuralı: P0-2b saat 2'nin sonunda geçmezse kahraman anı için S1 ROS kaydı (ue_feed replay)
ve RAD eğrisi + alan figürü kullanılır; ekranda "ROS run, Unreal live view in progress" yazar.

---

## 8. Yedi slayt (240 s)

Slayt metni İngilizce (teslim dili); konuşma notu Türkçe. Her slayt tek mesaj.

| # | Süre | Mesaj | Ekranda | Görsel / video | Konuşma (özet) |
|---|---:|---|---|---|---|
| 1 Açılış | 20 s | Bir insan hikâyesi | **REDLINE — Known · Unknown · Red line.** "Two astronauts. A few hours of oxygen. A solar storm. And a map that admits what it doesn't know." | Unreal: hava kilidinden Mars'a çıkış, yerde kırmızı çizgi (3–5 s klip) | Hikâye cümlesi, ekip adı. |
| 2 Problem | 35 s | Haritalar bilinmeyeni söylemez; radyasyon dakikada değişir; Dünya geç kalır | "20 May 2024, Curiosity: radiation ×61 in 53 min. Earth: 32 min round trip." "Mars maps are regional. They don't say what they don't know." | Gerçek RAD eğrisi (alarm ve tepe işaretli) | Mars Trek/USGS ölçeği; karar sahada verilmek zorunda. |
| 3 Çözümün değeri | 35 s | Amaç: bilinmeyen → dakika → tek çizgi | Başlık = amaç cümlesi: "Our goal: tell the crew, live, how far they can go and still get back in time." Altında: "Every unknown becomes minutes of return margin." Lejant: ARCHIVE · DERIVED · SIMULATED · SCENARIO | Harita kartı: normal çizgi ve fırtına çizgisi yan yana (6,02 → 0,41 km²) | Robot çözünce genişler, fırtına gelince daralır. |
| 4 Nasıl çalışıyor | 65 s | Her NASA verisi bir karar verir | Sol yarı **"Data → decision"** şeridi (5 satır): HiRISE 1 m terrain → walking time home · two HiRISE terrain models → where the map is unsure · Curiosity radiation detector → storm alarm · Curiosity X-ray spectrometer (690 measurements) → how long and how close to measure · NASA SPICE → daylight and Earth delay. Sağ yarı akış: model → flight rules + robot scouting (ROS 2 / Gazebo) → first-person rehearsal (Unreal 5) + tablet map | Şema + 2 kısa ekran: RViz/rover, tablet harita sayfası | Jürinin "veriyi nasıl kullandınız" sorusu burada cevaplanır: süs katman yok, her veri bir karara bağlı. Tek fizik otoritesi kuralı; uçuş kuralı dozu değil süreyi sınar. |
| 5 Demo / kanıt | 45 s | Çalışıyor; sonuçlar hedeflerden ayrı | Sol: video (C1 alarm → çizgi daralır → dönüş). Sağ "Tested": storm run FR held, area 6.02 → 0.41 km²; simulated drone found 16 blocked cells → new plan; suit leak caught in 36 s → all home, margin +17 min; 700 automated tests. Alt "Not yet": live drone flight, second-site check | C1 kaydı (yoksa S1 replay) | Test sonucu ile hedefi ayrı söyle. |
| 6 Etki | 30 s | Kim kullanır, ne kazanır, ne öğrendik | "For EVA planners and analog field teams: one number, one line, every decision traceable." "Learned from NASA data: measuring 6× longer cut the error only 7–29%; each cm closer matters more." "Biggest levers: warning time, and walking over ground no robot has seen." Next: second site, Moon south pole, analog tests | APXS bulgu grafiği + tornado | Sonuç cümlesi: veriden öğrendik ve modeli değiştirdik; robotla keşfin değeri sayıyla görünüyor. Manifestle başka sahaya taşınır. |
| 7 Kapanış | 10 s | Akılda kalan cümle | "Known · Unknown · Red line." Repo bağlantısı. "NASA data not AI-generated. Some 3D models (Tripo) and music (Suno) are AI-generated." | Logo yok; kapanış karesi | Teşekkür. |

Hazır figürler (gerçek veriden, `python scripts/space_apps_figures.py` ile yeniden üretilir):
slayt 2 → `docs/figures/space_apps/fig_rad_storm.png`; slayt 6 → `fig_apxs.png` ve
`fig_sensitivity.png`. Harita kartı (slayt 3) ve S4 plan v1/v2 figürü henüz yok.

Kısaltma kuralı: slaytta EVA yerine "space walk", SEP yerine "solar storm", RAD yerine
"radiation detector". APXS bir kez "X-ray spectrometer (APXS)" diye açılır.

---

## 9. Video çekim listesi (oyundan)

Her klibin köşesinde sabit etiket: "Simulation rehearsal · robot physics in ROS 2/Gazebo ·
archive radiation data · scenario crew". Ayrıca bir kez: "Contains AI-generated 3D models and music".

| Klip | İçerik | Kaynak | Not |
|---|---|---|---|
| A | Hava kilidi → Mars yüzeyi, ilk adım | `start-t5-eva.ps1` prologue | 5 s yeter |
| B | Tablet: saha haritası sayfası, istasyonlar, dönüş konturları | T tuşu, sayfa 7 | harita = ürün |
| C | İstasyonda E → görev, "nasıl çalışır" videosu | kampanya | E canlıda doğrulanırsa |
| D | **C1: alarm banner'ı → çizgi daralır → geri dönüş** | C1 backend + Unreal | kahraman çekimi |
| E | RViz / Gazebo rover sürüşü | tablet sayfa 0 veya RViz | gerçek ROS pikselleri |
| F | S4: drone kanıtı → plan v2 | atlas üstüne plan v1/v2 figürü | Unreal drone sunumu kabul değil; figür kullan |

## 10. Yedek plan

- Sunumda video yerel dosyadan oynar (internet yok sayılır). Aynı videonun ikinci kopyası USB'de.
- Canlı oyun yalnız soru-cevapta ve yalnız önceden açık, ısınmış makinede.
- C1 kaydı alınamazsa: S1 ue_feed replay figürü + RAD eğrisi.
- Slayt PDF'i ayrıca dışa aktarılır.
