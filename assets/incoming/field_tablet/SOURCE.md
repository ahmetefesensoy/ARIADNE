# REDLINE saha tableti — kaynak kaydı

15 Kasım 2026, 11:15 (+03:00)

Tablet, kullanıcının isteğiyle Tripo üzerinden üretilmiş bir **AI / SCENARIO**
görsel varlığıdır. Gerçek NASA donanımının modeli veya ölçüsü değildir.

| İşlem | Tripo görev kimliği | Kredi |
|---|---|---:|
| Metinden 3D üretim | `2ba0f9c0-286a-4899-8487-f1ca42345949` | 30 |
| FBX dönüşümü | `2563d68b-4a59-4236-9bfe-65aa8d0469e7` | 5 |

Toplam kullanım 35 kredidir; işlem sonrası kaydedilen bakiye 345 kredidir.

Özgün GLB korunur:
`tripo-out/realistic-rugged-handheld-eva-sc-2ba0f9c0/model.glb`.
SHA-256: `aa336f3358a301051f759f79ceccfae3f8ce69df485982d10ad3a160768b576c`.
Tripo'nun özgün FBX çıktısı bu klasördeki
`tripo/tripo-out/realistic-rugged-handheld-eva-sc-2-2563d68b/model.fbx`
dosyasıdır. Hazırlama işlemi bu özgün dosyaların üzerine yazmaz.

`scripts/prepare_tablet_asset.py` GLB eksenlerini düzenleyip tasarım ölçüsünü
**32 × 22 × 2 cm** olarak belirler. Hazırlanan ağ 79.999 üçgen ve bir UV
katmanı içerir. Özgün 4096 × 4096 renk dokusunun baytları korunmuştur.
Ayrıntılı dönüşüm matrisi ve dosya özetleri
[prepared/manifest.json](prepared/manifest.json) içindedir.

Unreal varlığı `/Game/Campaign/Tablet/SM_FieldTablet` olarak içe aktarılmıştır.
Ölçülen boyut 31,9967 × 21,9995 × 1,9977 cm'dir. İçe aktarma doğrulaması
`test-results/tablet-import.json` dosyasında başarılıdır; ölçü dönüşüm hatası
yaklaşık 0,00000143 cm'dir.

Kaldırma/indirme animasyonu Unreal koduyla, tutuş ise mevcut astronot
iskeletine uygulanan kol IK'sı ile yapılır. Tripo'dan rig veya karakter
animasyonu alınmamıştır. Canlı RViz görüntüsü ve bilim sayfaları Unreal
tarafından ayrı ekran yüzeyine çizilir; özgün model dokusunun parçası değildir.

Kullanım hakları kullanıcının Tripo hesabı ve ilgili hizmet koşullarına
bağlıdır; bu kayıtta bağımsız bir lisans doğrulaması yapılmamıştır. Varlık
CC0 veya kamu malı olarak işaretlenmez. Hesap bilgileri, erişim anahtarları
ve süreli indirme bağlantıları bu kayda eklenmemiştir.
