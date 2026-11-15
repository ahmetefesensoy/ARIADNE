# T4 — Unreal köprüsü ve arazi kabulü

14 Kasım 2026. T4'ün §18 teknik kabulü tamamlandı:
[hash bağlı kabul kaydı](verification/T4_ACCEPTANCE.json).
Unreal 5.8.4'te gerçek game aktörü, canlı ROS pozunu doğru map konumunda
uyguladı. Bu kabul, son görsel tasarım veya bütün robot modeli kabulü değildir.

| Kontrol | Gözlenen sonuç |
|---|---|
| Fresh C++ proje ve Runtime plugin | Hash doğrulanmış ASCII workspace'te build exit 0. |
| Unreal Automation | 9 başarılı; hata/uyarı/atlanan 0. Rastgele 1.000 koordinat/quaternion roundtrip, eksen, TF composition, parser, saat/tazelik, reconnect, callback reentrancy, actor frame guard ve offline replay. |
| Gerçek arazi collision | 17 mesh / 3.003.000 üçgen; üç native line trace DEM'den 0,004715 / 0,022170 / 0,019497 m farklı. Sınır 0,10 m. |
| Canlı ROS → gerçek UE aktörü | Son kaynakla aynı fizik zaman damgasında 72 eşleşme; maksimum konum farkı 6,50e-11 m, quaternion açı farkı 1,52e-6 rad. |
| Kaydedilmiş akış → gerçek UE aktörü | Son kaynakla 65 eşleşme; maksimum konum farkı 6,26e-12 m, yön farkı 1,28e-6 rad. |
| Bridge adapter testleri | 3 Python transport/poz testi; izole domain84'te iki statik DDS yazıcısının tek snapshot'a birleşmesi, geç aboneye tam veri ve çelişkili parent reddi. |

Canlı son test, `t3-runtime-5RZwQquS` koşusundaki duran rover ve tam
Gazebo/Nav2 grafiğiyle yapıldı. T4 istemcisi ROS'a hız/hedef yayımlamadı; yalnız
subscribe/unsubscribe gönderdi. Bağımsız doğrulayıcı ROS `map→odom` ve
odom pozunu birleştirip aktörün **GetActorLocation/GetActorQuat** CSV'siyle
karşılaştırır. Konum filtresinin doğruluğu bu testin konusu değildir.

Çelişkili veya bozuk statik snapshot durumunda aktör, o bağlantı boyunca
poz uygulamayı durdurur. Sonradan ulaşan eski geçerli snapshot/durum kaydı
kilidi kaldırmaz. Yeni oturum yeni dönüşüm ister. Gerçek ROS adapter testi
geç abonenin geçersiz durumu aldığını, Unreal frame guard testi aktörün
donduğunu ve geçerli geçmişin kilidi açmadığını doğrular. Salt cache, `/tf`
veya `/tf_static` otoritesi değildir.

`ARedlineRoverActor` teknik bir küptür; collision, overlap ve physics kapalıdır.
Model, rig, malzeme veya ekran tasarımı üretilmedi. `Content/T4Fixtures`
yalnız mevcut türetilmiş arazi ve sunum aktörünü içeren teknik kabul haritasıdır.
Kaynaklar değişmeden FBX'ler her kabul koşusunda yeniden içe alındı. İlk
denemelerdeki eksik Python API, test dünyasının iki kez oluşturulması ve map
dosyasının eşzamanlı açılmasından doğan kilit hataları loglarda korunur.

## Çalıştırma

PowerShell 7'de:

```powershell
pwsh -File scripts/build-t4.ps1
```

ROS/Gazebo, T3'ün seçilen ASCII workspace'iyle ayrı başlatılır. O açıkken WSL:

```bash
bash scripts/t4_rosbridge.sh <T3-ASCII-workspace>
```

Bu komut rosbridge ve salt okunur static snapshot adapter'ını birlikte sahiplenir.
Varsayılan dinleme `127.0.0.1:9090`, ömür 600 saniyedir. Gerektiğinde ortamdan
`T4_ROSBRIDGE_ADDRESS=<o-anki-WSL-IP>` ve `T4_BRIDGE_MAX_SECONDS` seçilir.
Bu oturumda Windows→WSL localhost yönlendirmesi çalışmadı; yerel WSL IP'si
üzerinden bağlantı doğrulandı. Eski IP bir sonraki oturum için sabit yazılmaz.

Unreal projesi `unreal/Redline/Redline.uproject`tir. `DefaultGame.ini` adresi
ya da `-RedlineRosbridgeUrl=ws://<adres>:9090/` ile canlı kaynak seçilir.
`-RedlineFeed=<JSONL>` çevrimdışı tekrar açar; bu mod gerçek ROS komutu vermez.
`-RedlinePoseLog=<CSV>` gerçek aktör pozunu ölçüm için kaydeder.

## Bağlantıda çözülen iki gerçek fark

UE5.8 native LWS, kök URL yolunun başına slash ekleyip `//` isteği gönderdi;
Tornado varsayılan root handler'ı 404 döndürüyordu. Bridge, yalnız kök slash
eşleşmesini `url_path:=/+` ile kabul eder. Protokol veya yetki genişletilmedi.

Statik TF ayrı DDS yazıcılarından gelir: RSP sensör dönüşümleri ve localization
`map→odom`. rosbridge 2.7.1'in geç istemci transient replay yolu ilk yazıcı
örneğinden sonra geçici aboneliği bırakır. Birleşik snapshot adapter'ı tüm
gözlenen statik kenarları **`/redline/bridge/tf_static_snapshot`** üzerinde tek
kayıt yapar; kaynak frame/zaman damgalarını korur. `/tf` veya `/tf_static`
yayımlamaz; yeni fizik veya TF otoritesi değildir. Yeni simülasyon oturumunda
adapter yeniden başlatılır. Statik topic abonelikleri açık reliable +
transient_local QoS kullanır; ilk istemcinin volatile seçimle kayıt açması
önlenir. Parent/child çelişkisi varsa adapter yeni geçerli snapshot yayımlamaz.

Socket callback'leri game thread'e kopyalanır; weak UObject/generation kontrolü
eski bağlantı callback'lerini dışlar. Expired service kayıtları callback'ten önce
yerel listeye alınır; callback'in Disconnect çağırması sonraki kayıt üzerinde
assert yaratmaz. Servis yanıtı kabul bildirir; gerçek yürütme sonucu ROS görev
durumuna aittir. Fizik `/clock` ile mission/PET saati ayrıdır.

T4 teknik kabulü sonrası açık kalanlar: son rover mesh/rig sunumu, render edilmiş
görsel kabul, T5 overlay/EV1, T6 alarm akışı, paketleme ve performans kampanyası.
Git/GitHub işlemi veya ücretli model üretimi yapılmadı.
