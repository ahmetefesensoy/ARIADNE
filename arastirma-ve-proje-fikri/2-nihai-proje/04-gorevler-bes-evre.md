# 04 · Görevler: tek EVA, beş evre

> REDLINE v3 nihai proje · Kılavuz bölümleri: §5 · [← 03](03-cekirdek-modeller-ve-teori.md) · [← Nihai proje](README.md) · [05 →](05-yazilim-mimarisi.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 5. Görevler: tek EVA kampanyası, beş evre

Beş görev ayrı demolar değil, aynı EVA'nın evreleridir. Her evre aynı harita kaydını (`campaign_id`, `target_id`) okur ve ona delta yazar.

### Evre 1 — Brifing ve Go/No-Go (eski "eğitim/sınav")
- **Amaç:** EVA'nın yapılıp yapılmayacağına karar vermek ve ekibi brifing etmek.
- **Kullanıcı:** habitat ekranında sahayı açar ve EVA penceresini seçer: REMS sıcaklık/basınç/UV, SPICE güneş açısı, DEM gölgesi. Bilim hedefini ve istasyonları seçer.
- **Sistem:** ilk EVA planını (PET timeline), sarı/kırmızı çizgileri ve cuff checklist'i üretir. Duyarlılık grafiğini gösterir.
- **Gerçek veri:** REMS seçilmiş sol, SPICE, DEM, CTX/HiRISE, SIM 3292, THEMIS, CRISM.
- **Simüle/senaryo:** giysi parametreleri, ekip sayısı, sarf kapasiteleri.
- **Çıktı:** `EVAPlan v1` ve `DecisionRecord` (neden bu pencere ve bu istasyonlar).
- **Prova modu (eski eğitim/sınav):** kullanıcı Unreal'da planı astronot gözünden prova eder. Sınav modunda gizli senaryo olayları (SEP, giysi kaçağı) devreye girer ve debrief'te karar kalitesi gösterilir.
- **Kabul:** plan bir kaynağa tıklanınca ürün kimliğini açar; varsayım değişince plan yeniden hesaplanır.

### Evre 2 — Robot öncü keşif (EVA'dan sol'ler önce)
- **Amaç:** EVA'dan önce en pahalı bilinmeyenleri çözmek.
- **Sistem:** bilgi değeri sıralamasıyla hücre seçer (§4.5). Drone `SurveyArea` görevini, rover `InspectTarget` görevini alır.
- **Gazebo:** rover (Curiosity modeli) Nav2 ile sürer. Drone Mars yoğunluğunda uçar. LiDAR/kamera alt-metre engeli bulur. Senaryo kayaları açıkça "senaryo" etiketlidir.
- **Gerçek veri karşılığı:** Navcam stereo türevleriyle "yörünge vs yer" farkı gösterilir: aynı yamada HiRISE DTM ile Navcam yan yana.
- **Çıktı:** hücre durumları `unobserved → detected/not_detected` olur, `EVAPlan v2` çıkar. Kırmızı çizgi değişir (genişler veya bir koridor kapanır).
- **Kabul:** her delta için "hangi kararı değiştirdi" kaydı var; kazanılan pay dakikası hesaplanır.

### Evre 3 — Traverse (iki astronot)
- **Amaç:** EV1/EV2'nin istasyonlara güvenli gidişi.
- **Unreal:** astronot gözünden yürüyüş; HUD'da yalnız kalan pay, sonraki istasyon ve dönüş yönü. Habitat ekranında IV operatörü (yerel uçuş kontrolü) iki astronotu ve rover'ı izler.
- **Gazebo:** astronotun kinematik proxy'si rover algısına dinamik engel olarak girer. Rover alet arabası ve röle olarak eşlik eder.
- **POV:** istasyona yaklaşınca gerçek Navcam karesi ile aynı CAHV pozundan Unreal render yan yana swipe ile gösterilir.
- **Çıktı:** gerçekleşen süre ve plan farkı. Fark marj modeline geri beslenir.

### Evre 4 — İstasyon bilimi (eski "numune/laboratuvar" ve "sondaj")
- **Amaç:** bilim planını uygulamak ve numuneyi doğru kayıtla almak.
- **Akış:** istasyon kartı (gerçek APXS/CheMin karşılaştırması, hata çubuklu, "preliminary" işaretli) → bağlam fotoğrafı → numune alımı ya da sondaj (rover kolu veya astronot aleti) → kap ve `SampleRecord`.
- **Kayıt:** köken konumu ile analiz konumu ayrı alanlardır. "Analiz sırasında rover burada" ile "numune burada" iki ayrı simgedir.
- **Gerçek veri:** APXS, CheMin, ChemCam/DAN (boxwork için Release 42, sol 4843'e kadar [K]).
- **Simüle:** yeni numunenin analiz sonucu senaryo olarak etiketlenir. Gerçek NASA ölçümüyle aynı kartta ayrı satırda durur. pH/iletkenlik gibi Gale'de ölçülmemiş büyüklükler "model" etiketiyle ikincil kalır.
- **Kabul:** numune kaydı tam (köken, işlem, kap, zaman); sonuç sonraki istasyonu ya da bir sonraki EVA'yı değiştirebilir.

### Evre 5 — Dönüş ve acil durum (eski "vana/kaçak müdahalesi")
- **Kriz A: SEP.** Sol 4190 replay'i ile alarm gelir. Uçuş kuralı devreye girer ve kırmızı çizgi daralır. Rover sığınağa doğru yaklaşır, isokron yeniden hesaplanır.
- **Kriz B: giysi kaçağı.** Eski vana görevi buraya dönüşür. EV2'nin sarf tüketimi artar, sınırlayan sarf değişir ve çizgi EV2'ye göre daralır. Rover sarf takviye noktası olabilir (varsayım). Habitat tarafında vana/servis hattı müdahalesi isteğe bağlı alt görev olarak kalır: ArUco ile kimlik, kol ile müdahale.
- **Çıktı:** debrief'te zaman çizelgesi replay'i, karar noktaları ve "hangi veri hangi kararı değiştirdi" tablosu.

### Doğrulama hattı (görevlerle paralel)
- **V1 — YKB tutarlılık kontrolü.** Yalnız yörünge katmanlarıyla hedef ve rota önerilir. Sonuç Curiosity'nin gerçek izi ve bulgularıyla karşılaştırılır. Karne: termal atalet → pekişmiş kayaç: isabet; HiRISE → kırıklı açık tonlu birim: isabet; CRISM → kil: kaçırma (toz örtüsü; CheMin ~%20 smektit [K]). Sunumdaki cümle: "Haritamız kili göremezdi ve bunu biliyordu."
- **V2 — Boxwork zaman bölmeli test (asıl kanıt).** Karar kuralı ve maliyet fonksiyonu önceden commit'lenip dondurulur. Yalnız sol 4533 öncesi arşivle plan yapılır. Sonuç sol 4534–4805 gerçek bulgularıyla karşılaştırılır. Geriye bakış yanlılığına karşı en güçlü cevap budur.
- **V3 — Monte Carlo duyarlılık.** Simüle dünyalarda "yalnız yörünge" ile "yörünge + robot" karşılaştırılır. Metrikler: rotadaki bilinmeyen oranı, tespit edilen engel, süre, dönüş payı, sığınak süresi. Hepsi "simüle dünyalar" etiketiyle sunulur.
