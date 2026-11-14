# Geliştirme: T0

Esas uygulama belgesi [proje.md](proje.md). Fikir/gelişim belgeleri [research/](../research/README.md), çalışma günlüğü [journal/](../journal/README.md) altında. Görsel tasarım, Unreal sahne içeriği ve 3D varlıklar kullanıcıyla birlikte hazırlanacak.

## WSL / Ubuntu 24.04

ROS Jazzy ve Python 3.12 ortamında repo kökünden:

```bash
bash scripts/bootstrap.sh
bash scripts/test.sh
```

Windows PowerShell'den, bu klasörde:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd "/mnt/c/Users/USER/Desktop/SPACE APPS BASKETBEYBİ" && bash scripts/bootstrap.sh && bash scripts/test.sh'
```

Bootstrap sistem Python'unu değiştirmez; Linux kullanıcı önbelleğinde bu checkout'a özel venv oluşturur. Bağımlılıklar `scripts/requirements-test.txt` içinde sabittir. Saf Python testleri ROS'un `PYTHONPATH` ve pytest eklentilerinden ayrıdır. Colcon, Jazzy'nin `/usr/bin/python3` yorumlayıcısını kullanır. Aktif bir venv veya çelişen ROS dağıtımı varsa script durur.

## Türkçe/boşluk içeren Windows yollarında ROS derlemesi

Yerel Jazzy `rosidl` üreticisi bu checkout yolundaki `İ` karakterini keserek configure hatası verdi. `scripts/test.sh`, `ros_ws/src` içeriğini WSL'de kısa ASCII yollu **yeni bir çalışma alanına** kopyalar; kaynak ve kopyanın tüm SHA256 değerlerini karşılaştırır. Eski ROS overlay/build kullanılmaz ve sistem ROS dosyaları yamalanmaz.

Her koşunun kanıtları `test-results/run-*/` altında saklanır:

- `python.xml`: saf Python testleri.
- `ros-workspace.json`: gerçek build yolu, kaynak ağaç hash'i ve dosya hash'leri.
- `ros/build/.../test_results/`: üretilmiş arayüzlerin test raporu.
- `ros/log/`: ilgili build/test koşusunun günlükleri.

Bu dizin Git'e alınmaz; CI aynı raporları artifact olarak yükler. Hash'le doğrulanan Linux workspace yolu test çıktısında yazılır. Ardından ROS komutları kullanmak için yeni WSL shell'inde Jazzy underlay'i ve **o koşunun** `install/local_setup.bash` dosyasını source et. Repo içindeki eski başarısız `ros_ws/build` veya `install` dizini geçerli build değildir.

## Şimdilik çalışanlar

`redline_core`: metre/santimetre, Y ekseni ve quaternion sözleşmeleri; fizik/PET saat tipleri ve açık UTC replay eşlemesi. `redline_data`: kurulabilir CLI temeli; `--version` çalışır, henüz uygulanmamış `fetch` gibi komutlar hata verir.

`redline_msgs`: 22 mesaj, 5 servis, 11 aksiyon; üretilmiş C/Python typesupport ve CDR serileştirmesi test edilir. Bu testler çalışan DDS topic'leri veya action server'ları olduğunu göstermez.

Henüz BXW verisi indirilmedi, bilim ölçümü üretilmedi, planner/ROS düğümü veya Unreal köprüsü yazılmadı. T1'de ürün kimliği/label/CRS doğrulamasıyla veri hattına geçilecek. `FieldTile` 16-bit nodata sözleşmesi ve tanımsız `CollectSample` adı gerçek üretici yazılmadan netleştirilmeli.
