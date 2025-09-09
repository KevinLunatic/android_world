#!/bin/bash

# 获取当前时间戳 (格式: YYYYMMDD_HHMMSS)
timestamp=$(date +"%Y%m%d_%H%M%S")

# 检查是否存在旧的build.log文件
if [ -f "build.log" ]; then
    # 重命名旧文件，添加时间戳后缀
    mv build.log "build.log.${timestamp}"
    echo "已将旧的 build.log 重命名为 build.log.${timestamp}"
else
    echo "未找到旧的 build.log 文件"
fi

# 开始新的构建
echo "开始 Docker 构建..."
echo "构建时间: $(date)"
echo "构建命令: nohup sudo docker build -t android_world:easy . > build.log 2>&1 &"

# 运行Docker构建命令
nohup sudo docker build -t android_world:easy . > build.log 2>&1 &

# 获取后台进程PID
build_pid=$!

echo "Docker 构建已在后台启动"
echo "进程 PID: ${build_pid}"
echo "日志文件: build.log"
# echo ""
# echo "使用以下命令监控构建进度:"
# echo "  tail -f build.log"
# echo ""
# echo "使用以下命令检查进程状态:"
# echo "  ps aux | grep ${build_pid}"
# echo ""
# echo "构建完成后可以通过以下命令检查状态:"
# echo "  echo \$? (退出码)"