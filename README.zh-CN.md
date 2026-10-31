# msauto —— 用命令行驱动 NI Multisim 14

`msauto` 通过 Multisim 官方的 COM 自动化接口，把电路设计的操作变成一个可重复的脚本流程：

```
类 SPICE 网表 ──► .ms14 原理图 ──► 后台瞬态仿真 ──► CSV ──► 断言
```

不抢鼠标键盘、不模拟点击；Multisim 在后台打开、仿真、导出数据、关闭。

## 组成

| 组件 | 作用 |
|---|---|
| `msctl`（C#，.NET 4，32 位） | COM 驱动：打开工程、枚举器件/探针、导出网表、跑瞬态并把结果写成 CSV、换器件、导出 PNG，输出 JSON。 |
| `msauto`（Python 3.9+） | 调用 `msctl`、读 CSV、提供波形断言 `Checks`；另有网表检查器和本地模板包工具。 |
| `docs/` | COM 接口踩坑手册。 |
| `examples/` | 快速上手脚本，以及完整的过负荷保护单元示例（建图 → 仿真 → 57 项断言）。 |

## 安装

```bat
git clone <repo-url>
cd multisim-automation

csharp\build.cmd        :: 用本机 Multisim 的类型库生成 interop 并编译 msctl
pip install -e python
```

需要：Windows、有授权的 Multisim 14.x、.NET Framework 4（系统自带）、Python 3.9+。

## 快速使用

```bat
msctl introspect C:\circuits\filter.ms14
msctl simulate C:\circuits\filter.ms14 --duration 0.02 --rate 20000 --csv run.csv
```

```python
from msauto import simulate, Checks

sim = simulate(r"C:\circuits\filter.ms14", duration=0.02, rate=20_000, csv="run.csv")
chk = Checks(sim)
chk.expect_high("V(OutProbe1)", 15e-3, "15 ms 后比较器输出为高")
chk.report()
chk.raise_for_failures()
```

命令行还提供 `msauto lint <网表>`（检查裸 `1`、重名器件、缺 `.end` 等）和
`msauto pack validate|build`（本地模板包校验/组装）。

## 必须知道的限制

- 仅 Windows + Multisim 14.x；COM 服务是 32 位，`msctl` 也必须是 32 位。
- COM 只能读取**已经放置探针**的信号，不能对任意网络临时请求 `V(net)`。
- 探针按坐标吸附，布线密集时可能吸到别的网络。
- Multisim 14.3 的蜂鸣器/指示灯/继电器符号是交互动画件、没有 SPICE 模型，
  仿真中表现为开路，需要用电学等效件代替并注明。
- 自动布局只保证功能，不保证美观；电源引脚多的数字电路交叉率容易超标。

## 模板策略

元件模板属于 NI 授权内容，本仓库**只放代码**。每位使用者需要用
`multisim-mcp` 里的本地提取工具从自己安装的 Multisim 中生成模板包，放在本机，
不得提交或分发（`.gitignore` 已排除常见目录名）。

详见 [docs/template-packs.md](docs/template-packs.md)。

## 许可

MIT。与 National Instruments 无隶属关系；Multisim 是 NI 的商标。
第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
