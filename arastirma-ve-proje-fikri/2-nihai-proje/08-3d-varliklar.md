# 08 · 3D varlıklar

> REDLINE v3 nihai proje · Kılavuz bölümleri: §8 · [← 07](07-unreal-ve-ekranlar.md) · [← Nihai proje](README.md) · [09 →](09-kalite-test-ve-dogrulama.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 8. 3D varlıklar

| ID | Varlık | Kaynak | Hak / durum | Yapılacak iş |
|---|---|---|---|---|
| M01 | Curiosity rover (görsel) | [NASA-3D-Resources](https://github.com/nasa/NASA-3D-Resources) "Curiosity Rover (MSL)" [D] | NASA kredisi; sayfa koşulu kontrol edilir | Unreal'a ölçülü import, tekerlek ve direk pivotları |
| M02 | Curiosity rover (fizik) | [space-ros/demos](https://github.com/space-ros/demos) `curiosity_description`, `curiosity_gazebo` [D] | Kök Apache-2.0; alt model hakları ayrı [K]; ROS sürüm uyumu [?] | Jazzy/Harmonic'e taşı, ros2_control, sensörler |
| M03 | Perseverance (alternatif rover / Jezero) | [science.nasa.gov 3D](https://science.nasa.gov/3d-resources/mars-2020-perseverance-rover/) [D] | NASA/JPL kredisi | yalnız görsel |
| M04 | Ingenuity (drone görseli) | [science.nasa.gov 3D](https://science.nasa.gov/3d-resources/ingenuity-mars-helicopter/) [D] | NASA kredisi | Gazebo'da basit gövde + 4 rotor eşdeğeri (koaksiyel model yerine) |
| M05 | Drone fizik | Gazebo `MulticopterMotorModel` / `MulticopterVelocityControl` sistemleri; PX4 gz modelleri referans [D: PX4-gazebo-models deposu] | Apache/BSD [?] | Mars ρ ve g ile itki ölçekleme |
| M06 | Basınçlı rover / hareketli sığınak | NASA-3D-Resources "Space Exploration Vehicle" [D] | NASA kredisi | Unreal görseli; Gazebo'da basit kutu collision |
| M07 | Habitat dış/iç | NASA-3D-Resources "Habitat Demonstration Unit" [D]; Kenney Space Kit (CC0) [K]; kendi Blender kitimiz | NASA kredisi / CC0 / özgün | modüler kit, harita masası odası |
| M08 | Astronot | NASA-3D-Resources "Astronaut" [D] (DigitalSpace kaynaklı; hak belirsiz [K]); alternatif: kendi Blender giysisi + UE Mannequin rig + IK Retargeting | belirsiz / Epic lisansı | rig, Mars yürüyüşü, iki farklı renk (EV1/EV2) |
| M09 | Kaya ve zemin | Poly Haven (CC0) [K]; Megascans/Fab (lisans kısıtlı [K]) | CC0 tercih | instancing; görevi etkileyen kayalar manifestte |
| M10 | Görev nesneleri | kendi üretimimiz | özgün | numune kabı, alet arabası, sondaj, röle direği, istasyon bayrağı, vana paneli |
| M11 | Arazi | DEM + HiRISE ortho | NASA/USGS kamu malı + kredi | §6.5 hattı |

Üretim kuralı: metre ölçüsü, doğru pivot, collision proxy, LOD. Unreal'da bilinen bir kenar cm olarak ölçülür ve Gazebo pozuyla eşleştirilir. Ad önekleri: `SM_`, `SK_`, `M_`, `T_`, `BP_`, `WBP_`, `UCX_`. NASA logosu ve marka öğesi üretilen içerikte kullanılmaz.
