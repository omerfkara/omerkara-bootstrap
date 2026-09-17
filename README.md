# omerkara-bootstrap

Her makinede tek komutla proje ortamı hazırlar:

- **Task API** (tasks.omerkara.com / n8n) için token, skill ve MCP
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
4. task-mcp'yi `~/.omerkara/task-mcp` altına kurar ve bağımlılıklarını `~/.omerkara/venv` içine yükler.
5. `~/.zshrc` / `~/.bashrc` dosyasına credential yükleyen bir blok ekler. Claude Code, `.mcp.json` içindeki `${TASK_TOKEN}` değerini buradan alır.
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
omk doctor                                          # kontrol
omk update                                          # bootstrap + skill + mcp güncelle
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

- Token'lar hiçbir proje dosyasına yazılmaz. `.mcp.json` sadece `${TASK_TOKEN}` referansı içerir, bu yüzden commit edilebilir.
- `.env` gitignore'dadır ve yalnızca secret olmayan proje ayarlarını içerir.
- Token'ı yenilemek için: `~/.config/omerkara/credentials` içindeki satırı silin, ardından `omk setup` çalıştırın.

## Yapılandırma

| Değişken | Varsayılan | Açıklama |
| :--- | :--- | :--- |
| `TASK_API` | `https://n8n.omerkara.com/webhook` | Task API adresi |
| `ORCH_API` | – | Orchestrator adresi (örn. `https://orchestrator.omerkara.com`) |
| `ORCH_REGISTER_PATH` | `/projects` | Proje kayıt endpoint'i |
| `ORCH_WEBHOOK_URL` / `ORCH_WEBHOOK_SECRET` | – | GitHub webhook ayarları |
| `OMK_GITHUB_USER` | `omerfkara` | Repo sahibi |

Kalıcı ayarlar `~/.config/omerkara/config` dosyasında tutulur (KEY='value').

## Yeni skill eklemek

`skills.txt` dosyasına bir satır ekleyin ve her makinede `omk update` çalıştırın:

```
omerkara-deploy|https://github.com/omerfkara/omerkara-deploy.git|no
```

## Orchestrator tarafında beklenen API

Orchestrator'da henüz yoksa eklenmesi gereken uçlar:

```
POST /projects      Authorization: Bearer <ORCH_TOKEN>
{ "name": "...", "type": "web", "runner": "ubuntu", "repo": "omerfkara/..." }
→ 201 oluşturuldu / 409 zaten var

GET /health         → 200
```

## Gereksinimler

- git, curl, python3, perl (macOS ve Ubuntu/Raspberry Pi OS'ta hazır bulunur)
- Opsiyonel: `gh`, `uv`, `op` (1Password CLI), `claude`
- Windows: WSL içinde çalıştırın.

## Yapı

```
bin/omk            CLI (setup / init / update / doctor)
lib/common.sh      yardımcı fonksiyonlar (bash 3.2 uyumlu)
lib/docs.py        Task API doküman yanıtı ayrıştırıcı
templates/         proje şablonları ({{PROJECT}} gibi yer tutucular)
skills.txt         kurulacak skill'ler
install.sh         curl | bash giriş noktası
```
