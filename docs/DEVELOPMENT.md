# Crawl4Weibo 开发文档

## 目录
- [开发环境设置](#开发环境设置)
- [项目结构](#项目结构)
- [开发工作流](#开发工作流)
- [测试指南](#测试指南)
- [代码质量](#代码质量)
- [CI/CD使用方法](#cicd使用方法)
- [发布流程](#发布流程)

## 开发环境设置

### 环境要求
- Python 3.7+
- uv (推荐的包管理工具)

### 快速开始
```bash
# 克隆项目
git clone https://github.com/Kritoooo/crawl4weibo.git
cd crawl4weibo

# 安装开发依赖
uv sync --dev

# 运行测试确保环境正常
uv run pytest tests/ -v
```

### 开发依赖说明
```toml
[project.optional-dependencies]
dev = [
    "pytest>=6.0",      # 测试框架
    "pytest-cov",       # 测试覆盖率
    "black",            # 代码格式化
    "isort",            # 导入排序
    "flake8",           # 代码质量检查
]
```

## 项目结构

```
crawl4weibo/
├── crawl4weibo/           # 主包
│   ├── __init__.py
│   ├── core/              # 核心功能
│   │   ├── __init__.py
│   │   └── client.py      # WeiboClient主要实现
│   ├── models/            # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py        # User模型
│   │   └── post.py        # Post模型
│   ├── utils/             # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py      # 日志工具
│   │   └── parser.py      # 解析工具
│   └── exceptions/        # 自定义异常
│       ├── __init__.py
│       └── base.py        # 基础异常类
├── tests/                 # 测试文件
│   ├── __init__.py
│   ├── test_models.py     # 模型单元测试
│   ├── test_client.py     # 客户端单元测试
│   └── test_integration.py # 集成测试
├── docs/                  # 文档
├── examples/              # 示例代码
├── .github/workflows/     # GitHub Actions配置
├── pyproject.toml         # 项目配置
├── pytest.ini            # 测试配置
└── README.md
```

## 开发工作流

### 分支策略
- `main` - 主分支，稳定版本
- `develop` - 开发分支
- `feature/*` - 功能分支
- `hotfix/*` - 热修复分支

### 功能开发流程
```bash
# 1. 从main创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. 开发过程中持续测试
uv run pytest tests/ -m unit  # 快速单元测试

# 3. 提交前完整检查
uv run black crawl4weibo tests/    # 格式化代码
uv run isort crawl4weibo tests/    # 排序导入
uv run flake8 crawl4weibo          # 检查代码质量
uv run pytest tests/               # 运行所有测试

# 4. 提交代码
git add .
git commit -m "feat: add your feature description"

# 5. 推送并创建PR
git push origin feature/your-feature-name
# 然后在GitHub创建Pull Request
```

### 提交信息规范
使用约定式提交格式：
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整（不影响功能）
refactor: 重构代码
test: 添加测试
chore: 构建或工具相关
```

## 测试指南

### 测试类型
项目包含两种类型的测试：

#### 单元测试 (`@pytest.mark.unit`)
- 测试单个函数或类的功能
- 不依赖外部API或服务
- 运行快速，适合开发过程中频繁运行

```bash
# 只运行单元测试
uv run pytest tests/ -m unit -v
```

#### 集成测试 (`@pytest.mark.integration`)
- 测试与真实微博API的交互
- 验证API返回数据结构的正确性
- 运行较慢，适合完整验证

```bash
# 只运行集成测试
uv run pytest tests/ -m integration -v
```

### 运行测试
```bash
# 运行所有测试
uv run pytest tests/ -v

# 带覆盖率报告
uv run pytest tests/ --cov=crawl4weibo --cov-report=html

# 运行特定测试文件
uv run pytest tests/test_models.py -v

# 运行特定测试方法
uv run pytest tests/test_models.py::TestUser::test_user_creation -v
```

### 编写测试

#### 单元测试示例
```python
import pytest
from crawl4weibo.models.user import User

@pytest.mark.unit
class TestUser:
    def test_user_creation(self):
        user = User(id="123", screen_name="TestUser")
        assert user.id == "123"
        assert user.screen_name == "TestUser"
```

#### 集成测试示例
```python
import pytest
from crawl4weibo import WeiboClient

@pytest.mark.integration
class TestWeiboClientIntegration:
    def test_get_user_by_uid_returns_data(self):
        client = WeiboClient()
        try:
            user = client.get_user_by_uid("2656274875")
            assert user is not None
            assert hasattr(user, 'screen_name')
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
```

## 代码质量

### 代码风格
项目使用以下工具确保代码质量：

#### Black - 代码格式化
```bash
# 检查格式
uv run black --check crawl4weibo tests/

# 自动格式化
uv run black crawl4weibo tests/
```

#### isort - 导入排序
```bash
# 检查导入排序
uv run isort --check-only crawl4weibo tests/

# 自动排序
uv run isort crawl4weibo tests/
```

#### flake8 - 代码检查
```bash
# 运行代码检查
uv run flake8 crawl4weibo
```

### 配置文件
代码质量配置在 `pyproject.toml` 中：
```toml
[tool.black]
line-length = 88
target-version = ['py37']

[tool.isort]
profile = "black"
line_length = 88
```

## CI/CD使用方法

### GitHub Actions 工作流

项目包含3个主要的CI/CD工作流：

#### 1. 主CI流水线 (`.github/workflows/ci.yml`)
**触发条件：**
- 推送到 `main` 或 `develop` 分支
- 向 `main` 分支创建PR
- 发布release

**执行步骤：**
1. 多Python版本测试 (3.7-3.11)
2. 代码质量检查 (flake8, black, isort)
3. 运行测试套件
4. 生成覆盖率报告
5. 构建Python包
6. 自动发布到PyPI（仅在release时）

#### 2. 发布流水线 (`.github/workflows/release.yml`)
**触发条件：**
- 推送Git标签 (`v*`)

**执行步骤：**
1. 构建Python包
2. 创建GitHub Release
3. 自动发布到PyPI

#### 3. 代码质量检查 (`.github/workflows/code-quality.yml`)
**执行检查：**
- flake8 语法检查
- black 格式检查
- isort 导入排序检查
- bandit 安全扫描
- safety 依赖漏洞检查

### 本地CI检查
在推送代码前，可以本地运行相同的检查：
```bash
# 完整的CI检查流程
uv sync --dev                      # 安装依赖
uv run black crawl4weibo tests/    # 格式化
uv run isort crawl4weibo tests/    # 排序导入
uv run flake8 crawl4weibo          # 代码检查
uv run pytest tests/ -v           # 运行测试
uv build                           # 构建包
```

### GitHub仓库设置

#### 必要的Secrets
在 `Settings → Secrets and variables → Actions` 中添加：
```
PYPI_API_TOKEN=your_pypi_token_here
```

#### 获取PyPI Token
1. 登录 [PyPI](https://pypi.org/)
2. 进入 Account Settings
3. 创建API Token
4. 复制token到GitHub Secrets

## 发布流程

### 语义化版本
遵循 [语义化版本](https://semver.org/) 规范：
- `v1.0.0` - 主版本（破坏性更改）
- `v0.1.0` - 次版本（新功能，向后兼容）
- `v0.0.1` - 补丁版本（bug修复，向后兼容）

### 发布步骤
1. **准备发布**
   ```bash
   # 确保在main分支且代码最新
   git checkout main
   git pull origin main
   
   # 运行完整测试
   uv run pytest tests/ -v
   ```

2. **更新版本**
   - 手动更新 `pyproject.toml` 中的版本号（如果使用 `dynamic = ["version"]`，则自动从git标签获取）

3. **创建标签并推送**
   ```bash
   # 提交版本更改（如果有）
   git add pyproject.toml
   git commit -m "bump version to 0.1.5"
   
   # 创建标签
   git tag v0.1.5
   
   # 推送代码和标签
   git push origin main
   git push origin v0.1.5
   ```

4. **自动发布**
   - GitHub Actions 自动触发发布流水线
   - 自动创建 GitHub Release
   - 自动发布到 PyPI

### 发布检查清单
- [ ] 所有测试通过
- [ ] 代码质量检查通过
- [ ] 文档更新完成
- [ ] CHANGELOG更新（如果有）
- [ ] 版本号更新正确
- [ ] 创建并推送标签
- [ ] 确认GitHub Release创建成功
- [ ] 确认PyPI发布成功

### 回滚发布
如果发现发布有问题：
```bash
# 删除本地标签
git tag -d v0.1.5

# 删除远程标签
git push origin --delete v0.1.5

# 在PyPI删除对应版本（需要手动操作）
```

## 常见问题

### 测试失败
```bash
# 查看详细错误信息
uv run pytest tests/ -v --tb=long

# 运行单个失败测试
uv run pytest tests/test_file.py::test_function -v
```

### 代码格式问题
```bash
# 自动修复格式问题
uv run black crawl4weibo tests/
uv run isort crawl4weibo tests/
```

### 依赖问题
```bash
# 重新安装依赖
rm -rf .venv
uv venv
uv sync --dev
```

### CI失败
1. 查看GitHub Actions日志
2. 本地复现相同的检查步骤
3. 修复问题后重新推送

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 确保所有检查通过
5. 创建Pull Request
6. 响应Code Review反馈

### Code Review检查点
- 代码功能正确性
- 测试覆盖率
- 代码风格一致性
- 文档完整性
- 性能影响
- 向后兼容性

欢迎贡献代码！如有问题请创建Issue讨论。