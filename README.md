# Drama Web Crawler

海外短剧站点每日抓取服务，基于 `uv + Python + FastAPI` 实现，当前统一抓取 `NetShort`、`DramaBox`、`ReelShort`、`ShortMax` 四个站点，并按站点导出每日 CSV 文件。

## 项目目标

- 每日定时抓取海外短剧站点数据。
- 统一四个站点的剧级字段口径。
- 每站点每天导出一个 CSV 文件。
- 提供 FastAPI 接口供外部服务下载 CSV。
- 将通用逻辑下沉到 `src/core`，站点抓取逻辑保持独立。

## 当前状态

- 已实现站点：`netshort`、`dramabox`、`reelshort`、`shortmax`
- 已实现能力：
  - 单站 / 全站批量抓取
  - 每日定时调度
  - CSV 原子写入
  - CSV 下载接口
  - 单元测试与解析测试
- 当前限制：
  - `DramaBox` 在当前环境下会被 CloudFront 返回 `403`，代码链路已就位，但生产抓取需要额外访问策略支持。

## 目录结构

```text
.
├─ docs/
│  ├─ 海外站点数据维度可行性分析.md
│  ├─ 项目技术文档.md
│  └─ 接口文档.md
├─ src/
│  ├─ api/
│  ├─ config/
│  ├─ core/
│  ├─ jobs/
│  └─ spiders/
├─ tests/
├─ data/
├─ logs/
├─ main.py
└─ pyproject.toml
```

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 启动 API 服务（含定时任务）

```bash
uv run python main.py
```

默认监听 `0.0.0.0:9000`，每天 00:00 自动执行全站爬取。

### 手动执行一次抓取

全站抓取：

```bash
uv run python -m src.jobs.daily_crawl --site all
```

单站抓取：

```bash
uv run python -m src.jobs.daily_crawl --site reelshort
```

指定抓取日期：

```bash
uv run python -m src.jobs.daily_crawl --site shortmax --date 2026-04-19
```

### 启动调度器（独立模式）

```bash
uv run python -m src.jobs.scheduler
```

> 注：通常不需要单独启动调度器，`main.py` 已集成后台调度。

## 输出说明

- CSV 路径：`data/exports/{site}/{site}_{YYYY-MM-DD}.csv`
- 日志路径：`logs/{YYYY-MM-DD}.log`

统一 CSV 字段：

- `site`
- `site_drama_id`
- `title`
- `summary`
- `cover_url`
- `detail_url`
- `tag_list`
- `category_list`
- `audience_type`
- `publish_date_std`
- `play_count`
- `collect_count`
- `like_count`
- `episode_count`
- `episodes_preview_json`
- `metric_source`
- `crawl_date`
- `crawled_at`

说明：

- `tag_list`、`category_list` 使用 `|` 拼接。
- `episodes_preview_json` 保存最多 10 集的预览信息。
- 不可信或站点未稳定提供的指标统一写空，不伪造 `0`。

## API 概览

健康检查：

```http
GET /api/v1/healthz
```

下载导出：

```http
GET /api/v1/exports/{site}?date=YYYY-MM-DD
```

支持站点：

- `netshort`
- `dramabox`
- `reelshort`
- `shortmax`

未传 `date` 时，接口返回该站点最新可用 CSV。

## 配置项

复制 `.env.example` 为 `.env` 并按需修改：

```bash
cp .env.example .env
```

常用配置：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DRAMA_SERVER_PORT` | API 服务端口 | `9000` |
| `DRAMA_CRAWL_HOUR` | 定时爬取小时（24 小时制） | `0` |
| `DRAMA_CRAWL_MINUTE` | 定时爬取分钟 | `0` |
| `DRAMA_TIMEZONE` | 时区 | `Asia/Shanghai` |
| `DRAMA_HTTP_TIMEOUT` | HTTP 超时（秒） | `20.0` |
| `DRAMA_HTTP_DELAY_SECONDS` | 请求间隔（秒） | `0.0` |
| `DRAMA_HTTP_MAX_RETRIES` | 最大重试次数 | `2` |
| `DRAMA_MAX_ITEMS` | 最大抓取数（调试用） | 不限制 |

完整配置见 `.env.example`。

### 旧版环境变量

- `DRAMA_TIMEZONE`
- `DRAMA_DATA_DIR`
- `DRAMA_EXPORTS_DIR`
- `DRAMA_LOGS_DIR`
- `DRAMA_HTTP_TIMEOUT`
- `DRAMA_HTTP_DELAY_SECONDS`
- `DRAMA_HTTP_MAX_RETRIES`
- `DRAMA_USER_AGENT`
- `DRAMA_MAX_ITEMS`
- `DRAMABOX_MAX_PAGES`
- `REELSHORT_MAX_PAGES`

其中 `DRAMA_MAX_ITEMS` 主要用于调试，限制每个站点抓取记录数。

## 测试

运行全部测试：

```bash
uv run pytest
```

## 相关文档

- [站点字段分析](D:/dev/projects/drama-web-crawler/docs/海外站点数据维度可行性分析.md)
- [项目技术文档](D:/dev/projects/drama-web-crawler/docs/项目技术文档.md)
- [接口文档](D:/dev/projects/drama-web-crawler/docs/接口文档.md)
