# 智汇出海情报雷达 (Overseas AI Scout - OAS)

本地部署的自动化情报系统，帮助跨境支付BD发现中国AI出海公司。

## 功能特性

- **多数据源采集**: Kickstarter, Product Hunt, RSS订阅, GitHub, IT桔子等
- **数据清洗与去重**: 自动标准化、去重、入库
- **智能评分**: 多维度评分（融资轮次、招聘海外岗位、目标市场等）
- **企业微信推送**: 高潜力客户自动推送到手机
- **Web管理界面**: 实时查看公司列表、详情、监控仪表板

## 项目结构

```
OAS/
├── main.py                 # 入口，启动调度器 + Flask 服务
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖列表
├── README.md               # 本文件
├── models.py               # 数据库模型
├── cleaner.py              # 数据清洗模块
├── scorer.py               # 评分模块
├── notifier.py             # 企业微信推送
├── utils.py                # 工具函数
├── collectors/             # 数据采集器
│   ├── __init__.py
│   ├── kickstarter.py
│   ├── producthunt.py
│   ├── itjuzi.py
│   ├── rss_feeds.py
│   └── github.py
└── web/                    # Web前端
    ├── __init__.py
    ├── app.py
    └── templates/
        ├── index.html
        ├── company.html
        └── dashboard.html
```

## 安装部署

### 1. 安装依赖

```bash
cd OAS
pip install -r requirements.txt
```

### 2. 配置 config.yaml

复制并编辑配置文件，填入你的企业微信机器人Webhook URL：

```yaml
# 企业微信配置
wechat:
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE"
  mention_mobile_list: ["your_phone_number"]
```

获取Webhook URL方法：
1. 打开企业微信群聊设置
2. 点击"添加群机器人"
3. 创建机器人后复制Webhook地址

### 3. 启动服务

```bash
python main.py
```

服务启动后：
- Web界面: http://localhost:5000
- 定时任务: 每天8:00全量采集，每2小时增量采集

## Web界面功能

### 公司列表 (/)
- 查看所有已采集公司
- 按评分、融资轮次筛选
- 查看公司详情

### 公司详情 (/company/<id>)
- 公司基本信息
- 评分明细
- 事件时间线

### 监控面板 (/dashboard)
- 系统统计信息
- 手动触发采集/评分/推送
- 查看采集器状态

## 评分规则

| 维度 | 最高分 | 说明 |
|------|--------|------|
| 融资轮次 | 20 | A轮+10, B轮+15, C轮+20... |
| 海外招聘 | 15 | 有海外岗位招聘 |
| 目标市场 | 10 | 目标市场为美国/欧洲 |
| 近期产品发布 | 10 | 30天内有产品发布 |
| 出海动态 | 5 | 30天内有出海动态 |
| GitHub活跃度 | 15 | 有GitHub仓库 |
| 众筹平台 | 10 | Kickstarter/Indiegogo项目 |
| Product Hunt | 5 | 有Product Hunt产品 |
| 媒体报道 | 10 | 30天内有新闻报道 |

**总分 >= 60 分** 的公司会收到推送通知。

## 手动操作

### 触发采集
```bash
curl -X POST http://localhost:5000/api/run
```

### 触发评分
```bash
curl -X POST http://localhost:5000/api/score
```

### 触发推送
```bash
curl -X POST http://localhost:5000/api/notify
```

## 常见问题

### Q: 采集器无法获取数据？
A: 部分数据源可能需要VPN或代理。请检查网络连接。

### Q: 企业微信收不到推送？
A: 1. 检查webhook URL是否正确
   2. 检查机器人是否被移除
   3. 确认评分>=60分的公司存在

### Q: 如何查看日志？
A: 日志文件位于 `logs/oas.log`

## 技术栈

- Python 3.8+
- Flask - Web框架
- SQLite - 数据库
- APScheduler - 定时任务
- BeautifulSoup4 - 网页解析
- Feedparser - RSS解析

## 许可证

MIT License
