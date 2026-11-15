# REDLINE — Sessiz Yörünge

14 Kasım 2026 · **AI üretimi sunum müziği — iki take de kullanıcı tarafından seçildi ve Unreal'a aktarıldı.**

## Kaynak ve üretim

- Sağlayıcı: Beatra Music Generation Studio
- Model: Suno 6 (`suno-6`)
- Görev: `task_mcp_17065155b553b94635083e6cc7bfafea8c33225d`
- Üretim türü: metinden enstrümantal müzik
- Referans ses: kullanılmadı
- Net kullanım: 360 Beatra kredisi
- Durum: iki take de farklı görev bölümlerinde kullanılmak üzere seçildi

Yaratıcı yön, REDLINE Mars EVA sahneleri için eski Sovyet uzay çağı film müziğini çağrıştıran genel bir dil olarak tanımlandı: minör/modal armoni, ağır yaylılar ve bakır üflemeliler, koro benzeri Mellotron, ölçülü trampet, analog bas, radyo dokusu, kontrollü epiklik ve hafif kozmik yalnızlık. Belirli bir eser, kayıt veya melodi referans olarak verilmedi ya da yüklenmedi.

## Adaylar

| Dosya | Süre | Boyut | Beatra artifact | SHA-256 |
|---|---:|---:|---|---|
| `redline_sessiz_yorunge_take_01.mp3` | 59,6 sn | 1.391.098 bayt | `artifact_01M7DMGTGQHKRPJX815H6BQ01F` | `17F5240A6B4F437982B5F87571D04C4B1CA69CF5D2D3CFF274881D7C867AE011` |
| `redline_sessiz_yorunge_take_02.mp3` | 62,4 sn | 1.449.826 bayt | `artifact_01M7DMGVX5VA87RR7B42KCPQQ9` | `7D1A5C7BBD172291099F17E3923B64121039504063AC1D6D02EF28FBAD3681EB` |

Yerel dosya boyutları Beatra görev çıktısıyla eşleşir ve iki dosyada da MP3/ID3 imzası doğrulandı. Bu ortamda `ffprobe` bulunmadığından süreler Beatra'nın tamamlanmış görev kaydından alınmıştır.

## REDLINE kullanımı

| Take | Unreal varlığı | Görev evreleri |
|---|---|---|
| 01 | `/Game/Audio/Music/SW_REDLINE_SessizYorunge_Exploration` | BRIEFING, PRECURSOR, TRAVERSE, STATION_SCIENCE, DEBRIEF |
| 02 | `/Game/Audio/Music/SW_REDLINE_SessizYorunge_Crisis` | CONTINGENCY, RETURN |

`URedlineMusicSubsystem`, `/redline/mission/state` fazını yalnız Unreal sunum katmanında müzik yatağına çevirir. ROS/Gazebo görev veya fizik yetkisini değiştirmez. Bölüm değişiminde 2,5 saniyelik eş-güç çapraz geçiş kullanılır; seviye `0,28`'dir. İçe aktarma UE 5.8.4'te MP3 → stereo `SoundWave` olarak gözlendi: 59,63 sn ve 62,41 sn. Kaynak eşlemesi ve ayarlar [`config/presentation-audio.yaml`](../../../../config/presentation-audio.yaml) içindedir.

`Redline.Music.RuntimePhaseRouting` otomasyonu, ses aygıtı açık gerçek game-type Unreal dünyasında bridge'e CONTINGENCY, RETURN ve DEBRIEF fazları verdi; sessize alınmış gerçek oynatma bileşeninde take 01 → take 02 → take 01 dizisini doğruladı. Rapor: [`test-results/redline-music-automation-v3/index.json`](../../../../test-results/redline-music-automation-v3/index.json).

## Kullanım sınırları

- Örnek-kusursuz döngü doğrulanmadı; bu nedenle Unreal varlıklarında looping kapalıdır. Parçalar görev bölümü başına tek geçiş olarak kullanılır.
- Kullanıcı iki take'i de seçti; asistanın bağımsız işitsel miks/konuşma-alarm maskeleme incelemesi tamamlanmış sayılmaz. `0,28` sunum başlangıç seviyesidir ve final sahne miksinde yeniden dinlenmelidir.
- Dağıtım ve yarışma tesliminden önce Beatra'nın güncel hizmet/kullanım koşulları ile etkinlik AI açıklama kuralları yeniden kontrol edilir.

