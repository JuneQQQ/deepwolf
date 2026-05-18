# 🐺 deepwolf

**一个 LLM 狼人杀引擎 —— Agent 自我博弈竞技场，以及可解释的人类副驾。**

[![CI](https://github.com/JuneQQQ/deepwolf/actions/workflows/ci.yml/badge.svg)](https://github.com/JuneQQQ/deepwolf/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[English](README.md) | **中文**

狼人杀（又名 Mafia）是一个关于**隐藏信息、说服与欺骗**的游戏 —— 这些恰恰是大语言
模型难以衡量、人类也难以做好的能力。`deepwolf` 把这个游戏变成两样工具：

- 🤖 **自我博弈竞技场** —— 多个 LLM agent 在严格、可复现的规则引擎下进行完整对局，
  让你能够**基准测试**一个模型在不完全信息下推理、欺骗与推断的能力；
- 🧭 **人类副驾** —— 一个*可解释的*顾问，在**你**亲自上场时估算谁是狼人并为你的
  投票给出建议。

开箱即用、全程可离线运行（内置一个确定性的 mock 模型）；接入任意 OpenAI 兼容端点
即可使用真实模型。

---

## 为什么做这个项目

多数 LLM 基准测试是单轮、完全可观测的。狼人杀两者都不是：玩家必须追踪*谁说了什么*、
推理他们*为什么*这么说、在多个回合中维持一个自洽的谎言、并根据投票和死亡更新信念。
`deepwolf` 让这一切可被衡量 —— 同时把同样的信念追踪能力作为副驾提供给人类。

## 特性

- ♟️ **严格、种子化的规则引擎。** 昼夜循环，包含狼人、预言家、守卫、猎人、女巫能力。
  每局游戏都可由种子复现；非法或幻觉的 agent 决策永远无法破坏对局。
- 🌏 **中英双语。** 整个对局 —— 事件日志、角色、AI 发言、CLI —— 都能用英文或简体
  中文进行。加 `--lang zh` 即可。
- 🔌 **厂商中立的 LLM 接入。** 任意 OpenAI 兼容端点 —— OpenAI、DeepSeek、小米 MiMo、
  本地服务器。改一个环境变量即可切换。
- 🧪 **默认离线。** 确定性的 `MockProvider` 零网络、零密钥即可跑完整对局。
- 📊 **基准竞技场。** 跑成百上千局种子对局，得到阵营胜率、角色存活率、各 agent 胜率。
- 🧭 **可解释的副驾。** 不是黑盒：一个透明的、贝叶斯风格的信念模型，可选叠加 LLM 二次意见。

## 安装

```bash
git clone https://github.com/JuneQQQ/deepwolf.git
cd deepwolf
pip install -e ".[dev]"
```

## 快速上手

观看一局 AI 自我博弈 —— **无需 API key**：

```bash
deepwolf simulate --players 7 --seed 1
deepwolf simulate --players 7 --seed 1 --lang zh        # 用中文进行对局
deepwolf simulate --players 7 --seed 1 --transcript game.json   # + JSON 记录
```

在多局种子对局上做基准测试，或排名：

```bash
deepwolf arena --games 50 --players 7 --villagers mock --werewolves random
deepwolf leaderboard --games 30 --players 7 --markdown board.md
```

亲自上场，每一票都有副驾建议：

```bash
deepwolf play --players 7 --lang zh
```

## 接入真实模型

`deepwolf` 使用 OpenAI 的 `/chat/completions` 协议。把 `.env.example` 复制为 `.env`
并填写：

```bash
DEEPWOLF_PROVIDER=mimo            # 或：openai, deepseek, groq, openrouter
DEEPWOLF_API_KEY=sk-...
DEEPWOLF_MODEL=mimo-v2-flash
```

然后给任意命令加 `--provider env`。自定义端点与排错见
[`docs/providers.md`](docs/providers.md)。

## 工作原理

```
          ┌─────────────┐   PlayerView   ┌──────────────┐
          │  GameEngine  │ ─────────────▶ │    Agent     │
          │  （裁判）     │ ◀───────────── │ random / llm │
          └─────────────┘     决策         └──────────────┘
                 │                               │
              事件日志                        LLMProvider
                 │                        (mock / OpenAI 兼容)
        ┌────────┴────────┐
        ▼                 ▼
     竞技场            副驾.advise()
   （基准测试）       （信念模型 + LLM）
```

**事件日志**是唯一的事实来源。`PlayerView` 只是日志的一个*过滤视图* —— agent 在物理
上无法看到它不该看到的秘密。完整设计见 [`docs/architecture.md`](docs/architecture.md)。

## 库的用法

```python
from deepwolf import GameConfig, GameEngine, LLMAgent, MockProvider

provider = MockProvider(seed=0)
config = GameConfig.standard(n_players=7, seed=1, lang="zh")  # 中文对局
result = GameEngine(config, lambda pid, role: LLMAgent(pid, provider)).run()

print(result.winner.label, "获胜，共", result.days, "天")
```

## 路线图

见 [CHANGELOG.md](CHANGELOG.md) 与 [issue 列表](https://github.com/JuneQQQ/deepwolf/issues)。

## 贡献

欢迎各种规模的贡献 —— 见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE) © 2026 deepwolf 贡献者。
