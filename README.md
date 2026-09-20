# omerkara-bootstrap

Her makinede tek komutla proje ortamı hazırlar:

- **Task API** (tasks.omerkara.com / n8n) için token ve skill
- **Task MCP** (`https://tasks.omerkara.com/api/mcp`, OAuth) için `.mcp.json`
- **Orchestrator** için deploy tanımı ve proje kaydı
- **Claude Code** için `CLAUDE.md`, `.mcp.json` ve `.claude/settings.json`

## Kurulum (her makinede bir kez)

```bash
curl -fsSL https://raw.githubusercontent.com/omerfkara/omerkara-bootstrap/main/install.sh | bash
```

Kurulum şunları yapar:

1. Bu repoyu `~/.omerkara/bootstrap` altına klonlar.
2. Token'ları `~/.config/omerkara/credentials` dosyasına yazar (chmod 600). Sırayla şu kaynaklara bakar: ortam değişkeni, ardından 1Password, ardından kullanıcıya sorar.
3. `skills.txt` içindeki skill'leri `~/.claude/skills/` altına kurar. Kayıtlı değilse
   `ORCH_API` (orchestrator adresi) sorulur; boş geçilebilir, deploy komutları o
   zaman devre dışı kalır.
4. Task MCP için kurulum yapmaz — uzak bir sunucudur ve OAuth ile kimlik doğrular.
   Eskiden klonlanmış yerel bir kopya varsa uyarır (silinebilir).
5. `~/.zshrc` / `~/.bashrc` dosyasına credential yükleyen bir blok ekler; `omk` ve
   `omerkara-sdlc` skill'i `TASK_TOKEN`'ı buradan alır.
6. `omk` komutunu `~/.local/bin/omk` olarak bağlar.

Etkileşimsiz kurulum (CI, Pi, SSH):

```bash
TASK_TOKEN=... ORCH_TOKEN=... ORCH_API=https://orchestrator.example.com \
  ~/.omerkara/bootstrap/bin/omk setup
```

1Password ile:

```bash
export OMK_OP_TASK_TOKEN="op://Dev/task-api/token"
export OMK_OP_ORCH_TOKEN="op://Dev/orchestrator/token"
omk setup
```

## Kullanım

```bash
omk init visual-configurator --type web --github   # yeni proje
omk init harf-harbi --type api --dir .              # mevcut klonda (başka makine)
omk init test-app --dry-run                         # sadece göster
omk token                                           # TASK_TOKEN'ı yenile (doğrulayıp kaydeder)
omk token --orch                                    # ORCH_TOKEN'ı yenile
omk doctor                                          # kontrol
omk update                                          # bootstrap + skill + mcp güncelle

omk deploy                                          # elle deploy tetikle
omk deploy --wait                                   # bitene kadar izle, hata olursa logu bas
omk deploy --dry-run                                # isteği göster, gönderme
omk status                                          # bu projenin son deploy'ları
omk status --all -n 20                              # tüm projeler
omk logs <deployment-id>                            # deploy logu
```

| `--type` | Runner |
| :--- | :--- |
| `ios`, `android`, `flutter` | macos |
| `web`, `cv` | ubuntu |
| `api` | pi |
| `other` | orchestrator yok |

### `omk init` ne yapar?

1. Proje adını doğrular (küçük harf, rakam, `-`).
2. Makine kurulmamışsa önce `omk setup` çalıştırır.
3. Klasör git reposu değilse `git init` yapar.
4. Task API'de bu projenin dokümanları varsa `docs/` altına indirir. İkinci makinede proje böylece senkronize olur.
5. Şablonlardan şu dosyaları üretir: `CLAUDE.md`, `docs/PROMPT.md`, `docs/SCOPE.md`, `.env.example`, `.env`, `.claude/settings.json`, `deploy.yml`, `.mcp.json`. Mevcut dosyaların üzerine yazmaz; yazması için `--force` gerekir.
6. `.gitignore` dosyasına `.env` ve ilgili satırları ekler.
7. Uzakta olmayan PROMPT/SCOPE dokümanlarını `POST /documents/upsert` ile gönderir. Uzaktaki dokümanın üzerine yazmaz.
8. Orchestrator'a `POST $ORCH_API$ORCH_REGISTER_PATH` çağrısıyla kayıt yapar. ORCH_API tanımlı değilse bu adım atlanır.
9. Projede hiç task yoksa bir başlangıç task'ı açar.
10. `--github` verilmişse private repo oluşturur. `ORCH_WEBHOOK_URL` ve `ORCH_WEBHOOK_SECRET` tanımlıysa orchestrator webhook'unu da ekler.

Komut tekrar çalıştırılabilir; her çalıştırmada eksik olanı tamamlar.

## Güvenlik

- Token'lar hiçbir proje dosyasına yazılmaz. `.mcp.json` yalnızca MCP adresini içerir —
  hiç secret taşımaz, rahatça commit edilir. Kimlik doğrulama OAuth ile yapılır:
  Claude Code içinde ilk kullanımda `/mcp` → *Authenticate*.
- `.env` gitignore'dadır ve yalnızca secret olmayan proje ayarlarını içerir.
- Token'ı yenilemek için: `omk token`. Yeni değeri sorar, baştaki/sondaki boşlukları
  kırpar (birebir eşleşme gerektiği için önemli), **kaydetmeden önce** canlı bir
  çağrıyla doğrular. Doğrulama başarısızsa dosyaya dokunmaz; `--force` ile zorlanır.
  Etkileşimsiz: `OMK_TOKEN_VALUE=... omk token`.
- Terminale iki kez yapıştırılan token birebir ikiye katlanır; yankı kapalı olduğu
  için fark edilmez ve sunucu tarafındaki tam eşleşme sessizce başarısız olur.
  `omk token` bunu tanır, tek kopyayı da dener ve doğrulanan değeri kaydeder.

## Yapılandırma

| Değişken | Varsayılan | Açıklama |
| :--- | :--- | :--- |
| `TASK_API` | `https://n8n.omerkara.com/webhook` | Task API adresi (HTTP, `X-Task-Token`) |
| `TASK_MCP_URL` | `https://tasks.omerkara.com/api/mcp` | Task MCP adresi (OAuth) |
| `ORCH_API` | – | Orchestrator adresi (örn. `https://orchestrator.omerkara.com`) |
| `ORCH_REGISTER_PATH` | `/api/projects` | Proje kaydı ve init ucu |
| `ORCH_DEPLOY_PATH` | `/api/deployments` | Deployment listesi |
| `ORCH_STATUS_PATH` | `/api/status` | Tek deployment durumu |
| `ORCH_LOGS_PATH` | `/api/logs` | Deployment logu |
| `ORCH_HEALTH_PATH` | `/health` | Sağlık kontrolü |
| `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` | – | Cloudflare Access servis token'ı |
| `ORCH_WEBHOOK_URL` / `ORCH_WEBHOOK_SECRET` | – | GitHub webhook ayarları |
| `OMK_GITHUB_USER` | `omerfkara` | Repo sahibi |

Kalıcı ayarlar `~/.config/omerkara/config` dosyasında tutulur (KEY='value').
Öncelik sırası: **ortam değişkeni > credentials > config > varsayılan** — yani tek
seferlik `ORCH_API=https://... omk status` çalışır.

## Yeni skill eklemek

`skills.txt` dosyasına bir satır ekleyin ve her makinede `omk update` çalıştırın:

```
omerkara-deploy|https://github.com/omerfkara/omerkara-deploy.git|no
```

## Orchestrator

Deploy tanımının tek kaynağı projedeki `deploy.yml`'dir; hem orchestrator kaydı hem de
`omk deploy` bu dosyayı okur. Sertifika, SSH anahtarı ve store credential'ları
orchestrator'da durur, proje repolarında değil.

```
omk deploy [proje] [--wait] [--dry-run]
omk status [proje] [-n <adet>] [--all]
omk logs <deployment-id> [satır]
```

`--wait`, deployment `done` ya da `failed` olana kadar durumu yoklar
(`OMK_WAIT_INTERVAL`, `OMK_WAIT_MAX` ile ayarlanır) ve başarısızlıkta logun son
satırlarını basar.

### API

Kaynak: `https://orchestrator.omerkara.com/orchestrator.md`

Kimlik doğrulama — `/health` dışındaki **her** uç üç başlık ister:

```
Authorization: Bearer $ORCH_TOKEN
CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID
CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET
```

Cloudflare Access servis token'ı eksikse yanıt 403 olur; `omk doctor` ayrıca uyarır.

```
POST $ORCH_API/api/projects              # proje kaydı (deploy.yml'den üretilir)
{ "name": "...", "git_url": "...", "target_runner": "macos|ubuntu|pi",
  "build_command": "...", "deploy_command": "...", "watch_paths": [...] }
→ göndermediğiniz alanlar orchestrator tarafında korunur

POST $ORCH_API/api/projects/<ad>/init    # elle deploy tetikleme
{ "deploy": true }  → 202 { "deployment_id": <id> }

GET  $ORCH_API/api/deployments?project=<ad>&limit=<n>
GET  $ORCH_API/api/status/<id>           # done | failed | pending
GET  $ORCH_API/api/logs/<id>             # düz metin
GET  $ORCH_API/health
```

Deploy normalde **main dalına push** ile tetiklenir: orchestrator'ın GitHub App'i
hesabın tüm push olaylarını yakalar, ayrıca webhook kaydı gerekmez. `omk deploy`
bunu elle tetiklemek içindir.

Alan adları esnek okunur (`server`/`runner`/`target`, `status`/`state`,
`deployment_id`/`id` …); eşleşmeler `lib/orch.py` içindeki `FIELDS` tablosunda.

## Gereksinimler

- git, curl, python3, perl (macOS ve Ubuntu/Raspberry Pi OS'ta hazır bulunur)
- Opsiyonel: `gh`, `uv`, `op` (1Password CLI), `claude`
- Windows: WSL içinde çalıştırın.

## Yapı

```
bin/omk            CLI (setup / init / update / doctor)
lib/common.sh      yardımcı fonksiyonlar (bash 3.2 uyumlu)
lib/docs.py        Task API doküman yanıtı ayrıştırıcı
lib/orch.py        deploy.yml ayrıştırıcı + orchestrator yanıt biçimlendirici
templates/         proje şablonları ({{PROJECT}} gibi yer tutucular)
skills.txt         kurulacak skill'ler
install.sh         curl | bash giriş noktası
```
