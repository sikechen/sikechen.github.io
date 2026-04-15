# 股市新闻监控系统 - 定时任务配置

## 方案一：使用 crontab (Linux/Mac)

```bash
# 编辑 crontab
crontab -e

# 添加以下内容（每2小时执行一次）
0 */2 * * * cd /path/to/股市新闻网页 && /usr/bin/python3 scripts/main.py >> logs/cron.log 2>&1

# 说明：
# - /path/to/股市新闻网页 替换为实际项目路径
# - /usr/bin/python3 替换为你的Python路径（可用 which python3 查看）
```

## 方案二：使用 systemd (Linux)

创建服务文件 `/etc/systemd/system/stock-monitor.service`:

```ini
[Unit]
Description=Stock Market News Monitor
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/股市新闻网页
ExecStart=/usr/bin/python3 scripts/main.py
StandardOutput=append:/var/log/stock-monitor.log
StandardError=append:/var/log/stock-monitor.log
```

创建定时器 `/etc/systemd/system/stock-monitor.timer`:

```ini
[Unit]
Description=Run Stock Monitor every 2 hours
Requires=stock-monitor.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=2h
Unit=stock-monitor.service

[Install]
WantedBy=timers.target
```

启用定时器:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-monitor.timer
sudo systemctl start stock-monitor.timer
```

## 方案三：使用 Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每2小时
4. 设置操作：
   - 程序: `python`
   - 参数: `scripts\main.py`
   - 起始位置: `项目完整路径\股市新闻网页`

## 方案四：使用 GitHub Actions (CI/CD 部署)

创建文件 `.github/workflows/update.yml`:

```yaml
name: Update Stock Monitor

on:
  schedule:
    # 每2小时执行一次 (UTC时间)
    - cron: '0 */2 * * *'
  workflow_dispatch:  # 支持手动触发

jobs:
  update:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4 lxml pandas echarts
          
      - name: Run crawler
        run: python scripts/main.py
        
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
```

## 方案五：使用第三方调度服务

### Apify (推荐用于云端运行)
```javascript
// Apify actor 配置
{
  "actorSpecification": 1,
  "name": "stock-news-monitor",
  "version": "1.0.0",
  "scheduling": {
    "cronPattern": "0 */2 * * *"
  }
}
```

### Railway / Render
在 Railway 或 Render 上部署，设置 cron job 为 `0 */2 * * *`

## 日志管理

创建日志目录:
```bash
mkdir -p 股市新闻网页/logs
```

查看日志:
```bash
# Linux/Mac
tail -f 股市新闻网页/logs/crawler.log

# Windows PowerShell
Get-Content 股市新闻网页/logs/crawler.log -Wait -Tail 50
```

## 故障排除

1. **Python路径问题**: 使用绝对路径
   ```bash
   which python3  # 查看Python路径
   ```

2. **权限问题**: 确保脚本可执行
   ```bash
   chmod +x scripts/main.py
   ```

3. **依赖缺失**: 先安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. **网络问题**: 检查代理设置（如果有）
   ```python
   import os
   os.environ['HTTP_PROXY'] = 'http://proxy:port'
   os.environ['HTTPS_PROXY'] = 'http://proxy:port'
   ```

## 生产环境建议

1. **使用虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   .\venv\Scripts\activate   # Windows
   ```

2. **使用进程管理器 (PM2)**
   ```bash
   npm install -g pm2
   pm2 start scripts/main.py --name stock-monitor --cron-restart="0 */2 * * *"
   ```

3. **设置环境变量**
   ```bash
   export PYTHONPATH=/path/to/股市新闻网页/scripts:$PYTHONPATH
   ```
