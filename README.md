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
3. `skills.txt` içindeki skill'leri `~/.claude/skills/` altına kurar.
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

omk deploy --env staging                            # orchestrator'a deploy
omk deploy --env production --wait                  # bitene kadar izle
omk deploy --ref hotfix/1 --dry-run                 # gövdeyi göster, gönderme
omk status                                          # bu projenin son deploy'ları
omk status --all -n 20                              # tüm projeler
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

## Yapılandırma

| Değişken | Varsayılan | Açıklama |
| :--- | :--- | :--- |
| `TASK_API` | `https://n8n.omerkara.com/webhook` | Task API adresi (HTTP, `X-Task-Token`) |
| `TASK_MCP_URL` | `https://tasks.omerkara.com/api/mcp` | Task MCP adresi (OAuth) |
| `ORCH_API` | – | Orchestrator adresi (örn. `https://orchestrator.omerkara.com`) |
| `ORCH_REGISTER_PATH` | `/projects` | Proje kayıt endpoint'i |
| `ORCH_DEPLOY_PATH` | `/deployments` | Deploy tetikleme / listeleme endpoint'i |
| `ORCH_HEALTH_PATH` | `/health` | Sağlık kontrolü endpoint'i |
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
omk deploy [proje] [--env <ortam>] [--ref <dal|commit>] [--wait] [--dry-run]
omk status [proje] [-n <adet>] [--all]
```

`--env` verildiğinde referans `deploy.yml`'deki o ortamın `branch` değerinden alınır;
`--ref` her zaman onu ezer. `--wait`, deployment `done/success` ya da `failed/error`
olana kadar durumu yoklar (`OMK_WAIT_INTERVAL`, `OMK_WAIT_MAX` ile ayarlanır).

### Beklenen API

Uç nokta yolları ortam değişkeniyle değiştirilebilir; orchestrator farklı bir şema
kullanıyorsa kod değil yalnızca bu değerler değişir. Yetkilendirme her istekte
`Authorization: Bearer $ORCH_TOKEN`.

```
POST $ORCH_API$ORCH_REGISTER_PATH        # varsayılan /projects
{ "project": "...", "repo": "omerfkara/...", "type": "web", "runner": "ubuntu", "ref": "main" }
→ 2xx oluşturuldu · 409 zaten var

POST $ORCH_API$ORCH_DEPLOY_PATH          # varsayılan /deployments
{ "project": "...", "ref": "main", "environment": "production", "trigger": "cli", ... }
→ 2xx { "id": "...", "status": "queued" }

GET  $ORCH_API$ORCH_DEPLOY_PATH/<id>     # --wait bunu yoklar
→ 2xx { "id": "...", "status": "running|done|failed" }

GET  $ORCH_API$ORCH_DEPLOY_PATH?project=<ad>&limit=<n>
→ 2xx [ { project, server, status, trigger, timestamp }, ... ]

GET  $ORCH_API$ORCH_HEALTH_PATH          # varsayılan /health, omk doctor kullanır
→ 2xx
```

Yanıt biçimi esnektir: düz liste, `{"deployments": [...]}`, `{"data": [...]}` ya da
n8n'in `[{"json": {...}}]` biçimi kabul edilir. Alan adları da esnektir —
`server`/`runner`/`target`, `status`/`state`, `created_at`/`timestamp` gibi karşılıklar
`lib/orch.py` içindeki `FIELDS` tablosunda tutulur; yeni bir ad çıkarsa oraya bir satır
eklemek yeter.

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
