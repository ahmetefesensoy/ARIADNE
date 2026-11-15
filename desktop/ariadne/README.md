# Ariadne Windows önizlemesi

Kapak yaklaşık üç saniye görünür, ardından GitHub ZIP'inden alınan Ariadne
tanıtım sayfası açılır. Bu paket mevcut web tanıtımı/simülasyonunu içerir;
ROS/Gazebo veya Unreal oyununu içermez. Çevrimdışı harita verileri pakettedir;
dış kaynak bağlantıları ve web fontları internet isteyebilir.

Geliştirme: `npm ci`, `npm start`. Windows klasör paketi: `npm run package`.
`Ariadne.exe` yanındaki dosyalarla birlikte taşınmalıdır. Kaynak web paketi
GitHub `ahmetefesensoy/redline` deposundaki 15 Kasım ZIP'idir. Orijinal ZIP ve
önceki uygulama kaynakları değiştirilmedi. Eksik ana sayfa için paketteki son
tarihli `eski-surumler/index(1).html` kullanıldı; site yeniden tasarlanmadı.

Kayıt: `npm run record`. Yalnız bu uygulamanın 1280×720 içeriğini kaydeder.
Masaüstü/ses/mikrofon kaydetmez. Tanıtım kaydı kapaktan sonra başlar ve
`Uygulamayı aç` bağlantısına tıklanınca hedef sayfa kayda girmeden biter.
Normal açılışta bu bağlantı paketteki web simülasyonuna gider.

Kapak yerleşik Image Generation aracıyla üretildi, kurgu görselidir; NASA
arşiv fotoğrafı değildir. Prompt ve kaynak kaydı `assets/cover-source.json`.
