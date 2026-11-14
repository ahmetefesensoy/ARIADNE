# 03 · Çekirdek modeller ve teorik modüller

> REDLINE v3 nihai proje · Kılavuz bölümleri: §4, §18 · [← 02](02-veri-ve-dunya-uretimi.md) · [← Nihai proje](README.md) · [04 →](04-gorevler-bes-evre.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 4. Çekirdek modeller

### 4.1 Güven katmanı → dakika cinsinden pay

Hücre şeması:

```
value, unit, product_id (LIDVID/STAC id), gsd_m, acq_time, processing_level,
sigma, sigma_source, state ∈ {detected | not_detected_limited | unobserved},
status ∈ {archive | derived | simulated | scenario}, decision_role
```

σ kaynakları:
- HiRISE DTM'ler arası fark. Bu "ampirik uyuşmazlık"tır, bağımsız hata değildir: ortak MOLA kontrolü var. Önce eşkayıt yapılır, sonuç tek σ değil dağılım olarak raporlanır.
- CTX `intersection_error`.
- DTM eğimi ile PLACES tilt farkı, rover tabanı ölçeğinde (~3 m).
- THEMIS ±%20.

Tespit sınırı: HiRISE 0,25 m/px'te "en az 3 piksel" kuralıyla yaklaşık 0,75–1 m altı kaya görünmez. Bu bir kural, ürün özelliği değil. Varsa HiRISE gölge tabanlı kaya bolluğu ürünü kullanılır (Golombek ve ark., MSL iniş elipsi [?]).

Marj zinciri: bilinmeyen hücre → yürüme hızı cezası ve süre belirsizlik bandı → dönüş süresi → kırmızı çizgi. Planlamacı "bu bilinmeyen bana kaç dakikaya mal oluyor?" sorusunun cevabını görür.

### 4.2 Kırmızı çizgi (operasyonel tanım)
- Çizgi EVA zaman çizelgesinden (PET) türetilir. Her zaman adımında erişilebilir bölge hesaplanır. İstasyonlar go/no-go karar noktalarıdır.
- Koşul: dönüş süresi × marj ≤ en kısıtlı sarfın kalanı. Sarflar: O₂, CO₂ tutma, soğutma suyu, batarya. Ekranda hangi sarfın sınırladığı yazar.
- İki çizgi: sarı = terminate (düzenli dönüşe başla), kırmızı = abort (hemen dön).
- EV1/EV2: çizgi durumu daha kötü olana göre çizilir. Biri yavaşlarsa (yaralanma veya giysi kaçağı) çizgi yeniden hesaplanır.
- Sığınak: habitat veya hareketli basınçlı rover. Rover yer değiştirdikçe isokron değişir.
- İletişim: DEM viewshed'den habitat/rover görüş hattı katmanı çıkar. Rover tepeye çıkınca gölgedeki istasyon iletişimli olur.

### 4.3 Giysi ve insan modeli (parametrik)
- Yapı SEXTANT (BASALT analog programı) planlayıcısına benzer: DEM + eğime bağlı metabolik maliyet + süre. Metabolik veri Apollo kökenlidir [K].
- BASALT bulgusu: gerçek traverse süresi tahminden uzun çıktı [K]. Bu, marj çarpanının kaynağıdır.
- Apollo verisi 1/6 g, Mars 3/8 g ve Mars giysisi için ölçüm yok. Hepsi kaydırıcı olur ve "Apollo/analog türevi varsayım" diye etiketlenir.
- **Duyarlılık grafiği (tornado):** "Kararı hangi varsayım değiştiriyor?" Jürinin "modeliniz uydurma mı" sorusunun cevabı budur.

### 4.4 SEP uçuş kuralı
- RAD replay düğümü doz hızını okur. Önceki pencereden arka plan hesaplanır; ≥%25 artışta alarm verilir.
- Alarm anında herkes için "sığınağa varış süresi" hesaplanır. Kuralı karşılamayan bölge kırmızıya döner ve EVA timeline'ı yeniden planlanır.
- Kümülatif doz çubuğu "rover konumunda ölçülen soğurulmuş doz" etiketini taşır. İnsan dozuna dönüşüm senaryo olarak etiketlenir.
- "Hangi dedektör, hangi eşik" ayarlanabilir parametredir (sol 242'de B alarm verir, E vermez).

### 4.5 Robot değeri (bilgi değeri)
- Aday gözlem: "bu hücreyi çözersem kırmızı çizgide kaç dakika pay kazanırım?"
- Drone ve rover "gözlenmedi / tespit sınırı altı" hücrelere gönderilir.
- Ölçüt: robot saati başına kazanılan pay dakikası.
- Bir kararı değiştirmeyen robot deltası ekranda öne çıkarılmaz, ama kayıtta durur.
- Drone uçuş zarfı REMS'ten türetilir: ρ = P / (R_CO₂·T), R_CO₂ ≈ 188,9 J/(kg·K). Örnek: 750 Pa ve 220 K için ρ ≈ 0,018 kg/m³. Sıcaklık ve basınç gerçek ölçüm, ρ türetilmiş. Gazebo'da itki katsayısı ρ ile ölçeklenir.

---

## 18. Teorik modüller (v0.3'ten taşınan çekirdek)

Ayrıntılı formüller ve kaynaklar: REDLINE_RESEARCH.md §5. Fikirler araştırmadır; kod yeni depoda yazılır. Aşağıdaki sayılar v0.3 kaba hesaplarıdır [K].

| Modül | Ne yapar | Ana yöntem | v3'teki yeri |
|---|---|---|---|
| **M1 İnsan hareketi ve sarf** | eğim ve araziye göre hız, O₂, su, batarya | Tobler hız eğrisi × Froude çarpanı (Mars ≈ 0,615); Pandolf + Minetti yönlü maliyet; NASA EWT 3/8 g kalibrasyonu; O₂ ≈ 0,256 g/sa/W; HR tabanlı Kalman ile "mürettebatın dijital ikizi" | §4.3 giysi modeli |
| **M2 Arazi ve kaya tehlikesi** | eğim σ, sırt bariyerleri, kaya riski | HiRISE DTM hassasiyeti (Kirk 2008); 2–5 m çok tabanlı eğim; şans kısıtı; gölgeden kaya tespiti; **Golombek–Rapp** dağılımıyla çözünürlük altı kayalar; Poisson karşılaşma riski Dijkstra'ya toplanır | §4.1, §16.1 adım 7 |
| **M3 Radyasyon (GCR) ve SEP modu** | araziden gökyüzü kapanmasıyla doz haritası; sığınağa süre | görünür gökyüzü faktörü F_α (ufuk küpünden), RAD açı bağımlılığı (α ≈ 1,18); Murray Buttes kontrolü; **dürüst sonuç:** GCR koruması küçük (6 sa EVA'da ~8–24 µSv), asıl güvenlik etkeni SEP | §4.4, §3.2 |
| **M4 Işık, termal, atmosfer** | gölge takvimi, düşük güneş riski | SPICE + ufuk küpü; MGCM/AmesCAP | §16.3 |
| **M5 Bilim değeri (Bayesçi)** | istasyonların beklenen bilgi kazancı | EIG, submodüler seçim; ölçüm gelince posterior güncellemesi | §5 evre 4, bilim masası |
| **M6 Planlama çekirdeği** | walkback alanı, kırmızı çizgi, Pareto rotaları | yönlü 16 komşulu graf; ters graf çok kaynaklı Dijkstra; risk düzeltmeli walkback; pay = min_j m_j / tüketim hızı (dakika); hızlı/güvenli/bilim rotaları; D* Lite | §4.2 |
| **M7 Durak seçimi** | zaman pencereli stokastik orienteering | MILP (HiGHS/OR-Tools), CVaR; canlıda ≤1 s sezgisel | §5 evre 1 |
| **M8 Rover hareketli sığınak** | rover istasyonlarını en kötü kurtarma süresini azaltacak biçimde seçmek | darboğaz dinamik programlama O(K·C²); p-merkez ailesi | §15.6 |
| **M9 Uçuş kuralları (biçimsel)** | FR-01…FR-15 kuralları | NASA FRET → Ogma → Copilot C99 izleyicileri ROS'ta; GSN güvence argümanı; Ogma çalışmazsa elle C++ izleyici | `redline_safety` |
| **M10 İletişim ve DTN** | yerel ağ görüş hattı, Mars–Dünya gecikmesi | DEM viewshed + kırınım cezası; ION/HDTN, SPICE'tan kontak planı; röle TGO/MRO/Odyssey (MAVEN 2025'te kayıp [K]); kavuşum ≈ 2 hafta sessizlik | `redline_comm`, §17.5 |
| **M11 GPS'siz konum** | astronot konumu ve kovaryansı | EKF (IMU, adım, UWB); **ufuk çizgisi eşleştirme** (kask kamerası ↔ ufuk küpü); güneş pusulası | §15.1 istisna, FR-09 |

Seçilmiş uçuş kuralları:
- **FR-01:** kalan O₂ ≥ walkback O₂ + rezerv
- **FR-03:** her noktada sığınağa süre ≤ T_SEP,max = 20 dk (varsayım)
- **FR-04:** SEP alarmında 30 s içinde sığınak modu
- **FR-05:** EV1–EV2 mesafesi ≤ 100 m ve görüş hattı var
- **FR-06:** bağlantı 300 s kopuk kalırsa dönüş modu
- **FR-09:** konum σ > 20 m ise yeniden lokalizasyon
- **FR-12:** gün batımından önce dönüş
- **FR-13:** kurtarma süresi sınırı

Parametreler senaryo varsayımıdır [K].
