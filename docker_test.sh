docker run -d \
  --name android_world_0 \
  --privileged \
  -p 5000:5000 \
  -p 6556:5556 \
  -i \
  -t \
  -v /home/a/liwenkai/android_world:/aw \
  -e HTTP_PROXY=http://host.docker.internal:7897 \
  -e HTTPS_PROXY=http://host.docker.internal:7897 \
  -e NO_PROXY=localhost,127.0.0.1 \
  --add-host host.docker.internal:host-gateway \
  android_world:easy