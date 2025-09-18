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

# 3 创建环境

```shell
conda create -n malicious_mas python=3.12
conda activate malicious_mas
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

保存环境

```shell
pip freeze > requirements.txt
```

# 4 运行代码

```shell
python main.py
    # --topology 拓扑策略 [hierarchical, centralized, decentralized]
    # --malicious_role 恶意角色 
        # hierarchical: Analyst, Solver, Validator
        # centralized: Coordinator, Expert, Verifier
        # decentralized: Agent1, Agent2, Agent3
    # --dataset 数据集名称 [mmlu, mmlu_pro, gsm8k, math, humaneval]
    # --llm 模型调用 [ollama, api]
    # --model 模型名称 
        # ollama: qwen3:8b...
        # api: Qwen/Qwen3-8B...
    # --sample_size 样本数量
    # --random_seed 随机种子
```

后台运行

```shell
conda activate malicious_mas
nohup python -u main.py > output.log 2>&1 &
echo $! > output.pid
```
