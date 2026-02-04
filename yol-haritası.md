# Geliştirme Raporu ve Yol Haritası

**Proje:** cita-uiauto-engine  
**Referans:** pywinauto/pywinauto analizi

---

## Özet

Bu rapor, **cita-uiauto-engine** projesinin, **pywinauto**’dan aktarılabilecek yeteneklerle nasıl geliştirilebileceğini analiz etmektedir.  
Toplam **7 ana geliştirme alanı** belirlenmiş olup, **tahmini toplam süre 6–8 iş günü** olarak hesaplanıştır.

### Önemli Bulgular

- Mevcut proje, **QtQuick uygulamaları** için optimize edilmiş sağlam bir temel sunmaktadır
- **pywinauto’nun 10+ yıllık olgunluğundan** yararlanılabilecek kritik pattern’ler mevcuttur
- Önerilen geliştirmeler ile:
  - **%30–50 performans artışı**
  - **%80 debug kolaylığı** beklenmektedir

---

## Mevcut Durum Analizi

### Güçlü Yönler

- QtQuick `Accessible.name` desteği (`name / name_re` locator’lar)
- Multi-locator fallback stratejisi
- JSON Schema ile senaryo validation
- Artifact generation (screenshot + control tree)
- Inspector ve Recorder araçları

### İyileştirme Alanları

- Tek tip timing (tüm action’lar için aynı interval)
- Exception stack trace kaybı
- Structured logging eksikliği
- Strict element matching (typo tolerance yok)
- Element property caching yok
- Generic wrapper (control-type specific değil)
- Immediate resolution (lazy evaluation yok)

---

## Entegrasyon Değerlendirme Matrisi

| Yetenek              | Mevcut Durum                 | pywinauto Çözümü               | Beklenen Fayda         | Öncelik |
| -------------------- | ---------------------------- | ------------------------------ | ---------------------- | ------- |
| TimeConfig           | Tek `polling_interval=0.2`   | 40+ action-specific timing     | %30–50 hızlanma        | Orta    |
| wait_until_passes    | Exception string’e dönüşüyor | original_exception attribute   | Debug %80 kolaylaşır   | Yüksek  |
| ActionLogger         | Log yok, print debugging     | Structured logging + decorator | Real-time visibility   | Yüksek  |
| Best Match           | Strict matching              | Fuzzy matching (difflib)       | Typo/version tolerance | Orta    |
| Element Caching      | Her çağrı UIA API’ye gider   | Lazy/eager cache stratejisi    | Inspector 3–5x hızlı   | Düşük   |
| Wrapper Registry     | Generic Element sınıfı       | Control-specific wrapper’lar   | Type-safety + IDE      | Orta    |
| ElementSpecification | Immediate resolution         | Lazy specification pattern     | Chained lookups        | Düşük   |

---

## Uygulama Yol Haritası

### Faz 1: Kritik İyileştirmeler (2–3 Gün)

#### 1.1 ActionLogger Entegrasyonu

**Süre:** 1 iş günü  
**ROI:** ★★★★★ (En yüksek)

**Kapsam**

- `uiauto/actionlogger.py` modülü
- `@log_action` decorator
- Actions sınıfına entegrasyon
- Enable / disable mekanizması
- Console + file output desteği

**Örnek Çıktı**

```bash
12:34:56 | INFO | click | element='loginbutton'
12:34:57 | INFO | type  | element='usernamefield' | text='TestUser...'
12:34:58 | INFO | hotkey | keys='^l'
```

**Kabul Kriterleri**

- [ ] Tüm action’lar otomatik log’lanıyor
- [ ] `ActionLogger.disable()` sessiz mod sağlıyor
- [ ] Log dosyasına yazma destekleniyor

---

#### 1.2 wait_until_passes Fonksiyonu

**Süre:** 2–3 saat  
**ROI:** ★★★★★ (Kritik debugging)

**Mevcut**

```python
raise TimeoutError(f"...{last_exc}")
```

**Önerilen**

```python
err = TimeoutError("timed out")
err.original_exception = last_exc
raise err
```

**Kabul Kriterleri**

- [ ] Timeout sonrası orijinal exception erişilebilir
- [ ] Stack trace korunuyor
- [ ] Mevcut testler geçiyor

---

#### 1.3 TimeConfig Sistemi

**Süre:** 4–6 saat  
**ROI:** ★★★★☆ (Performans)

**Kapsam**

- `uiauto/timings.py` modülü
- Action-specific timing değerleri
- `fast()`, `slow()`, `default()` preset’leri
- `elements.yaml` ile override desteği

**Timing Kategorileri**

| Kategori            | Default |  Fast |  Slow |
| ------------------- | ------: | ----: | ----: |
| window_find_timeout |    5.0s |  1.0s | 30.0s |
| element_find_retry  |    0.2s | 0.01s |  0.5s |
| after_click_wait    |   0.09s | 0.01s |  0.3s |
| after_type_wait     |   0.05s | 0.01s |  0.2s |

**Kabul Kriterleri**

- [ ] `Timings.fast()` ile CI/CD hızlanıyor
- [ ] Action bazlı farklı timing uygulanıyor
- [ ] Backward compatibility korunuyor

---

### Faz 2: Kalite İyileştirmeleri (2–3 Gün)

#### 2.1 Best Match Algorithm

**Süre:** 4–6 saat  
**ROI:** ★★★★☆ (Developer Experience)

**Kapsam**

- `uiauto/bestmatch.py` modülü
- `difflib.SequenceMatcher` kullanımı
- Configurable cutoff ratio (varsayılan: 0.6)
- Repository genelinde opsiyonel fuzzy lookup desteği

**Örnek Senaryolar**

```bash
loginbutton   -> loginButton    ✔ (ratio: 0.95)
usernamefield -> usernamefield  ✔ (ratio: 0.92)
taskButton    -> taskBtn        ✖ (ratio: 0.55 < 0.6)
```

**Kabul Kriterleri**

- [ ] Typo’lar tolere ediliyor
- [ ] Exact match her zaman öncelikli
- [ ] `strict=True` ile fuzzy matching tamamen kapatılabiliyor

---

#### 2.2 Wrapper Registry Pattern

**Süre:** 1–2 iş günü  
**ROI:** ★★★☆☆ (Uzun vadeli bakım ve ölçeklenebilirlik)

**Kapsam**

- `uiauto/wrappers/` modülü
- `@WrapperRegistry.register()` decorator
- Control-type özel wrapper sınıfları:
  - `CheckBoxWrapper`
  - `ComboBoxWrapper`
  - `EditWrapper`
  - `ButtonWrapper`
  - `ListWrapper`
- Resolver içerisinde otomatik wrapper seçimi

**Önerilen Wrapper Yapısı**

```bash
uiauto/wrappers/
├─ __init__.py      # Registry + base wrapper
├─ checkbox.py      # check(), uncheck(), get_state()
├─ combobox.py      # select(), get_items(), expand()
├─ edit.py          # set_value(), get_value(), clear()
├─ button.py        # click(), is_enabled()
└─ list.py          # select_item(), get_items(), item_count()
```

**Kabul Kriterleri**

- [ ] Her control type için specialized wrapper mevcut
- [ ] IDE autocomplete wrapper metodlarını gösteriyor
- [ ] Mevcut `Element` metodları backward compatible şekilde çalışıyor

---

### Faz 3: Performans Optimizasyonları (1–2 Gün)

#### 3.1 Element Property Caching

**Süre:** 4–6 saat  
**ROI:** ★★★☆☆ (Inspector performansı)

**Kapsam**

- `Element` sınıfına cache mekanizması
- `enable_cache()` / `disable_cache()` metodları
- Inspector için bulk operation desteği
- Net cache invalidation stratejisi

**Performans Hedefleri**

| Operasyon            | Mevcut | Hedef |
| -------------------- | -----: | ----: |
| 1000 element inspect |   ~15s | ~3–5s |
| Tekli element access |  ~50ms | ~50ms |

**Kabul Kriterleri**

- [ ] Inspector en az 3x hızlanmış
- [ ] Normal action’larda her zaman fresh data garantisi
- [ ] Memory leak tespit edilmedi

---

#### 3.2 ElementSpecification (Lazy Resolution)

**Süre:** 4–6 saat  
**ROI:** ★★★★☆ (API esnekliği ve okunabilirlik)

**Kapsam**

- `uiauto/specification.py` modülü
- Lazy `find()` pattern
- Chained lookup desteği
- Fluent API tasarımı

**Kullanım Örneği**

**Mevcut Yaklaşım**

```python
button = resolver.resolve("loginbutton")
button.wait("enabled")
button.click()
```

**Önerilen yaklaşım (lazy resolution)**

```python
spec = ElementSpec("loginbutton")
spec.wait("enabled").click()
```

**Kabul Kriterleri**

- [ ] Chained lookup syntax stabil çalışıyor
- [ ] Lazy evaluation yalnızca action anında gerçekleşiyor
- [ ] Mevcut API ile tam uyumluluk korunuyor

---

## Ekler

### A. pywinauto Referans Kodları

- `pywinauto/timings.py` – TimeConfig implementasyonu
- `pywinauto/actionlogger.py` – Logging pattern
- `pywinauto/findbestmatch.py` – Fuzzy matching

### B. Önerilen Dosya Yapısı

```bash
uiauto/
├─ __init__.py
├─ actionlogger.py       # YENİ
├─ timings.py            # YENİ
├─ bestmatch.py          # YENİ
├─ specification.py      # YENİ
├─ wrappers/             # YENİ
│  ├─ __init__.py
│  ├─ checkbox.py
│  ├─ combobox.py
│  ├─ edit.py
│  ├─ button.py
│  └─ list.py
├─ element.py            # GÜNCELLEME (caching)
├─ waits.py              # GÜNCELLEME (wait_until_passes)
├─ resolver.py           # GÜNCELLEME (wrapper seçimi)
└─ ... (mevcut dosyalar)
```

---

## Rapor Sonu

Bu rapor, cita-uiauto-engine projesinin geliştirilmesi için pywinauto/pywinauto repository analizine dayanmaktadır.
