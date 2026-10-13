# Ulanzi BLE Işık — Home Assistant Entegrasyonu

Bu eklenti, **Ulanzi EC65** gibi Bluetooth ile kontrol edilen Ulanzi ışıklarını
Home Assistant'tan yönetmenizi sağlar:

- Işığı **açma / kapama**
- **Parlaklık** ayarı
- **Renk sıcaklığı** ayarı (sıcak sarı 2700 K'den soğuk beyaz 6500 K'ye kadar)
- Hazır **efektler**: Flaş, TV, Mum, Çakar 1, Çakar 2, Çakar 3

Işık, Home Assistant'ın çalıştığı cihazın (örneğin Raspberry Pi) kendi
Bluetooth'u ile kontrol edilir. Ek bir donanım gerekmez.

> **Bilmeniz gereken bir şey:** Bu ışık o anki durumunu (açık mı, kapalı mı)
> Home Assistant'a geri bildiremiyor. Bu yüzden Home Assistant ışığın durumunu
> **en son verdiğiniz komuta göre** gösterir. Işığı kendi düğmesinden açıp
> kapatırsanız Home Assistant'taki görünüm yanlış kalabilir; bir sonraki
> komutta düzelir. Aynı sebeple ekranda tek bir anahtar yerine ayrı
> "aç" ve "kapat" düğmeleri görürsünüz.

---

## Kuruluma başlamadan önce

1. Home Assistant'ta **Ayarlar → Cihazlar ve Hizmetler** sayfasını açın.
   Listede **Bluetooth** görünüyor olmalı. Raspberry Pi'de bu genellikle
   kendiliğinden eklenir. Görünmüyorsa sağ alttaki **Entegrasyon ekle**
   düğmesine basıp "Bluetooth" yazarak ekleyin.
2. Ulanzi ışığınızı **açın** ve Raspberry Pi'ye yakın bir yere koyun
   (aynı oda yeterli).
3. Işık başka bir uygulamaya (telefondaki Ulanzi uygulaması gibi) **bağlıysa
   o uygulamayı kapatın**. Bluetooth ışıklar aynı anda yalnızca tek bir
   cihazla konuşabilir.

---

## Yol 1: HACS ile kurulum (önerilen)

HACS, Home Assistant'a topluluk eklentileri kurmayı kolaylaştıran bir
"uygulama mağazası"dır. HACS kurulu değilse aşağıdaki **Yol 2**'ye geçin.

### 1. Adım — Dosyaları GitHub'a yükleyin

HACS eklentileri GitHub'dan indirir, bu yüzden önce bu klasörü GitHub'a
koymanız gerekir.

1. [github.com](https://github.com) adresinde ücretsiz bir hesap açın
   (varsa giriş yapın).
2. Sağ üstteki **+** işaretine, sonra **New repository**'ye tıklayın.
3. **Repository name** kutusuna `ulanzi_ble` yazın.
4. **Public** (herkese açık) seçili olsun. HACS gizli depoları göremez.
5. **Create repository** düğmesine basın.
6. Açılan sayfada **uploading an existing file** bağlantısına tıklayın.
7. Bilgisayarınızdaki bu klasörün **içindekileri** (`custom_components`
   klasörü, `hacs.json`, `README.md` ve diğerleri) sürükleyip sayfaya bırakın.
   Klasörün kendisini değil, içindekileri bırakın: `hacs.json` deponun en üst
   seviyesinde görünmeli.
8. Aşağıdaki **Commit changes** düğmesine basın.

İsteğe bağlı: `custom_components/ulanzi_ble/manifest.json` dosyasındaki
`KULLANICI_ADI` yazan iki yeri kendi GitHub kullanıcı adınızla
değiştirebilirsiniz. Değiştirmeseniz de eklenti çalışır.

### 2. Adım — Depoyu HACS'e ekleyin

1. Home Assistant'ta soldaki menüden **HACS**'i açın.
2. Sağ üstteki **⋮** (üç nokta) menüsünden **Custom repositories**
   (Özel depolar) seçeneğine tıklayın.
3. **Repository** kutusuna deponuzun adresini yapıştırın, örneğin:
   `https://github.com/KULLANICI_ADINIZ/ulanzi_ble`
4. **Type** (Tür) olarak **Integration**'ı seçin ve **Add**'e basın.
5. Pencereyi kapatın. HACS arama kutusuna **Ulanzi** yazın,
   **Ulanzi BLE Light**'a tıklayın ve sağ alttaki **Download** (İndir)
   düğmesine basın. Çıkan pencerede yine **Download**'a basın.

### 3. Adım — Home Assistant'ı yeniden başlatın

**Ayarlar → Sistem** sayfasında sağ üstteki güç simgesine tıklayın ve
**Home Assistant'ı yeniden başlat**'ı seçin. Birkaç dakika bekleyin.

Sonra aşağıdaki **"Işığı ekleme"** bölümüne geçin.

---

## Yol 2: HACS olmadan, klasörü elle kopyalama

1. Home Assistant'ın ayar klasörüne erişmeniz gerekir. En kolay yol, Home
   Assistant'ta **Ayarlar → Eklentiler** (Add-ons) bölümünden
   **File editor** veya **Samba share** eklentisini kurmaktır.
   - **Samba share** ile Home Assistant'ın klasörleri bilgisayarınızda ağ
     sürücüsü olarak görünür; dosyaları sürükle-bırak ile kopyalarsınız.
2. Ayar klasörünü (`config`) açın. Bu klasörde `configuration.yaml`
   dosyasını görürsünüz.
3. Orada `custom_components` adında bir klasör yoksa oluşturun.
4. Bu projedeki `custom_components/ulanzi_ble` klasörünü olduğu gibi, Home
   Assistant'taki `custom_components` klasörünün içine kopyalayın. Sonuç
   şöyle görünmeli:

   ```
   config/
   ├── configuration.yaml
   └── custom_components/
       └── ulanzi_ble/
           ├── __init__.py
           ├── manifest.json
           ├── light.py
           └── ...
   ```

5. Home Assistant'ı yeniden başlatın (**Ayarlar → Sistem** → sağ üstteki güç
   simgesi → **Home Assistant'ı yeniden başlat**).

---

## Işığı ekleme

### Otomatik (çoğu zaman bu yeterli)

Yeniden başlattıktan sonra, ışık açıksa Home Assistant onu kendiliğinden
bulur. **Ayarlar → Cihazlar ve Hizmetler** sayfasının üstünde
**"Bulundu"** başlığı altında ışığınızı görürsünüz. **Ekle**'ye ve ardından
**Gönder**'e basın. Bu kadar!

### Elle ekleme

Işık kendiliğinden görünmezse:

1. **Ayarlar → Cihazlar ve Hizmetler** sayfasında sağ alttaki
   **Entegrasyon ekle** düğmesine basın.
2. **Ulanzi BLE Light** yazıp seçin.
3. Yakındaki Ulanzi ışıkları listelenir; kendi ışığınızı seçin.
4. Liste boşsa bir adres kutusu açılır. Işığın Bluetooth adresini yazın,
   örneğin `5D:AA:9E:7B:9F:0B`. Işığın Bluetooth adını biliyorsanız (genellikle
   "Ulanzi" ile başlar) ikinci kutuya yazın. Bu, ışığın adresi değişirse
   onu yeniden bulmaya yarar.

Ekledikten sonra ışık, panelinizde normal bir lamba gibi görünür. Ona tıklayıp
parlaklığı, renk sıcaklığını ve efekti değiştirebilirsiniz.

---

## Sorun giderme

- **"Bluetooth menzilinde değil" hatası:** Işık kapalı, çok uzakta ya da
  başka bir cihaza (telefon gibi) bağlı olabilir. Işığı açın, yaklaştırın,
  telefondaki uygulamayı kapatın ve tekrar deneyin.
- **İlk komut biraz gecikiyor:** Normaldir. Home Assistant ışığa ilk komutta
  bağlanır, bağlantıyı bir dakika açık tutar, sonra kapatır. Bu bir dakika
  içindeki komutlar hemen uygulanır.
- **Efekt çalışırken parlaklığı değiştirdim, efekt durdu:** Normaldir.
  Parlaklık ya da renk değiştirmek ışığı normal moda döndürür. Efekti
  yeniden seçebilirsiniz.
- **Ayrıntılı kayıt görmek isterseniz:** **Ayarlar → Cihazlar ve Hizmetler →
  Ulanzi BLE Light** sayfasında **Hata ayıklama günlüğünü etkinleştir**'e
  basın, sorunu tekrarlayın, sonra aynı düğmeyle kapatın. İndirilen dosya
  ışığa gönderilen her komutu gösterir.

---

## Geliştiriciler için

- Protokol: [kevinlouie/lctl](https://github.com/kevinlouie/lctl) projesinden.
  Bayt dizileri `custom_components/ulanzi_ble/protocol.py` dosyasındadır.
- Birim testleri: `python3 -m unittest discover -s tests`
- Bluetooth erişimi Home Assistant'ın kendi Bluetooth bileşeni üzerinden
  yapılır. Bu yüzden ESPHome Bluetooth proxy ile de çalışır.
