# FalconPy

## 🚀 安装和运行

### 环境要求
- Python 3.8+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/scyphozoax/FalconPy.git
   cd falconpy
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行应用**
   ```bash
   python main.py
   ```

### 依赖包说明
- `PyQt6` - 现代化GUI框架
- `requests` - HTTP请求库
- `Pillow` - 图像处理
- `aiohttp` - 异步HTTP客户端
- `cryptography` - 加密支持
- `psutil` - 系统性能监控
- `beautifulsoup4` - HTML解析

## 📖 使用指南

### 基本操作

1. **选择站点**
   - 在工具栏中选择要浏览的图片站点
   - 不同站点有不同的内容和特色

2. **搜索图片**
   - 在搜索框中输入关键词或标签
   - 支持多个标签组合搜索
   - 按回车键或点击搜索按钮开始搜索

3. **浏览图片**
   - 图片以网格形式展示
   - 点击图片查看大图
   - 使用分页控件浏览更多内容

4. **收藏管理**
   - 点击图片上的收藏按钮添加到收藏夹
   - 在左侧面板管理收藏夹
   - 支持创建多个收藏夹分类

### 快捷键操作

FalconPy 提供了丰富的快捷键支持，提高使用效率：

#### 🔍 搜索与导航
- **Ctrl+F** - 快速聚焦到搜索框
- **Ctrl+←** - 上一页
- **Ctrl+→** - 下一页
- **F5** - 刷新当前内容

#### 🖼️ 图片操作
- **Ctrl+D** - 切换当前选中图片的收藏状态
- **Ctrl+S** - 下载当前选中的图片
- **F11** - 切换全屏模式
- **Escape** - 退出全屏或关闭对话框

#### 📁 文件管理
- **Ctrl+I** - 导入收藏夹
- **Ctrl+E** - 导出收藏夹
- **Ctrl+Q** - 退出应用程序

#### ⚙️ 系统功能
- **Ctrl+L** - 打开账号登录对话框
- **Ctrl+,** - 打开设置对话框

> 💡 **使用提示**: 图片操作快捷键需要先选择图片（点击图片缩略图），选中的图片会显示蓝色边框。

### 高级功能

1. **账户登录**
   - 点击工具栏的登录按钮
   - 输入各站点的用户名和密码
   - 登录后可访问私人收藏和高级功能

2. **设置配置**
   - 菜单栏 → 设置 → 打开设置对话框
   - **外观设置**: 主题、字体大小
   - **网络设置**: 代理、超时时间
   - **下载设置**: 下载路径、文件命名

3. **性能监控**
   - 状态栏右侧显示性能信息
   - 实时监控内存和CPU使用率
   - 查看缓存统计和命中率

## 🔧 配置说明

### 配置文件位置
- Windows: `.\config.json`
- 配置文件会自动创建，包含默认设置

### 主要配置项
```json
{
  "window": {
    "size": [1200, 800],
    "maximized": false
  },
  "appearance": {
    "theme": "dark",
    "font_size": 10
  },
  "network": {
    "timeout": 30,
    "proxy": {
      "enabled": false,
      "host": "",
      "port": 0
    }
  },
  "download": {
    "path": "Downloads",
    "create_subfolder": true,
    "filename_format": "{site}_{id}_{title}"
  }
}
```

## 🛠️ 开发说明

### 项目结构
```
falconpy/
├── src/
│   ├── api/          # API客户端
│   ├── core/         # 核心功能
│   ├── ui/           # 用户界面
│   │   ├── dialogs/  # 对话框
│   │   ├── themes/   # 主题管理
│   │   └── widgets/  # UI组件
├── cache/            # 缓存目录
├── main.py          # 程序入口
├── requirements.txt # 依赖列表
└── test_app.py     # 测试脚本
```

### 核心模块
- **APIManager**: 管理各站点API客户端
- **CacheManager**: 智能缓存管理
- **DatabaseManager**: 本地数据库操作
- **SessionManager**: 用户会话管理
- **ThemeManager**: 主题和样式管理

### 测试
```bash
python test_app.py
```

## ⚠️ 注意事项

1. **网络要求**: 中国大陆用户需要挂梯使用
2. **内容警告**: 部分站点包含成人内容，请谨慎使用

## 🤝 贡献

欢迎提交Issue和Pull Request来改进FalconPy！

## 📄 许可证

本项目采用LGPL v2.1协议。
