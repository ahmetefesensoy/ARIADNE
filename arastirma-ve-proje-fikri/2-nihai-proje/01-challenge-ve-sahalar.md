# 01 · Challenge uyumu ve sahalar

> REDLINE v3 nihai proje · Kılavuz bölümleri: §1, §2 · [← Nihai proje](README.md) · [02 →](02-veri-ve-dunya-uretimi.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 1. Challenge uyum matrisi

Alıntılar yerel organizatör kopyasından alındı [D]. Resmî sayfa SSL hatası verdi; teslimden önce resmî metinle karşılaştır.

| Challenge isteği | REDLINE karşılığı | Veri |
|---|---|---|
| "layered, integrated view of a location or route", "multiple NASA science missions" | İki saha, 7+ katman. Her katmanın bir karar rolü var | MRO (HiRISE, CTX, CRISM), Odyssey (THEMIS), MSL (RAD, REMS, APXS, CheMin, Navcam, PLACES), MGS (MOLA, DEM içinde) |
| "map, tool, or interface a Mars astronaut could use" | Habitat ekranı, tablet, HUD + dışa aktarılan EVA kartı | — |
| Bilim hedefi ve konum; örnek "boxwork formations" | Boxwork-Batı ileri EVA sahası, bilim sorusu, istasyonlar | MMGIS, HiRISE DTM, ChemCam/DAN |
| "may consider including at least three kinds of data" (öneri, zorunlu değil [D]) | optik, termal, spektral, topografik, kimyasal, radyasyon, atmosferik | §3 |
| "astronaut safety", "might include space weather data" | Kırmızı çizgi ve SEP uçuş kuralı | RAD sol 242 ve sol 4190 [D] |
| Giysi hareket kısıtı, büyük kayalardan kaçan rota | Parametrik giysi modeli, eğim/pürüzlülük, tespit sınırı altı kaya riski | DEM, DTM σ, PLACES tilt |
| Habitat ekranı / tablet / HUD | Üç biçim = üç operasyonel rol | — |
| "static snapshot, interactive product, or a tool that generates maps" | Manifest + pipeline başka sahaya harita üretir | STAC |
| Diğer dünyaların haritalanması (Earth, Moon) | Apollo traverse ve BASALT analog mirası; Jezero (ve isteğe bağlı Ay) manifest testi | — |
| Zaman çerçevesi (geçmiş / tahmin / zamansız) | Katman başına açık seçim; tarihsel sol replay | REMS, RAD |
| Yüzey görevlerinin POV görüntüleri | "Varınca ne göreceksin": Navcam karesi ile Unreal render yan yana | Navcam RDR, Perseverance Raw |
| Robotlarla mürettebat ve alet taşıma, çift astronot | Rover alet arabası, iletişim rölesi, hareketli sığınak; EV1/EV2 | DEM viewshed |
| "updates on current conditions" | Güncel durum paneli: her kaynağın son kaydı ve yaşı | MMGIS, REMS özeti, PDS sürümü |
| Resources (5 kaynak) | Beşi de işlevsel kullanılıyor (§3.3) | — |

Jüri ölçütleri (2025 rehberi; 2026 metni okunmadı [?]): Impact, Creativity, Validity, Relevance, Presentation.

---

## 2. Sahalar

| Saha | Rol | Konum | Neden |
|---|---|---|---|
| **Yellowknife Bay (YKB)** | Kalibrasyon ve tutarlılık kontrolü | John Klein, lat −4,5895, lon 137,449 [K] | NASA burayı 2012'de yörünge katmanlarıyla seçip yerde doğruladı (Grotzinger+2014 [K]). Sol 242 SEP olayı burada ölçüldü [D] |
| **Boxwork-Batı (Mount Sharp)** | İleri EVA sahası, yeni bilim planı | Curiosity kampanyası sol 4534–4805: lat −4,798…−4,809, lon 137,379–137,386 [D] | Challenge'ın kendi örneği. Sol 4190 SEP olayı yaklaşık 1,5 km uzakta ölçüldü [D] |
| Eski 2×2 km AOI | İsteğe bağlı "az çalışılmış saha" | lat −4,825…−4,791, lon 137,428–137,462 [K] | Boxwork kampanyasının yaklaşık 2,5–5 km doğusunda; PLACES'ta rover örneği yok. Challenge "an area that hasn't been studied as closely" seçeneğine izin veriyor |
| Jezero | İsteğe bağlı manifest testi | Trek JEZ katmanları [K] | "Harita üreten sistem" kanıtı. Perseverance'ta RAD benzeri dozimetre yok; ekranda "ölçüm yok" yazar |

Eski AOI YKB'den yaklaşık 13 km güneyde [D]. Eski kırpım YKB için kullanılamaz. Yeni depoda iki saha da sıfırdan kırpılır.

Bilim sorusu (boxwork-Batı): "Doğu kenarında görülen sırtta kil / çukurda karbonat deseni batı uzantısında da geçerli mi?" REDLINE bir sonuç iddia etmez. Bir **EVA bilim planı** üretir: hipotez, istasyon, cihaz ve beklenen ölçüm.
