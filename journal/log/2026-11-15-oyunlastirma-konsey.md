# Oyunlaştırma konseyi, APXS kalibrasyonu, bölüm mesafesi ve debrief notu

15 Kasım 2026 · Claude Code (bu oturum). Diğer ajanın kampanya ve Unreal işleri sürerken yazıldı.

## Konsey

Kullanıcı şunu istedi: daha oyun gibi, daha sinematik, daha çok bilim görevi ve bunların simülasyonları. Üç üyeli yerel konsey kuruldu (opus, sonnet, fable). Kayıt yolu: oturumun scratchpad dizininde `council/20261115-1200-oyunlastirma-bilim/`.

Oy birliğiyle sıralama: opus 1., fable 2., sonnet 3. Ortak bulgular:
- Oyuncu bir senaryo oynamıyordu.
- İstasyon evresi yalnız bir zamanlayıcıydı.
- Gerçek alarm (PET 111,8 dk) ve hedef mesafeleri (374–1703 m) 15 dakikalık bir oyuna sığmıyordu.

Konsey yazılırken diğer ajan şunları ekledi: `redline_science`, `science_operations.py`, `campaign.py`, `campaign_controller.py`, `MissionCommand.srv` (D017) ve Unreal'da kampanya konsolu, numune etkileşimi ve habitat kapısı. Plan bu yüzden "var olanı tamamla" olarak yeniden kuruldu. Oyun katmanı ve Unreal onda kalır.

## Bu oturumun yaptıkları

1. **APXS hassasiyet modeli (D018).** Gerçek NASA tablosu indirildi, SHA pinle doğrulandı. Hata, süreyle √t'nin öngördüğünden çok daha yavaş küçülüyor ve sensör mesafesiyle büyüyor. Modül `redline_core.apxs_precision`, uydurma `redline_data.apxs`, betik `scripts/fetch_apxs_supplement.py`.
2. **Bölüm mesafesi.** `scripts/chapter_reach.py` gerçek ızgarada ölçtü. Kampanya hedefleri 16 m ve 31 m'de; orada kırmızı çizgi hiç bağlamıyor (FR-03 boşluğu 19 dk). Bağlaması için durak 280–454 m'de olmalı (T_ε 12–18 dk).
3. **C1 bölümü.** `config/scenarios/C1_SOL4190_CHAPTER.yaml`: 05:10 UTC çıkış, gerçek alarm PET 11,8 dk'da, ×1.
4. **Debrief notu.** `redline_core.debrief.grade`: güvenlik, bilim (bit) ve numune eksenleri; genel not güvenlik ile bilimin kötüsü. Eşikler SCENARIO.

Hepsi testlerle yazıldı; önce kırmızı koşuldu. Tek istisna `chapter_reach.py`: bir analiz betiği, kullandığı çekirdek fonksiyonlar zaten testli.

## Diğer ajana devir notu (öneri; onun dosyalarına dokunulmadı)

- **APXS gürültüsü.** `config/targets_BXW.yaml` şu an `noise_calibration: UNCALIBRATED_SCENARIO`. `ContactScience` (APXS / EV1_XRF) için σ şöyle alınabilir:
  ```python
  from redline_core.apxs_precision import ApxsPrecision
  model = ApxsPrecision.load("data/derived/instruments/apxs_precision_v1.json")
  sigma = model.sigma_wt(oxide, value_wt, integration_s, standoff_cm)
  ```
  `model.provenance()` ürünün provenance'ına girer. Bileşim yine SCENARIO kalır; yalnız gürültü DERIVED olur. 540 s altı integrasyon reddedilir; oyun 10 dk / 1 sa gibi seçenekler sunmalı.
- **Hedef mesafesi.** Kampanya durakları 280–454 m bandına alınırsa C1 alarmında çizgi oyuncunun etrafında daralır ve dönüş gerçekten yarışa dönüşür. Gerekçe ve sayılar `docs/verification/CHAPTER_REACH.json`'da.
- **Debrief.** `assessment` / `debrief` görevleri `grade()` çıktısını gösterebilir. Gereken girdiler: RuleViolation kayıtları, çalıştırma boyunca en küçük dönüş payı, ölçümlerin ürettiği posterior ve SampleRecord durumları. `science_value.posterior()` hâlâ hiçbir düğümden çağrılmıyor; ürün → inanç bağlantısı açık.
- **Zaman hızlandırma.** Konseyin önerisi şöyle: yalnız EV1 dururken ve bir alet çalışırken, ×20, ROS'ta korunan, her geçiş DecisionRecord'lu. Bu mission clock'a dokunur ve ayrı bir D kaydı ister; yapılmadı.

## Açık kalanlar

- S4/S4c gerçek koşusu, diğer ajan precursor kodunda çalıştığı için bekletildi.
- S2 giysi kaçağı bölümü.
- Canlı Unreal'da C1 kabulü.
- İngilizce altyazı ve kayıtlı koşudan oynatma yedeği (jüri için).

## S4 / S4c gerçek BXW koşusu (09:00)

Tam ROS kapısı: 109 test, sıfır hata (`ws-14684bfebfb9e670-zk8pu81c`). İki senaryo da bu derlemeyle, domain 86 / 9190 üzerinde koştu.

- **S4c (engelsiz koridor): kabul edildi.** Drone kanıtları geldi, karar "precursor: route clear, plan kept". Plan v1 korundu. Dört istasyon gezildi ve DEBRIEF'e ulaşıldı (PET 13 734 s). Kural ihlali yok; en dar pay 101,2 dk. Kanıt: `test-results/scn-bxw-20261115T055717Z-S4c_CLEAR_CORRIDOR-4/`.
- **S4 (engelli koridor): kabul edilmedi.** Drone 1420 gözlem üretti; cell_store hepsini işledi ve 1420 delta yayımladı. Ama diğer ajanın yeni kanıt kapısı 4 kimliği göremedi ("scout evidence not in cell-store snapshot"). Görev PRECURSOR'da güvenli biçimde bekledi ve saat başlamadı.
- **Sebep benim D015 tasarımım.** cell_store her gözlemden sonra bütün bilinen hücreleri `/redline/cells/known`'a yeniden yayımlıyordu; trafik gözlem sayısının karesiyle büyüdü. mission_manager her büyük mesajda bütün hücreleri dolaşırken geride kaldı; 50 derinlikli kuyruktan delta düştü. S4c'nin taraması daha küçüktü, sorun görülmedi.
- **Düzeltme.** Anlık görüntü en fazla 0,5 sn'de bir ve yalnız değişiklik varsa yayımlanacak; son görüntü her zaman tam. Delta yine gözlem başına bir. Önce test yazıldı (`test_cell_store.py`, 40 gözlemlik patlama). Kırmızı / yeşil ve S4'ün yeniden koşusu arka planda sürüyor.

## S2 kaçak zinciri ve WSL bellek olayı (09:10–09:20)

- **Kırmızı aşama (09:08).** Dört yeni test beklenen sebeple düştü: rule_monitor'de kaçak kaydı yok, `leak` alanı yok, cell_store'da 40 anlık görüntü (> 10), mission_manager'da DEBRIEF'e ulaşılamadı. Sonra üç yama uygulandı:
  - rule_monitor: telemetriden SUIT_LEAK tespiti; RuleViolation ve `/redline/alerts` uyarısı yayımlıyor.
  - mission_manager: SUIT_LEAK uyarısında CONTINGENCY'ye geçip bütün mürettebat için ReturnToShelter başlatıyor (BRIEFING ve PRECURSOR'da yok sayıyor). SEP yoluyla ortak `_send_return` kullanıyor.
  - cell_store: anlık görüntü hızı sınırlandı.
- **Yeşil aşama (09:10).** Tam kapı 115 test, sıfır hata (`ws-dc2376c9106aee04-9ar9njv0`).
- **Bellek olayı (09:10–09:15).** S2 koşusu başlarken WSL belleği tükendi (15,5 GB, yük ortalaması 266). OOM killer dbus'ı ve 3,4 GB'lık bir `ruby` sürecini (`gz sim`) öldürdü; ardından bütün kullanıcı süreçleri kapandı:
  - kullanıcının domain 87'deki EVA backend'i,
  - diğer ajanın kampanya ve iki Gazebo/Nav2 yığını,
  - bu oturumun sürücüsü.

  Yük birleşikti: diğer ajanın iki Gazebo yığını, bu oturumun paralel test kapısı ve senaryo başlatması. Başkasına ait hiçbir süreç yeniden başlatılmadı. S2 ve S4, yeniden derlenmeden aynı yeşil çalışma alanında tekrar koşuluyor.

## T7 S4 kabul edildi (10:05)

WSL yeniden başlatıldıktan sonra aynı yeşil derlemeyle S4 yeniden koşuldu. Rotada 16 engelli hücre bulundu, 1424 kanıt uygulandı ve plan v1'den v2'ye geçildi. Planlanan en dar pay 58,6 dk'dan 64,3 dk'ya çıktı; istasyon sırası T05 öne alınarak değişti. DEBRIEF'e ihlalsiz ulaşıldı. Ayrıntılar VERIFICATION_LOG'da.

## S2 ilk gerçek koşu: zincir çalıştı, simüle astronot eve dönmedi

`test-results/scn-bxw-20261115T065138Z-S2_SUIT_LEAK-2/` (`s2_acceptance_run1.json`):
- Kaçak PET 3000 s'de başladı. Telemetri oranı 1,000'dan 3,000'a çıktı.
- rule_monitor kaçağı 38,9 s sonra yakaladı. mission_manager PET 3051 s'de CONTINGENCY'ye ve hemen RETURN'e geçti.
- Tespitten sonraki 356 sınırlayan kaydın hepsi EV2/O₂. Bu, spesifikasyon §17'nin S2 ölçütü.
- Yayımlanan pay kayıtlı telemetriden yeniden hesaplandı. EV2'nin durduğu 253 örnekte fark en fazla 0,40 dk; bütün örneklerde ortanca 4×10⁻⁷ dk.
- **Ama FR-01 ihlal edildi:** EV2'nin payı −93,6 dk'ya indi. Sebep ev_sim'de: mission_manager CONTINGENCY'den RETURN'e milisaniyeler içinde geçti. ev_sim yalnız RETURN'ü gördü ve bunu planın son ayağı sandı. Simüle astronotlar istasyonları gezmeyi sürdürdü ve planın bitişinde (PET 13 749 s) eve girdi. Bu hata SEP için de vardı; S1'de mürettebat Unreal'dan yürüdüğü için görünmemişti.
- **Düzeltme:** aktif bir sığınak görevi olan RETURN da acil dönüş sayılıyor. Önce test yazıldı (`test_ev_sim_plan.py`). Kırmızı / yeşil ve S2'nin yeniden koşusu sürüyor.

## S2 kabul edildi (10:25)

ev_sim düzeltmesi önce kırmızı koşuldu (yeni test, astronot eve yaklaşmadığı için düştü), sonra yeşil oldu (116/116). S2 yeniden koşuldu:
- Kaçak 36,4 s'de yakalandı ve mürettebat eve döndü.
- Sınırlayan kayıtların hepsi EV2/O₂.
- Elle hesap telemetrinin sabit olduğu 297 örnekte en fazla 0,20 dk farkla tuttu.
- FR-01 korundu; en düşük pay +17,3 dk.

Kabul betiğinin "sabit örnek" tanımı iki kez sıkılaştırıldı: önce konumun, sonra O₂ hızının da değişmemesi istendi. Gerekçe: yürürken ve giriş anında, walkback_field'ın kullandığı CrewState kayıttan birebir eşlenemiyor. Bu bir modelleme farkı değil, ölçüm eşleştirmesi. İlk koşunun sonuçları da yeni tanımla yeniden hesaplandı.

## Bilim kampanyası, tablet atlası, yüzey v2 ve anlatım videoları (11:00–12:00)

- Kullanıcı yeni bir iş bölümü yaptı:
  - **ChatGPT:** shader, atmosfer, toz, kum, yürüyüş, ışınlanma, odalar ve tablet arayüzü.
  - **Bu oturum:** bilim görevleri ve yerleri, Mars yüzeyi, uzaktan haritalama, görev amaçları ve "nasıl çalışır" videoları.

  Shader işine başlamadan önce sorundu. Kullanıcı "shader işini GPT'ye bırak" dedi ve Unreal haritalarına ve malzemelerine dokunulmadı.
- Kampanya, atlas ve yüzey v2 ayrıntıları D020'de ve VERIFICATION_LOG'da.
- **Anlatım videoları** (`assets/production/explainer_videos.py`, Blender 5.2 EEVEE): matkap (B5), APXS (B1) ve LIBS (B2) için 1080p MP4, poster, TR/EN SRT ve açıklama JSON'u. Her video yaklaşık 4 dakikada çizildi.
  - APXS'teki ± değerleri D018 modelinden hesaplanıyor. LIBS'teki çizgiler NIST dalga boyları.
  - Kızılötesi lazerin görünmediği ve sayıların SCENARIO olduğu ekranda yazıyor.
- Deneme kareleriyle bulunan hatalar:
  - Matkap ucu kayaya değmiyordu; yüzey artık ışın atarak ölçülüyor.
  - Yazılar kadraj dışındaydı ve yakın çekimde kayanın arkasında kalıyordu; artık kameranın 15 cm önünde.
  - APXS kafası yanlamasına duruyordu.
  - Kayalar metal gibi parlıyordu.
  - LIBS'te dev bir kıvılcım vardı ve kamera yanlış hedefe bakıyordu.
- Tripo üretimi yapılmadı: `TRIPO_API_KEY` yok.
