# AI katkı kaydı

14 Kasım 2026 · Araştırma yayını.

Önceki pakette AI destekli tasarım ve konsey çıktıları bulunur; kaynak ve hash kayıtları `research/notes/council-v3-source/SOURCE.json` ve `research/handoff/HANDOFF_MANIFEST.json` içinde korunur.

Bu depodaki aktarım, ortam kontrol komutları, doğrulama/ilerleme notları ve Research dizini OpenAI Codex yardımıyla hazırlandı. Nihai plan `docs/proje.md` olarak taşındı; yalnız belge bağlantıları düzenlendi, tasarım kararları değiştirilmedi. Tasarım belgeleri çalışan uygulama olarak sunulmaz.

T0 uygulamasında iki Python paketinin temeli, frame/saat sözleşmeleri ve testleri, ROS §5 arayüz tanımları ve generated-types testleri, build/test script'leri ve GitHub Actions CI OpenAI Codex ve alt ajanları yardımıyla sıfırdan yazıldı. Yerel sonuçlar [T0 kaydında](verification/T0_LOCAL_2026-11-14.json) gösterilir. Bu yardım NASA ölçüm verisi veya çalışan Unreal/Gazebo görev sistemi üretildiği anlamına gelmez.

14 Kasım 2026, 13:20 (+03:00): T1 katalog/fetch/CRS/ENU/derive/QA kodu, birim ve entegrasyon testleri, GIS bootstrap ve çalışma raporları Codex yardımıyla yazıldı. Alt ajanlar katalog, kaynak metadata incelemesi, testler ve dizi türevleri üzerinde çalıştı; nihai ENU/CLI/QA entegrasyonu ve yerel kabul kontrolleri ana ajan tarafından tamamlandı. Gerçek NASA/USGS kaynak piksellerinden DERIVED katmanlar üretildi. `redline-space-apps`, `geomaster`, `planetary-geologist` ve `scientific-visualization` yöntem rehberleri kullanıldı; Scientific Agent Skills atfı [DATA_SOURCES.md](DATA_SOURCES.md) içinde.

14 Kasım 2026, 13:44 (+03:00): Codex/alt ajan yardımıyla ürün-özel düşey metadata doğrulaması, sınırlı IMG/ARD piksel deneyi, iki DTM göreli kayıt/fark kodu ve testleri, STAC yazıcı/çevrimdışı resmi şema doğrulayıcı, T1 runner ve sekiz kapılı kabul raporu tamamlandı. 299 test geçti. Teknik kaynaklar ve Scientific Agent Skills atfı veri kaynaklarında saklanır. Kullanıcının Claude/Tripo üretimi için iki motoru kapsayan 3D brifi yazıldı; varlık üretilmedi.

Kaynaklı NASA/USGS kayıtları ile AI destekli yorumlar ayrı değerlendirilmelidir. Yeni NASA ölçümü üretilmedi; türev veri/test sonuçlarının sınırları doğrulama günlüğündedir. Tripo ile daha önce üretilen astronot bu çalışmaya dahil değildir. Bu T1 adımında AI görsel/video/3D üretimi veya ücretli model çağrısı yapılmadı. Kullanıcının son yönlendirmesinden sonra yeni kod GitHub'a gönderilmedi.

14 Kasım 2026, 14:37 (+03:00): T2 çekirdeği (`redline_core` yürüyüş maliyeti, dönüş alanı, pay/çizgi, radyasyon, kaya, SEP, sığınak, PET ve parametre modülleri; testleri; SCENARIO `config/crew.yaml` ve `config/suit.yaml`; `t2_margin_map.py` ve `bench_walkback.py`; ilgili belge güncellemeleri) Anthropic Claude Code yardımıyla yazıldı. Beklenen test değerleri spek formüllerinden üretim kodundan bağımsız olarak hesaplandı. BXW margin haritası gerçek T1 DERIVED arazisi ve SCENARIO parametreleriyle üretildi; plan değildir. Aynı oturumda, kullanıcının isteği ve API anahtarıyla Tripo text-to-model'den bir `scout_1` drone denemesi üretildi (görev `f91d9e38-645a-42e6-8287-a9d2266658fd`, 20 kredi). Dosya `assets/incoming/scout_1/` altında yereldedir, depoya alınmadı ve oyun/simülasyona hazır sayılmaz. Anahtar depoya yazılmadı.

14 Kasım 2026 — 3D varlık hazırlığı: kullanıcının açık isteğiyle Codex, bağlı Tripo API/CLI üzerinden 305 kredilik üretim/rig/animasyon/segmentation işlemlerini yürüttü. Önceki astronot ve drone kaynakları korundu; astronot rig/idle/walk, drone parça türevleri, istasyon ve beş bilim aracı işlendi. Tripo rover adayı teker düzeni nedeniyle seçilmedi. NASA ve Poly Haven hazır kaynaklarından görsel türevler, Blender master/LOD/export, EV1/EV2 kaplamaları ve yerel QA kayıtları Codex’in yazdığı asset hazırlama script’leriyle üretildi. NASA ölçümü veya robot fizik/kontrol sistemi üretilmedi. [Teslim](3D_ASSET_DELIVERY.md), [görev/prompt/harcama](../assets/CREDIT_LEDGER.json), varlık başına SOURCE.md/asset.json. Bu paragraf yalnız 3D oturumunu açıklar; yukarıdaki T1’de üretim yapılmadığına ilişkin kayıtlar kendi aşamalarına aittir.

14 Kasım 2026 — 3D ek paketler (Claude Code):
- 11 nesnenin geometrisi `assets/production/procedural_assets.py` ile prosedürel olarak üretildi; üretken model kullanılmadı.
- ArUco ve pist dokuları OpenCV ile üretildi.
- 4 taş Poly Haven CC0'dan alındı.
- Sığınak dokusundaki NASA/bayrak öğeleri OpenCV inpaint ile temizlendi.
- Taşıma kutusu yeniden renklendirildi, astronot master'ı döndürüldü.
- Bu adımlarda Tripo veya başka ücretli AI üretimi kullanılmadı.

14 Kasım 2026, 17:10 (+03:00) — T5 ROS ipliği (Claude Code): `redline_core` T5 modülleri (`fieldtile`, `planning`, `cells`, `suit_state`, `mission_clock`, `field_model`, `polyline`) ve testleri; `redline_env`, `redline_crew`, `redline_mission`, `redline_planner` ROS paketleri ve düğüm testleri; `config/eva.yaml` (SCENARIO); T5 derleme/koşu/özet betikleri ve belge güncellemeleri Anthropic Claude Code yardımıyla yazıldı. BXW koşusundaki EV1 yürüyüşü Unreal yerine geçen SIMULATED test hareketidir; görsel, model veya AI üretimi içerik oluşturulmadı.

14 Kasım 2026, 21:18 (+03:00) — REDLINE ses üretimi: kullanıcının açık yönlendirmesi ve ücretli çağrı onayından sonra Beatra Music Generation Studio üzerinden Suno 6 ile bir enstrümantal müzik görevi çalıştırıldı (`task_mcp_17065155b553b94635083e6cc7bfafea8c33225d`, net 360 Beatra kredisi). Belirli bir kayıt yüklenmedi; genel yaratıcı yön eski Sovyet uzay çağı film müziğini çağrıştıran minör/modal orkestrasyon, kontrollü epiklik ve kozmik yalnızlıktı. İki MP3 üretildi. Kullanıcı 22:13'te ikisini de farklı görev bölümleri için seçti; take 01 keşif/bilim, take 02 kriz/dönüş yatağı olarak UE 5.8.4 `SoundWave` varlıklarına aktarıldı. Döngü dikişi doğrulanmadığı için looping kapalıdır; asistan tarafında bağımsız işitsel miks incelemesi tamamlanmış sayılmaz. Prompt, artifact kimlikleri, süreler, hash'ler, Unreal yolları ve kullanım sınırları [`assets/audio/incoming/redline_sessiz_yorunge/`](../assets/audio/incoming/redline_sessiz_yorunge/SOURCE.md) altında kayıtlıdır.

14 Kasım 2026, 21:50 (+03:00) — T2 v2 kararları, plan çekirdeği ve T6 SEP hattı (Claude Code):
- σ topluluğu, hıza bağlı giysi maliyeti, tasarım noktası kapasiteleri, habitat seçimi, `science_value`, `orienteering`, `targets`, `voi`, `eva_plan`, `scenario`, `rules` ve testleri Anthropic Claude Code yardımıyla yazıldı.
- ROS düğümleri de aynı şekilde yazıldı: `planner_server`, `rad_replay`, `scenario_player`, `mission_manager`, `rule_monitor` ve paket `redline_safety`; ayrıca RAD ayrıştırıcısı ile BXW/S1 betikleri.
- Kaynak değerleri (EWT/IST, Apollo PLSS, MSL iniş limitleri, HiRISE görüntü geometrisi) NASA/USGS/UArizona belgelerinden alındı ve D010–D012'de atıflandı.
- RAD değerleri NASA ölçümüdür, AI tarafından üretilmedi. Görsel veya model üretimi yapılmadı.

14 Kasım 2026, 22:45 (+03:00) — T6 ortam durumu ve FR-12 (Claude Code):
- `spice_env`, `solar`, `env_server`, gün ışığı payı, `place_habitat`, `Fr12Tracker`, `rule_monitor` FR-12/FR-01 değişiklikleri, betik güncellemeleri ve testleri Anthropic Claude Code yardımıyla yazıldı.
- Güneş geometrisi NASA/NAIF SPICE çekirdeklerinden hesaplandı (DERIVED); doğrulama NASA RAD zaman damgalarına karşı yapıldı. Görsel, ses veya model üretimi yapılmadı.

15 Kasım 2026, 03:30 (+03:00) — Anlatı ve iç mekânlar (Codex): Kullanıcının
isteğiyle Tripo'da yedi yeni görsel paket üretildi: plakçalar, mürettebat modülü,
kurgu iniş aracı, airlock, komuta merkezi, laboratuvar ve koridor. Toplam 245
Tripo kredisi; kalan bakiye 380 doğrulandı. Ham dosyalar korunur, ölçek/kapı
geçitleri ve çarpışma türevleri açıkça SCENARIO'dur. Mevcut NASA veri katmanları
üretken görsellerle değiştirilmedi. Üretim görevleri ve hash kayıtları
`assets/narrative/prologue_v1/*manifest.json` ve türev manifestlerindedir.

Chatterbox Multilingual V3 ile RTX 5080 üzerinde dokuz Türkçe anlatım klibi
üretildi; varsayılan kurgu ses koşulu kullanıldı, kişi/sanatçı referans kaydı
yüklenmedi ve ücretli ses servisi kullanılmadı. Kod/model MIT kaydı, sürüm ve
bağımlılıklar `chatterbox/runtime/` altındadır. Doğallık/oyunculuk için işitsel
onay verilmedi. Mevcut gövde rig'inde yüz blendshape'i yoktur; mimik hazır değildir.
Chet Baker kılıfı/etiketi özgün kod çizimidir; resmî albüm kapağı veya fotoğraf
kopyalanmadı. Çalan yerel caz taslağı özgündür ve Chet Baker kaydı içermez.

- 2026-11-15: Oyunlaştırma planı için Claude Code yerel bir "LLM council" çalıştırdı. Üç Claude alt ajanı bağımsız cevap verdi, cevaplar anonim olarak birbirine puanlatıldı, ana oturum başkan olarak sentezledi. APXS modeli, bölüm mesafesi analizi, C1 senaryosu ve debrief modülü Claude Code tarafından testlerle yazıldı. Sayılar gerçek NASA verisinden ve depodaki ızgaradan yeniden hesaplandı.
- 2026-11-15: Claude Code bilim kampanyası yapılandırmasını, tablet uzaktan haritalama atlasını, 2,75 km'lik 1 m yüzey dışa aktarımını ve Blender "nasıl çalışır" anlatım videolarını (matkap, APXS, LIBS) üretti. Videolar projenin kendi 3D paketlerini kullanır. Ekrandaki sayılar ya SCENARIO hikâyesidir ya da etiketli olarak arşivden türetilmiştir (APXS hatası D018, NIST çizgi dalga boyları).
