# REDLINE 3D varlık üretimi — 14 Kasım 2026

Kapsam: kullanıcının bu oturumda paylaştığı `3D_VARLIK_BRIFI.md` temelinde yerel varlık paketi. Bu istek, AGENTS.md içindeki önceki 3D bekletme kararını bu paket için kaldırır. Uygulama/ROS kodu, T1 verileri, Git/GitHub, sahne ve ekran tasarımı kapsam dışıdır.

Gerçekçi bilimsel Mars keşif dili; mevcut astronotun beyaz/grafit/kırmızı paleti başlangıç referansıdır. Bütün yeni nesneler SCENARIO görselidir. NASA kaynakları arşivdeki dijital görsellerdir; fiziksel ölçüm, sensör verisi veya doğrulanmış robot dinamiği sayılmaz. Taşların rengi/minerali Mars ölçümü olarak kullanılmaz.

| Varlık | İşlem | LOD0 hedefi / Gazebo üçgen hedefi | Doku | Ölçek ve hareket |
|---|---|---|---|---|
| astronaut | Mevcut Tripo görevini indir; rig-check, insan iskeleti, idle/walk | 60–100 bin / kapsül, isteğe bağlı ≤10 bin | 2K PBR | 1,85 m SCENARIO; taban root; deformasyon ayrıca kontrol |
| rover_1 | Tripo H3.1 parçalı geometri ve PBR kaplama | 80–150 bin / 15–35 bin | 2K PBR | 6 teker, direk ve 5 DOF kol; gerçek parça/pivot sayısı ölçülür |
| scout_1 | Mevcut Tripo GLB'yi koru; parçala ve sadeleştir | 30–60 bin / 5–15 bin | 2K PBR | 4 rotor; gövde ve rotor merkezleri; SCENARIO uçak |
| pr_1 | NASA Space Exploration Vehicle hazır GLB | 100–180 bin / 15–35 bin | Kaynak; azami 2K türev | Kaynaktaki teker yapısı korunur; fizik çıkarılmaz |
| habitat | NASA Habitat Demonstration Unit hazır GLB | 50–100 bin / 5–15 bin | Kaynak; azami 2K türev | İlk sürüm dış görünüş; giriş/kapı ayrı kontrol |
| science_station | Tripo H3.1 parçalı geometri ve PBR kaplama | 15–30 bin / 3–8 bin | 1K PBR | Ayrı ayak/anten; ilk kullanım sabit istasyon |
| science_tools | Uygun lisanslı hazır model ara; uygun olmayan yerine ayrı SCENARIO araçları | Araç başına 5–15 bin / 1–4 bin | 1K | APXS, LIBS, matkap, nötron kutusu, multispektral kamera |
| sample_kit | Uygun hazır model ara; tüp, kapak ve kutu ayrı | Parça başına 2–8 bin / 0,5–2 bin | 1K | Toplama kökeni ve analiz yeri bu görselden türetilmez |
| rocks | Poly Haven CC0, az sayıda kuru taş | 1–5 bin / 0,2–1 bin | 1K | Yerleşim üretilmez; yalnız varyant paketi |

Ortak master: metre, sağ elli +X ileri/+Y sol/+Z yukarı. Ölçek seçimleri ve kaynak dönüşümleri `asset.json` içinde saklanır. Unreal FBX ve Gazebo OBJ görseli ayrı çıkartılır. Kalibrasyon küpü bir metre; motor içi 100 cm/1 m kontrolü yapılmadan motor kabulü verilmez. Çarpışma geometrisi ayrı basit proxy'dir; kütle/inertia/limit/uçuş parametreleri üretilmez.

Etkin skill'ler: `redline-space-apps` (sözleşme/provenance), `blender-director` (üretim sırası), `asset-optimization` (bütçe/audit), `unreal-export` (ayrı export ve import sınırı). Blender MCP bağlı değil; Blender 5.2.3 LTS komut satırı mevcut. Skill'in ortak `../references` dosyaları kurulu kopyada yok; teslim kriterleri proje brifinden uygulanır.

İşlem sırası: kaynakları koru → Tripo üretim/rig/segmentation → geometri/doku incelemesi → parça ve ölçek kaydı → master/LOD/collision → FBX/OBJ → yerel yeniden içe aktarma ve ön/yan/arka önizleme → dosya hash'leri ve eksik kabul kontrolleri. Başarısız kaliteyi örtmek için ücretli yeniden üretim yapılmaz.

Başlangıç Tripo bakiyesi: 930 kredi, frozen 0. Önceden var olan astronot: `7583fea2-05ef-4340-8cc9-5b5a756d3eb4` (önceki 50 kredi); drone: `f91d9e38-645a-42e6-8287-a9d2266658fd` (önceki 20 kredi). Yeniden üretim yerine bu kaynaklar kullanılacak. H3.1 rover parçalı/detailed geometri tahmini 50, istasyon parçalı geometri tahmini 30 kredi; kaplama, rig ve segment ayrı ücretlidir. Tahmin canlı fiyat garantisi değildir; gerçek tüketim görev kaydından raporlanır.

Kabul durumu dosya başına kaydedilecek. Motor içi import, Nav2, robot kontrolü, iskeletin Unreal uyumu veya görevin uçtan uca çalışması yalnız dosya oluştu diye tamamlandı işaretlenmez.
