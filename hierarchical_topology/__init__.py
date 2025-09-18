roles = ['Analyst', 'Solver', 'Validator']
help = '恶意角色 Analyst: 分析; Solver: 解决; Validator: 验证'

conditions = ['No Malicious', 'Simple Malicious', 'Framing Malicious']

from .simulation import run_single_simulation
