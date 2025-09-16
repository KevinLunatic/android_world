#!/bin/bash

# 基础镜像和配置
IMAGE="android_world:easy"
BASE_PORT=5000
BASE_ADB_PORT=6556
NUM_CONTAINERS=5 # 新建容器数量
MAX_RETRIES=5
CHECK_INTERVAL=30  # 检查间隔（秒）
SUCCESS_TIMEOUT=600  # 成功超时时间（秒，10分钟）
PARALLEL_JOBS=5  # 并行作业数

# 启动单个容器的函数
start_single_container() {
    local i=$1
    local HOST_PORT=$((BASE_PORT + i))
    local ADB_PORT=$((BASE_ADB_PORT + i))
    local CONTAINER_NAME="android_world_$i"
    local start_time=$(date +%s)
    
    echo "[容器$i] 开始处理容器: $CONTAINER_NAME"
    
    for ((retry=1; retry<=MAX_RETRIES; retry++)); do
        echo "[容器$i] 尝试 $retry/$MAX_RETRIES: 启动容器 $CONTAINER_NAME, 端口: $HOST_PORT:5000, ADB 端口: $ADB_PORT:5556"
        
        # 清理可能存在的同名容器
        sudo docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
        
        # 启动容器（后台运行）
        sudo docker run -d \
            --name "$CONTAINER_NAME" \
            --privileged \
            -p $HOST_PORT:5000 \
            -p $ADB_PORT:5556 \
            -v /home/a/liwenkai/android_world:/aw \
            -e HTTP_PROXY=http://host.docker.internal:7897 \
            -e HTTPS_PROXY=http://host.docker.internal:7897 \
            -e NO_PROXY=localhost,127.0.0.1 \
            --add-host host.docker.internal:host-gateway \
            "$IMAGE" 
        
        if [ $? -eq 0 ]; then
            echo "[容器$i] 容器 $CONTAINER_NAME 已启动，开始监控..."
            
            # 监控容器状态
            local monitor_start=$(date +%s)
            local container_stable=false
            
            while true; do
                local current_time=$(date +%s)
                local elapsed=$((current_time - monitor_start))
                
                # 检查容器状态
                local status=$(sudo docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
                
                if [ "$status" != "running" ]; then
                    echo "[容器$i] ✗ 容器 $CONTAINER_NAME 状态异常: $status (监控时间: ${elapsed}s)"
                    sudo docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
                    break  # 跳出监控循环，进入下次重试
                else
                    echo "[容器$i] 容器 $CONTAINER_NAME 运行正常 (监控时间: ${elapsed}s)"
                fi
                
                # 检查是否达到成功超时时间
                if [ $elapsed -ge $SUCCESS_TIMEOUT ]; then
                    echo "[容器$i] ✓ 容器 $CONTAINER_NAME 运行稳定 (${SUCCESS_TIMEOUT}s)，视为成功启动"
                    container_stable=true
                    break
                fi
                
                # 显示监控进度（每分钟显示一次）
                # if [ $((elapsed % 60)) -eq 0 ] && [ $elapsed -gt 0 ]; then
                #     local remaining=$((SUCCESS_TIMEOUT - elapsed))
                #     echo "[容器$i] 容器 $CONTAINER_NAME 运行正常，剩余监控时间: ${remaining}s"
                # fi
                
                sleep $CHECK_INTERVAL
            done
            
            # 如果容器稳定运行，返回成功
            if [ "$container_stable" = true ]; then
                return 0
            fi
        else
            echo "[容器$i] ✗ 容器 $CONTAINER_NAME 启动失败"
        fi
        
        # 如果不是最后一次重试，等待一下再重试
        if [ $retry -lt $MAX_RETRIES ]; then
            echo "[容器$i] 等待10秒后重试..."
            sleep 10
        fi
    done
    
    echo "[容器$i] ✗ 容器 $CONTAINER_NAME 启动失败，已达到最大重试次数"
    return 1
}

# 检查现有容器状态的函数
check_existing_container() {
    local i=$1
    local CONTAINER_NAME="android_world_$i"
    
    # 检查容器是否存在及其状态
    if sudo docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -q "^${CONTAINER_NAME}\s"; then
        local status=$(sudo docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
        if [ "$status" == "running" ]; then
            echo "[容器$i] ✓ 容器 $CONTAINER_NAME 已运行，跳过"
            return 0
        else
            echo "[容器$i] 容器 $CONTAINER_NAME 状态异常 ($status)，将重新创建"
            return 1
        fi
    else
        echo "[容器$i] 容器 $CONTAINER_NAME 不存在，需要创建"
        return 1
    fi
}

# 安装 socat 并配置转发
install_socat_and_forward() {
    local i=$1
    local CONTAINER_NAME="android_world_$i"

    echo "[容器$i] 安装socat..."
    if sudo docker exec "$CONTAINER_NAME" bash -c "apt install -y socat"; then
        echo "[容器$i] socat安装成功"
        
        # 启动socat端口转发（后台运行）
        echo "[容器$i] 启动socat端口转发..."
        sudo docker exec -d "$CONTAINER_NAME" socat TCP-LISTEN:5556,bind=0.0.0.0,fork,reuseaddr TCP:127.0.0.1:5555
        
        if [ $? -eq 0 ]; then
            echo "[容器$i] socat端口转发启动成功"
            return 0
        else
            echo "[容器$i] ✗ socat端口转发启动失败"
        fi
    else
        echo "[容器$i] ✗ socat安装失败"
    fi
}

# 处理单个容器（检查+启动）
process_container() {
    local i=$1
    
    # 先检查现有容器
    if check_existing_container $i; then
        return 0
    fi
    
    # 需要启动容器
    start_single_container $i

    # 转发
    install_socat_and_forward $i
}

# 导出函数供 parallel 使用
export -f start_single_container check_existing_container process_container install_socat_and_forward
export IMAGE BASE_PORT MAX_RETRIES CHECK_INTERVAL SUCCESS_TIMEOUT BASE_ADB_PORT

echo "开始并行处理 $NUM_CONTAINERS 个容器..."
echo "配置: 检查间隔=${CHECK_INTERVAL}s, 成功超时=${SUCCESS_TIMEOUT}s, 最大重试=${MAX_RETRIES}次, 并行数量=${PARALLEL_JOBS}"

# 使用 parallel 并行执行
seq 0 $((NUM_CONTAINERS-1)) | parallel --line-buffer -j $PARALLEL_JOBS process_container {}

echo "所有容器处理任务完成"

# 显示最终状态统计
echo ""
echo "=== 最终状态统计 ==="
running_count=$(sudo docker ps --filter "name=android_world_" --format "table {{.Names}}" | grep -c "android_world_" || echo "0")
total_count=$(sudo docker ps -a --filter "name=android_world_" --format "table {{.Names}}" | grep -c "android_world_" || echo "0")

echo "运行中的容器: $running_count/$NUM_CONTAINERS"
echo "总创建容器: $total_count"

# 显示异常容器
echo ""
echo "=== 异常容器状态 ==="
sudo docker ps -a --filter "name=android_world_" --format "table {{.Names}}\t{{.Status}}" | grep -v "Up " | head -10