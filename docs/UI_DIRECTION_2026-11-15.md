# Görev panosu: uçuş not defteri

15 Kasım 2026, 12:14 (+03:00). Kullanıcı mavi ekranların ve üretilmiş şablon
görünümünün kaldırılmasını istedi. Interface Design becerisi bu doğrultuda
uygulanıyor; web bileşenleri Unreal'a taşınmıyor, ilkeler mevcut Canvas'a uyarlanıyor.

Oyuncu, EVA öncesinde sonraki işi bulur; sahada nerede duracağını ve ne zaman
işlemi başlatacağını, döndüğünde hangi ürünün geldiğini görür. Ekran bir uzay
gemisi dekoru değil, eldivenle kullanılan bilim çalışma defteri gibi okunur.

Alan sözlüğü: dönüş payı, yürüyüş ayağı, numune zinciri, sayım, kanıt, görev
sırası. Renkler ortamdan gelir: grafit cihaz gövdesi, açık giysi kumaşı,
bazalt gölgesi, bakır Mars tozu, soluk yeşil kayıt göstergesi. Özel öğe,
etkin görevden varışa ve kayıtlı sonuca giden tek adımlı görev şerididir.
Görev listesi süs kartı ızgarası yerine okunabilir sıra; kaynaklar rakam
kutuları yerine alt bilgi; parlak mavi çerçeveler yerine boşluk ve sıcak
gri yüzey farkları kullanır.

Pano: ana odak görev başlığı ve tek işlem; sağda beş komşu adım, altta süre
ve dönüş payı. Palette `RedlineConsoleTheme.h` tek kaynaktır. 8 piksel temel
aralık, 40 piksel dış boşluk, yaklaşık 1,25 tipografik oran; başlık 2,8,
metin 1,55, ikincil etiket 1,1 Canvas ölçeği. Mevcut Roboto/Engine fontu
Türkçe karakter ve aynı çalışma ortamında tutarlı görünüm için korunur.
Derinlik yalnız yakın yüzey tonu farklarıyla verilir. Parlama, dekoratif
gradient, neon çizgi ve rastgele rozet eklenmez.

Veri durumları: bekleniyor, güncel, eski, işlem sürüyor, reddedildi, kayıtlı.
Renk daima metinle desteklenir. Varış görevi tamamlamaz; ROS sonucu/ürünü
gerekir. İnsan adımı mesafe kapısı, rover adımı uzaktan komut içerir.
Atlasın gelecekteki istasyon kartları çalışan kampanya adımları değildir.

Kaynak beceri: [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design),
MIT, commit `2f9be3206855bcb2d1d0af262c8bae25cba6658d`. Kurulum
`C:/Users/USER/.codex/skills/interface-design`; özgün LICENSE ve SOURCE.json
orada korunur. Bu kurulum yürütülebilir veya yeni servis bağlantısı kurmaz.
