# T7 / T9 / T12 uygulama planı (S4, S0, S2, V3, tornado, MCAP)

15 Kasım 2026 · Claude Code. Taslak, üç üyeli bir LLM konseyinde (opus, sonnet, fable; anonim çapraz sıralama) incelendi ve düzeltildi. Bu dosya konseyin sentezidir. Kararlar kodlamadan önce **D015** olarak `docs/DECISIONS.md`'ye yazılır.

## 1. Neden değişti

Taslak üç yanlış sonuç üretecekti. Bunların hepsi kaynakta yeniden okunarak doğrulandı:

- **S2 iyimser çizgi gösterirdi.** Sızıntı yalnız O₂ *hızını* çarpıyordu; eve dönüş için gereken O₂ metabolik modelden önbelleğe alınıyor ve ölçeklenmiyordu (`field_model.py` `recompute`, hız `walkback_field.py` `crew_input`). ×3 sızıntıda çizgi yaklaşık 3 kat iyimser kalırdı.
- **S2 hiç koşamazdı.** `walkback_field` yalnız `eva.yaml` mürettebatına (`[EV1]`) abone oluyor ve ReturnToShelter hedefini başka mürettebat için reddediyor.
- **VOI robotu tehlikeye göndermiyordu.** Mevcut VOI, yol üstündeki olası engelli ayak izine 0 puan veriyor (`test_voi.py` bunu doğruluyor). Varsayılan kaya önseli 0 olduğu için engelli dal hiç çalışmıyor. Bu yüzden S4 bir tesadüf, V3 de döngüsel olurdu.

Diğer doğrulanmış eksikler:
- Nominal görev akışı yok: `mission_manager` TRAVERSE'te başlıyor ve PlanEva istemcisi yok.
- Planlayıcı rotayı hep habitattan başlatıyor; bu yüzden yeniden plan yalnız çıkıştan önce yapılabilir.
- `planner_server` hücre deltalarını almıyor ve delta QoS'u volatile (geç katılan düğümler ve v2 yarışı riski).
- Eşitlik kuralı en küçük kodu, O₂'yi seçiyor; "limiting = O2" sızıntıdan önce de doğru.
- Spek görüş hattı yükseklikleri anten 3 m, EV 2 m (§6).
- Gizli gerçek dosyası spekte `scenario_rocks_<seed>.json`.
- Çekirdek kaynaklar git'te izlenmiyor; sürüm kimliği için içerik hash'i gerekiyor.
- Sıra spek §18'e ters düşüyordu (T7, T9'dan önce gelir).

**Ortak ağaç:** diğer ajan `mission_manager.py`'ye isteğe bağlı bir oryantasyon akışı ekliyor (`intro_enabled`, `/redline/mission/advance`, `redline_core/eva_intro.py`, `test_eva_intro_node.py`; 15 Kasım 00:58–01:01). Görev akışındaki her değişiklik ekleyici olur. Dosya her düzenlemeden hemen önce yeniden okunur ve onların testi yeşil kalır.

## 2. Kesim çizgisi

| Katman | İçerik | Koşul |
|---|---|---|
| 1 — zorunlu | P0 sözleşmeler, P1 çekirdek, P2 temel + S0, P3 S4, P4 S2 | §17 S0/S2 ve §18 T7 kabulleri |
| 2 — iyi olur | P5: MCAP determinizmi, tornado, V3 öncü koşusu | Katman 1 kanıtlı bitmiş olmalı |
| 3 — ertele | V3 tam N, FR-08, `rover_placer`, kalp hızı modeli, `link_manager`, Open MCT | V3 tam N yalnız öncü koşu ve güç hesabından sonra |

Her fazdan sonra iki kapı var:
- Python ve ROS testleri yeşil olmalı. Şu anki sayılar 558 ve 37; diğer ajanın yeni testleri de dahil.
- S1 başlatma testi, gerçek S1 özeti (alarm, FR-04, alan, FR-12) ve `test_eva_intro_node.py` değişmeden geçmeli.

## 3. P0 — D015 sözleşmeleri (koddan önce)

**a. Tek mürettebat kaynağı.**
- Senaryonun `crew` listesi bütün düğümlere `crew_ids` olarak gider: `walkback_field`, `planner_server`, `ev_sim`, `mission_manager`, `rule_monitor`. Yoksa `eva.yaml` kullanılır.
- Her kimlik `crew.yaml`'da tanımlı olmalı.
- `eva.yaml`'a EV2 eklenmez, S1 tek kişilik kalır.
- Bir başlatma testi, düğümlerin aynı listeyi kullandığını doğrular.

**b. Zaman tabanı ve poz yetkisi.**
- Otomatik koşularda iki EV de `motion: plan` modunda yürür (SIMULATED, PET üzerinde, plan rotası ve model hızıyla). EV1 belirli bir mesafe arkada kalır.
- Unreal pozuyla yürüyen EV1 yalnız `time_scale` 1'de kullanılır; o zaman EV2 `follow` modundadır.
- Her EV'nin tek bir poz yayıncısı vardır; başka bir yayıncı görülürse `ev_sim` başlamaz.

**c. Sızıntı.**
- `ev_sim`, olaydan itibaren O₂ hızını `k_leak` ile çarpar (spek §8.2, SCENARIO). Fiziksel olarak sızıntı basınca bağlı bir akıştır; bu sınırlama kayda geçer.
- Çekirdek `leak_factor = o2_rate / O2(metabolic_w)`. Consumables mesajı iki alanı zaten taşıdığı için mesaj değişmez.
- `crew_margin` O₂ ihtiyacını bu faktörle ölçekler; FR-01 kendiliğinden doğru olur.
- PlanEva da mürettebat başına güncel faktörü kullanır.

**d. Senaryo olayları.**
- Kanonik yük `redline.scenario_event.v1`; çekirdekte encode/parse fonksiyonları ve testleri olur.
- `SUIT_LEAK` olayını yalnız `ev_sim` tüketir.
- `mission_manager` sızıntıyı telemetriden tespit eder: faktör eşiğin üstünde ve bir kalıcılık penceresi boyunca. Tespit gecikmesi ölçülen bir kabul büyüklüğüdür; sistem enjeksiyon zamanını bilmez.

**e. Görev akışı (çekirdek `mission_flow.py`).**
- Başlangıç evresi senaryoya göre seçilir; S1 TRAVERSE'te kalır.
- Akış:
  - BRIEFING: PlanEva → v1, `active_plan_id` atanır.
  - PRECURSOR: PET duraklatılır, robotlar kendi zamanında çalışır.
  - TRAVERSE ⇄ STATION_SCIENCE: plan PET'ine göre.
  - RETURN, ardından DEBRIEF: giriş olur ve habitatta tüketim durur.
- Her geçiş bir DecisionRecord yazar.
- Diğer ajanın `intro_enabled` akışı ayrı kalır; iki akış aynı anda açılamaz.

**f. Gözlem v2 (`redline.cell_observation.v2`).**
- Yeni isteğe bağlı alan `"passable": false`; v1 kayıtları geçerli kalır.
- Engelli hücreler ayrı bir `blocked` katmanında tutulur. Yayında `speed_factor = 0` olur ve `prepare_terrain`'de yasaktır (bölme yapılmaz).
- "Blocked kazanır" kuralı geçerlidir. Saplamada algılama sınırı var, yanlış pozitif üretmez; bu sınırlama kayda geçer.
- Tek bir çekirdek delta fonksiyonunu `walkback_field` ve `planner_server` birlikte kullanır.
- `cell_store` ek olarak birikimli, transient-local `/redline/cells/known` yayımlar (CellDelta tipi).
- Planlayıcı, uyguladığı evidence id'lerini DecisionRecord'a yazar.
- Bağlantı kuralları:
  - Erişilemez kalan istasyon plandan açık kayıtla düşer.
  - Engelli hücredeki mürettebatın payı NaN olur ve CAUTION verilir.
  - Sonsuz ihtiyaç −∞ olarak FR-01'e gider; bu mevcut davranıştır.

**g. Robot görev önerisi.**
- `/redline/robot_tasks/proposed` üzerinde yalnız DecisionRecord yayımlanır (transient-local, depth 1).
- Aday başına `redline.robot_task_proposal.v1` JSON kullanılır. Alanlar SurveyArea hedefine 1:1 karşılık gelir; ayrıca VOI terimleri, pay ve bilim biti taşır.
- `model_version` = VOI parametreleri + ızgara SHA'sı + bilgi sürümünün hash'i.
- `mission_manager` ayrıca, öneriyi referans veren bir `robot_task_dispatch` kaydı yazar.

**h. Gizli gerçek.**
- Spek biçiminde `scenario_rocks_<seed>.json` kullanılır: kaya listesi, `decor`/`navigation` sınıfı; S4 için senaryo yazarının yerleştirdiği bir kaya kümesi.
- Dosya senaryodan referanslanır ve yalnız SIMULATED gözlemciler okur.
- Bir izolasyon testi, planlayıcı, VOI ve walkback düğümlerinin dosya yolunu almadığını doğrular.
- Biçim, Gazebo spawn'ı için diğer ajanla paylaşılır.

**i. Tehlike modeli ve VOI (D011 VOI maddesinin yerine).**
- Tek kaya modeli kullanılır:
  - D < D_block kayalar sapma süresi ekler (λ, D010).
  - D ≥ D_block kaya hücreyi geçilemez yapar.
- Planlayıcı önseli Golombek k'dır (SCENARIO, `config/voi.yaml`). BXW'de kaya katmanı olmadığı açıkça yazılır.
- VOI = E_o[m(o'ya göre en iyi plan)] − E[m(mevcut plan gözlemsiz yürütülür; geç keşif dahil)]. Bu tanımda VOI ≥ 0'dır.
- Bu, spek §7.11'deki "margin_plan_şimdi" teriminin beklenen değer okumasıdır. Eski değer tanı alanı olarak kalır.
- Düşen istasyon, bilim biti olarak cezalandırılır.

**j. Görüş hattı (`los.py`).**
- Spek yükseklikleri kullanılır: anten 3 m, EV 2 m.
- Örneklenmiş DTM profili üzerinden hesaplanır; eğrilik terimi yok (100 m'de 1,5 mm).
- Açıklık payı ve histerezis `rules.yaml`'dadır; sonuç DERIVED'dir.
- 4 m'nin altındaki rölyefin görünmediği not edilir.
- FR-05 tek kişilik mürettebatta uygulanmaz.

**k. Keşif saplaması (`redline_env/scout_stub`, SIMULATED).**
- Donmuş `ExecuteScout`/`SurveyArea` action'larını tam uygular: fazlar, sonuç kodları, iptal, yinelenen `request_id`, bayat komut reddi.
- TF, odom veya `cmd_vel` yayımlamaz. Gazebo'da `scout_1` varsa başlamaz.
- Parametreler `config/drone.yaml`'dadır.
- Algılama sınırlıdır: sınırın altındaki hücreler NOT_DETECTED_LIMITED olur.
- Yalnız PRECURSOR'da uçar, bu yüzden FR-14 gerekçesiyle "uygulanamaz" olarak kaydedilir.

**l. Kurallar.**
- FR-05 açılır.
- FR-06, 07, 09, 13 ve 14 gerekçeyle yeniden hedeflenir.
- Kalp hızı NaN kalır (ertelendi).

## 4. P1 — Çekirdek (ROS yok)

Her madde TDD ile yapılır. Beklenen değerler üretim kodundan bağımsız hesaplanır.
- `cells` v2, delta fonksiyonu ve blocked yasağı. Testler: v1 aynen; v2 engelli; bilinmeyen anahtar reddedilir; önce engelli sonra geçilebilir gelince engelli kalır; yinelenen id etkisizdir; VOI ve gözlem ayak izi aynı hücre kümesini verir.
- VOI düzeltmesi. Testler:
  - VOI ≥ 0 (özellik testi);
  - olası engelli, yol üstü aday ilk sırada;
  - elle hesaplanmış iki istasyonlu örnek;
  - aday başına ≤ 50 ms.
  BXW için bir benchmark betiği aday sayısını ve toplam sıralama süresini kaydeder. Ucuz etki kontrolü: k ×0,5/×1/×2 için ilk-K adaylar yol üstünde mi ve VOI > 0 mı?
- `leak_factor` ve ihtiyaç ölçekleme; elle hesaplanmış pay.
- `mission_flow`: geçiş tablosu ve geçersiz geçiş testleri.
- `plan_follow`: PET üzerinde kinematik yürüyüş, servis süresi kadar bekleme, RETURN'de `return_path`, `follow` modu. Altın test: gürültü yokken yürüyüş planla birebir aynı.
- `los` ve `Fr05Tracker` (CAUTION, 60 s sonra WARNING, geri dönünce temizlenir; tek kişide uygulanmaz).
- `scenario_event` encode/parse; `scenario_rocks` üreticisi ve blocked kuralı.

## 5. P2 — Temel ve S0 (T9, 1. kısım)

- Mürettebat bağlantısı; `ev_sim` plan/follow modları.
- `mission_manager` nominal akışı ve PlanEva istemcisi: ekleyici değişiklik, oryantasyon akışı korunur. `mission_manager` için ayrı düğüm testi.
- `planner_server`: delta uygular, gerekince yeniden hesaplar, evidence id'lerini kaydeder.
- `rule_monitor` FR-05.
- Tek parametreli koşucu: `scripts/run-scenario-bxw.sh <senaryo>`. Kaydedici START'tan önce hazırdır (`auto_start:=false`, sonra ScenarioControl START).
- `S0_NOMINAL` (EV1+EV2). Başlangıç saati FR-12'yi tetiklemeyecek şekilde seçilir.

Kabul:
- INFO üstünde RuleViolation yok; CAUTION ve üstünde Alert yok.
- Plan sürümü baştan sona 1.
- Her geçişin DecisionRecord'u var; koşu DEBRIEF'te bitiyor.
- Negatif kontrol `S0b`'de (zorla ayrılma) FR-05 önce CAUTION, 60 s sonra WARNING veriyor.
- Sentetik başlatma testi ve gerçek BXW koşusu var; S1 değişmiyor.

## 6. P3 — T7 / S4

- `voi_tasker` (`redline_mission`): iş parçacığında çalışır, K = 5 öneri üretir.
- `scout_stub`: ilk-K adayı içeren bacak koridoru üzerinde SurveyArea yapar ve bütün şerit için kanıt üretir.
- `mission_manager` PRECURSOR akışı: görev gönder → kanıt kapısı (planlayıcı keşif kanıtlarını uygulamış mı?) → PlanEva → v2 → `replan` DecisionRecord. Kayıtta evidence id'leri, eski ve yeni plan, kazanılan pay (dakika) bulunur.
- `S4_BLOCKED_CORRIDOR` ve gerçek dosyası. Engel yeri VOI çalışmadan önce sabitlenir.

Kabul:
- Gözlem → hücre değişimi → v2 engelli hücrelerden kaçınıyor; v2'nin bütün istasyonları erişilebilir.
- DecisionRecord keşif kanıt id'lerini içeriyor.
- Karşı-olgu: engelsiz aynı koşu v2 üretmiyor.
- Engelin ilk-K ayak izine düşüp düşmediği ve önerinin engelli dal VOI'sinin > 0 olup olmadığı raporlanıyor.
- Gecikmeli delta varyantı ve action sözleşme testleri (iptal, PARTIAL, REJECTED, yinelenen `request_id`) var.
- Gerçek BXW koşusu var.
- Etiket: "S4 SIMULATED keşif saplamasıyla gözlendi; Gazebo drone bekliyor."

## 7. P4 — S2 (T9, 2. kısım)

- `ev_sim` sızıntıyı olay yükünden uygular.
- `mission_manager` telemetriden tespit eder; SUIT_LEAK EMERGENCY → CONTINGENCY → iki kişi için ReturnToShelter → RETURN (ikisi de eve yürür) → DEBRIEF.

Kabul:
- `limiting_crew_id` tespitten sonra bir tik içinde EV1'den EV2'ye geçiyor.
- O₂ CO₂ ve suya göre en az X dk açıkla sınırlayan.
- EV2'nin `margin_now`'ı elle hesaplanan değere eşit; abort alanı daralıyor.
- Tespit gecikmesi belirtilen sınırın altında.
- FR-01 sonucu gözlendiği gibi kaydediliyor.
- S1 regresyonu geçiyor.

## 8. P5 — T12 alt kümesi

**V3.**
- Çekirdek: `worlds.py` ve `execute.py`.
- Tasarım:
  - Dünyalar eşleştirilmiş (ortak rastgele sayılar).
  - Kollar: A yalnız yörünge; B VOI ile görevlendirilen robot; C eşit bütçeli rastgele gözlem; O kâhin (üst sınır).
  - Gerçek bağımsız üretilir: kümeli kayalar; 50 m bloklar için k hiper-önseli; yanlış belirtim ×0,5/×1/×2.
  - Gerçek fizik bilgi durumundan bağımsızdır; θ dünya başına bir kez çekilir.
  - Pay tabanı etkisi (D011 payları 63–154 dk) nedeniyle sıkılık taraması (rezerv / EVA süresi) zorunludur.
- Sonuçlar:
  - Birincil (sürekli, eşleştirilmiş): gerçekleşen en dar pay, ek dakika, tamamlanan istasyon ve bit; eşleştirilmiş bootstrap güven aralığı.
  - İkincil: P(pay < 0) ve P(pay < 30 dk); kol başına Wilson aralığı, ayrıca McNemar/Newcombe.
- Önce 20–50 dünyalık öncü koşu ve güç hesabı, sonra N.
- Ön kayıt dosyası içerik hash'leriyle tutulur.
- Etiket: "SCENARIO simülasyon çalışması; ampirik doğrulama değil."

**Tornado.**
- Çekirdek `sensitivity.py`.
- Birincil: plan v1 dondurulmuş. İkincil: yeniden planlı.
- Aralıklar kaynaklı (EWT c, IST 7,1–10,0, σ_θ, z_ε, σ ölçeği, gözlenmemiş hız çarpanı, rezerv) ya da etiketli ±%20.
- λ ve alacakaranlık gerekçeyle dışarıda (yapısal sıfır).
- Altyazı: "tek seferde bir parametre".

**MCAP.**
- MarginField kaydedilmez (≈ 2,25 MB).
- Determinizm: aynı tohumla iki canlı koşu. Sıralı olay anahtarları (tip, kod, plan sürümü, PET) PET toleransıyla karşılaştırılır.
- Replay: bag iki kez yeni bir tüketiciye oynatılır.
- Karar/kanıt tablosu JSON olarak çıkar.
- §17 Replay satırı yalnız "ROS yarısı" olarak işaretlenir.

## 9. Kanıt disiplini

- Her özet, büyüklük başına provenance statüsü yazar.
- Bir saplamanın spek bileşeninin yerini tuttuğu satır "tamam" işaretlenmez. T7 ve T9 "alt küme" olarak yazılır.
- Kayıtlar: DECISIONS (D015), VERIFICATION_LOG, PROGRESS, günlük, AI_DISCLOSURE.
- Satır sonları LF; paylaşılan belgeler her düzenlemeden önce yeniden okunur.
- Test ROS domain'leri 77 dışındadır.
- Diğer ajana bildirilecekler:
  - CellDelta'da `speed_factor = 0` anlamı;
  - `scenario_rocks` biçimi;
  - yeni topic'ler (`/redline/cells/known`, `/redline/robot_tasks/proposed`);
  - `mission_manager` akış parametreleri.
  Bunlar D015'e yazılır; uyumluluk için oryantasyon testi ve S1 her fazda koşar.

## 10. Konseyin ikinci tur ekleri

Aşağıdakiler D015'e de yazıldı:
- Oryantasyon akışı PRECURSOR'u atlıyor. Nominal akış onunla birleşir, yerine geçmez.
- Engelli kodlaması: depodaki iki tüketici aynı değişiklikte güncellenir ve ikisinin de düğüm testi olur.
- Yeniden plan yalnız PRECURSOR'da; donmuş `PlanEva.srv`'de başlangıç durumu yok.
- V3 çekirdekte koşar ve bu bir sapma olarak kaydedilir. Kılavuzun "1000 koşu ≤ 60 s" hedefi için önbellek tasarımı kullanılır.
- §0.2 sırasında T8 atlanıyor; gerekçesi kayıtlı.

Konsey sıralaması (üç oylayıcı, oybirliği):

| Üye | Ortalama sıra |
|---|---|
| opus | 1,0 |
| fable | 2,0 |
| sonnet | 3,0 |

Bütün metin: oturum scratchpad'i, `council/20261114-2300-t7-t9-t12-plan/`.

## 11. Kimsenin doğrulayamadıkları

- BXW'de VOI aday sayısı ve V3'te dünya başına süre.
- v2 yarışının pratikte ne sıklıkla oluştuğu.
- Python `mcap` paketleri.
- Diğer ajanın `scout_1` topic'leri ya da `scenario_rocks` spawn'ı planlayıp planlamadığı.
