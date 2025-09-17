"""
Android World 任务扩增
1. 根据现有的 evaluator，构造新的参数 --> 任务多样化
  1.1 目前的任务指令产生 & 任务初始化 & 任务 evaluator ，全部依赖于初始化这个任务时传入的参数 params
  1.2 针对任务初始化，尽可能复用，筛选出 params 只影响 evaluator 的任务
  1.3 针对 evaluator，构造新的 params，缺点是这样的新任务几乎等于测试集
  1.4 针对任务指令，现有的流程是固定的 template + params 填充，为了避免与测试集过于相似，需要对任务指令进行多样化，需要修改目前任务指令产生的逻辑，根据 params["instruct"] 产生
2. 给定多个 evaluator，自由组合
3. 给定 adb 指令，生成新的 evaluator
"""

import os