# 1 文件传输

将源服务器的文件夹 malicous_mas 拷贝到目标服务器 CodeProjects 目录下：

```shell
scp -r luotianlong@IP(source):/home/luotianlong/CodeProjects/malicous_mas luotianlong@IP(target):/home/luotianlong/CodeProjects/
```

如果源服务器或目标服务器是本机系统，则省略对应的 `luotianlong@IP:` 前缀

如果在本地 Windows 上操作时可以将 `luotianlong@IP` 替换为 `ltl6|7|8|9|10`，如果涉及到 Windows 服务器时需要使用 Windows 文件系统 `E:/CodeProjects/...`

# 2 Huggingface

设置镜像

单次：

```shell
export HF_ENDPOINT=https://hf-mirror.com
```

永久

```shell
# 编辑 bashrc
vim ~/.bashrc

# 在文件末尾添加
export HF_ENDPOINT=https://hf-mirror.com

# 加载文件
source ~/.bashrc
```

# 3. 运行代码

```shell
python main.py
    # --dataset 数据集名称 [mmlu, mmlu_pro, gsm8k, math, humaneval]
    # --topology 拓扑策略 [hierarchical, centralized, decentralized]
    # --malicious_role 恶意角色 
        # hierarchical: Analyst, Solver, Validator
        # centralized
        # decentralized
    # --llm 模型调用 [ollama, api]
    # --model 模型名称 
        # ollama: qwen3:8b...
        # api: Qwen/Qwen3-8B...
    # --sample_size 样本数量
    # --random_seed 随机种子
```
