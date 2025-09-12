#!/bin/bash

BEGIN=51
END=100

echo "停止并删除容器..."

for ((i=BEGIN; i<=END; i++)); do
  CONTAINER_NAME="android_world_$i"
  
  # 检查容器是否存在
  if sudo docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "删除容器: $CONTAINER_NAME"
    sudo docker stop "$CONTAINER_NAME" 2>/dev/null
    sudo docker rm "$CONTAINER_NAME" 2>/dev/null
  else
    echo "容器 $CONTAINER_NAME 不存在，跳过"
  fi
done

echo "所有容器删除完成。"