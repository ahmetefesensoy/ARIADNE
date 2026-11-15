# EV1 ile oynanabilir başlangıç

15 Kasım 2026 · Teknik oynanış ve canlı harita; son arayüz tasarımı değildir.

Oyuncu EV1 astronotudur. Unreal insan hareketini yönetir; rover/drone fiziği ve
kontrolü ROS/Gazebo'da kalır. Robot öncü keşfi ve bilim görevleri bu başlangıca
sonraki taşlarda bağlanır. Park edilmiş bir modeli otonom robot kabul etmeyin.

## Açılış ve kontroller

Önce güncel T5 çalışma alanıyla WSL'de:

```bash
bash scripts/run-eva-client-backend.sh <dogrulanmis-T5-workspace> 1800
```

Betik güncel WSL adresini, port 9290'ı ve kanıt klasörünü yazar. ROS domain 87
üzerinde çalışır; roverın domain 77 / port 9090 akışına karışmaz. Backend EV1
pozunu üretmez: tek poz yayıncısı gerçek Unreal karakteridir.

Ardından Windows PowerShell'de:

```powershell
./scripts/start-t5-eva.ps1 -RosbridgeUrl ws://<guncel-WSL-IP>:9290/
```

WASD / oklar yürür, fare kamerayı çevirir, E etkileşir, TAB haritayı gösterir.
Pencereye odaklanın. Görev bağlantısı eskirse karakter durur; bağlantı geri
geldiğinde yeni girişle yürür. Hareket hızı çekirdeğin M1 tablosundan, hücre
çarpanı ROS QueryCell'den gelir; model Unreal'da yeniden yazılmadı.

## Başlangıç akışı

1. Habitat önündeki brifing alanında bilim sorusu ve dönüş payı okunur.
   Görev saati E onayına kadar sıfırda bekler.
2. E isteğini ROS kabul edince görev saati başlar ve yakındaki bağlam istasyonu
   işaretlenir. İstasyona yaklaşıp E ile bağlam incelemesi açılır.
3. Bir sonraki E, habitat dönüşünü ister. Brifing noktasına dönüp E ile giriş
   provası tamamlanır. ROS her geçiş için DecisionRecord yazar.

Bu **SCENARIO oryantasyonudur**. PRECURSOR robot keşfi, alet kullanımı, numune
alımı veya bilim ürünü tamamlanmış sayılmaz. İstasyon, NASA'nın ölçüm yaptığı
bir nokta değildir. Gerçek nominal EVA planının yerine geçmez. Ayrı Tripo
komuta, laboratuvar, koridor ve airlock iç mekânları önizlemeye eklenmiştir;
bütün oda–koridor–yüzey geçişlerinin kabulü açıktır.
[Güncel anlatı ve iç mekân durumu](NARRATIVE_PROLOGUE.md).

İlerleme `/redline/mission/state` üzerinden gelir. E yalnız
`/redline/mission/advance` (`std_srvs/srv/Trigger`) isteği yollar. Servis 2 s'den
eski/eksik EV1 konumunu, hedeften 4 m'den uzak etkileşimi ve uyumsuz evreyi
reddeder. SEP veya etkin sığınak aksiyonu oryantasyondan önceliklidir. Kabul
yanıtı, yürüyüş/aksiyon bitişi değildir. [D016](DECISIONS.md) sözleşmeyi kaydeder.

## Modeller ve düzeltilen hatalar

Mevcut astronotun 1,85 m modeli, özgün renk/normal/roughness/metallic/AO
dokuları ve idle/walk klipleri kullanılır. İçe aktarma önce iskeleti ve malzeme
bağlantılarını diske kaydetmiyordu; yeniden açılışta animasyon iskeletsiz,
malzeme boş kalıyordu. Bağımlılıklar artık açıkça kaydedilir ve ayrı süreçte
yeniden okunur. UE struct dizilerinin döngü kopyaları üzerinde değişiklik
yapma hatası da giderildi.

Animasyonun kök ölçeği 1, mesh bağlama ölçeği 102,7778 idi. Yalnız animasyon
kökü kendi mesh'inin bağlama ölçeğine çevrildi; kaynak FBX ve modeller
değişmedi. Ölçülen baş–ayak mesafesi: bağlama 151,84 cm; idle 151,95 cm;
walk 150,68 cm. Bu test, klip süresinin dolu olmasından daha güçlü bir kontroldür.
Animasyon yerinde oynar; karakteri CharacterMovement taşır. Diagnostic probe
süresi bittiğinde WASD'ı kilitleyen hata ve kısa tuşların kaçırılması düzeltildi.

Habitat, harita masası ve bilim istasyonu mevcut teslimlerden alınır. Boyutları
FBX importundan tekrar ölçülür. Dokulu astronotun okunması için yalnız bu EVA
sahnesinde sabit dolgu ışığının yönü değiştirildi; rover görünümü korunur.

## Kanıt ve kalan işler

[T5 kabul kaydı](verification/T5_ACCEPTANCE.json) derleme, 20 Unreal testi,
39 ROS testi, 14 yeni core testi ve canlı görüntü/poz kanıtlarını ayırır.
Canlı CUA görüntüsünde renkli kıyafet, istasyon hedefi, harita ve pay görüldü;
WASD hareketi ve değişen animasyon kemikleri runtime kaydında gözlendi.

T6 tamamlanmadı: RAD değer/alarm etiketi bağlı ve eski aktif alarm korunur;
fakat S1'in alarm ve alan daralmasının tam görsel kabulü, `WBP_SpaceWeather`
grafiği, `/env/state` güneş/ortam gösterimi, REMS ve arazi ufku açık. Bir önceki
S1 yakalaması `/redline/alerts` gelmediği için `passed:false` kaldı; bu kayıt
başarı olarak kullanılmaz. Metal parlaması sonraki görsel tur için bekler.

İçeriği yeniden hazırlama sırası: `prepare_eva_runtime.py` (WSL venv),
`t5_prepare_eva_scene.py` (UE Python), `t5_prepare_intro_content.py` (UE Python).
Son iki betik için `REDLINE_REPO` gerekir. Bu betikler mevcut T4/VisualShowcase
veri ve içeriğinin hazır olduğunu varsayar; sıfırdan veri indirici değildir.
